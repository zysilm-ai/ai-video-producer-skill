# AI Video Producer Skill

A Claude Code skill for complete AI video production workflows using **WAN 2.2** video generation and **Qwen Image Edit 2511** keyframe generation via **HuggingFace diffusers**. Runs entirely locally on consumer GPUs (RTX 3080+ with 10GB+ VRAM).

## Overview

This skill guides you through creating professional AI-generated videos with a structured, iterative workflow:

1. **Production Philosophy** - Define visual style, motion language, and narrative approach
2. **Scene Breakdown** - Decompose video into scenes with keyframe requirements
3. **Keyframe Generation** - Create start/end frames with visual consistency
4. **Video Synthesis** - Generate video segments using WAN 2.2 (local, fast)
5. **Review & Iterate** - Refine based on feedback

The philosophy-first approach ensures visual coherence across all scenes, resulting in professional, cohesive videos.

## Key Features

- **100% Local** - No cloud APIs needed, runs on your GPU
- **Fast Generation** - ~2 minutes per 5-second clip with LightX2V optimization
- **Low VRAM** - Works on 10GB+ GPUs using GGUF quantization
- **High Quality** - 8-step distillation LoRA maintains quality at high speed
- **Two Modes** - Image-to-Video (I2V) and First-Last-Frame (FLF2V)

## Supported Video Types

- **Promotional** - Product launches, brand stories, ads
- **Educational** - Tutorials, explainers, courses
- **Narrative** - Short films, animations, music videos
- **Social Media** - Platform-optimized content (TikTok, Reels, Shorts)
- **Corporate** - Demos, presentations, training
- **Game Trailers** - Action sequences, atmosphere, gameplay hints

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM | 10GB | 12GB+ |
| RAM | 16GB | 32GB |
| Storage | 30GB free | 50GB+ |
| OS | Windows/Linux | Windows 10/11, Ubuntu 22.04+ |

**Required Software:** Python 3.10+, Git, CUDA 12.x

## Usage

### With Claude Code (Recommended)

Simply describe what video you want to create. Claude will automatically:
- Check and run setup if needed (downloads ~50GB of models on first run)
- Load models as needed (cached for subsequent runs)
- Guide you through the production workflow
- Generate keyframes and videos

**Example conversation:**
```
You: I want to create a 15-second product demo for a smartwatch

Claude: I'll help you create a product demo video. Let's start by
establishing a Production Philosophy...
```

**The workflow:**
1. Claude creates philosophy.md, style.json, scene-breakdown.md
2. You approve each keyframe before video generation
3. Videos are generated scene by scene
4. Review and iterate until satisfied

### Manual / Standalone Usage

For using the scripts without Claude Code.

#### 1. Setup (First Time Only)

```bash
cd gemini-video-producer-skill

# Install Python dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Check setup status
python scripts/setup_diffusers.py --check

# Download required models (~50GB)
python scripts/setup_diffusers.py --download
```

This downloads from HuggingFace:
1. WAN 2.2 I2V 14B model (~28GB)
2. LightX2V distillation LoRA (~0.7GB)
3. Qwen Image Edit 2511 (~20GB)
4. (Optional) ControlNet Union for pose guidance (~3.5GB)

Models are cached in `~/.cache/huggingface/` and reused across runs.

See [SETUP.md](SETUP.md) for detailed manual installation instructions.

#### 2. Generate Keyframe Image

```bash
python scripts/qwen_image.py \
  --prompt "A warrior stands ready for battle, dramatic lighting" \
  --output outputs/scene-01/keyframe-start.png \
  --preset medium
```

#### 3. Generate Video (Image-to-Video)

```bash
python scripts/wan_video.py \
  --prompt "The warrior charges forward, cape flowing in the wind" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --output outputs/scene-01/video.mp4 \
  --preset medium
```

#### 4. Generate Video (First-Last-Frame)

```bash
python scripts/wan_video.py \
  --prompt "Warrior swings sword in powerful arc" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --end-frame outputs/scene-01/keyframe-end.png \
  --output outputs/scene-01/video.mp4
```

### Resolution Presets

| Preset | Resolution | Frames | Use Case |
|--------|------------|--------|----------|
| low | 640x384 | 49 | Quick tests, low VRAM |
| medium | 832x480 | 81 | Balanced quality/speed |
| high | 1280x720 | 81 | High quality (12GB+ VRAM) |

## Architecture

### Diffusers Pipeline

The skill uses HuggingFace diffusers for direct Python inference without a server:

```
┌─────────────┐     ┌─────────────────────────────────────┐
│   Prompt    │────▶│  WanImageToVideoPipeline            │
│   (user)    │     │  ├─ Text Encoder (T5-XXL)           │
└─────────────┘     │  ├─ Transformer (WAN 2.2 14B)       │
                    │  ├─ LightX2V LoRA (8-step distill)  │
┌─────────────┐     │  └─ VAE Decoder                     │
│   Image     │────▶│                                     │
│   (keyframe)│     └──────────────┬──────────────────────┘
└─────────────┘                    │
                                   ▼
                            ┌─────────────┐
                            │   Video     │
                            │  (81 frames)│
                            └─────────────┘
```

### Key Components

| Component | HuggingFace Model | Purpose |
|-----------|-------------------|---------|
| Video Pipeline | `Wan-AI/Wan2.2-I2V-A14B-Diffusers` | 14B MoE video generation |
| Distillation LoRA | `lightx2v/Wan2.1-I2V-14B-480P-StepDistill...` | Enables 8-step generation |
| Image Pipeline | `Qwen/Qwen-Image-Edit-2511` | Keyframe generation |
| ControlNet | `InstantX/Qwen-Image-ControlNet-Union` | Pose-guided generation |

### Generation Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Steps | 8 | With LightX2V LoRA |
| CFG | 1.0 | Guidance baked into LoRA |
| LoRA Strength | 1.25 | Optimized for I2V |
| Resolution | Up to 832x480 | Adjustable presets |
| Frame Rate | 16 fps | ~5 sec per clip |

### Model Locations

Models are stored in the `models/` directory within this repository (gitignored):

```
gemini-video-producer-skill/
└── models/
    └── hub/
        ├── models--Wan-AI--Wan2.2-I2V-A14B-Diffusers/
        ├── models--Qwen--Qwen-Image-Edit-2511/
        └── models--lightx2v--Wan2.1-I2V-14B-480P-StepDistill.../
```

This keeps models local to the project and avoids filling your system drive.

## Script Reference

### wan_video.py

Generate videos from prompts and keyframes.

```bash
python scripts/wan_video.py \
  --prompt "Motion description" \
  --output path/to/output.mp4 \
  [--start-frame path/to/start.png] \
  [--end-frame path/to/end.png] \
  [--style-ref path/to/style.json] \
  [--preset low|medium|high] \
  [--steps 8] \
  [--cfg 1.0] \
  [--seed 0]
```

### qwen_image.py

Generate keyframe images using Qwen Image Edit 2511 with multiple modes.

```bash
python scripts/qwen_image.py \
  --prompt "Image description" \
  --output path/to/output.png \
  [--style-ref path/to/style.json] \
  [--reference path/to/reference.png] \
  [--pose path/to/pose.png] \
  [--control-strength 0.8] \
  [--preset low|medium|high]
```

#### Generation Modes

| Mode | Command | Best For |
|------|---------|----------|
| **T2I** | No reference | Initial keyframe, establishing shots |
| **Edit** | `--reference` only | Editing existing image, maintaining consistency |
| **Pose** | `--reference` + `--pose` | Dramatic pose changes while keeping identity |

#### ControlNet Strength (pose mode)

| Strength | Effect |
|----------|--------|
| `0.8-1.0` | Strong pose guidance (default) |
| `0.5-0.7` | Moderate - allows some variation |
| `0.3-0.5` | Light guidance |

**Example - Edit mode (maintain consistency):**
```bash
python scripts/qwen_image.py \
  --prompt "Same character now smiling" \
  --reference keyframe-start.png \
  --output keyframe-end.png
```

**Example - Pose mode (change pose):**
```bash
python scripts/qwen_image.py \
  --prompt "Character sitting in meditation pose" \
  --reference keyframe-start.png \
  --pose assets/poses/meditation.png \
  --control-strength 0.8 \
  --output keyframe-end.png
```

### setup_diffusers.py

Setup and download models from HuggingFace.

```bash
python scripts/setup_diffusers.py              # Check setup status
python scripts/setup_diffusers.py --check      # Validate setup
python scripts/setup_diffusers.py --download   # Download required models
python scripts/setup_diffusers.py --download-all  # Download all models (including optional)
python scripts/setup_diffusers.py --info       # Show download size estimates
```

## Directory Structure

```
gemini-video-producer-skill/
├── SKILL.md                 # Claude Code skill instructions
├── README.md                # This file
├── SETUP.md                 # Detailed setup guide
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── wan_video.py         # Video generation (WAN 2.2 via diffusers)
│   ├── qwen_image.py        # Keyframe generation (Qwen via diffusers)
│   ├── setup_diffusers.py   # Model download and setup
│   ├── validate_diffusers.py # Setup validation
│   ├── diffusers_utils.py   # Shared utilities for diffusers
│   └── utils.py             # General utilities
├── references/
│   ├── prompt-engineering.md
│   ├── style-systems.md
│   └── troubleshooting.md
├── docs/
│   └── ADVANCED_KEYFRAME_PLAN.md  # Layer-based generation docs
└── outputs/                 # Generated content
```

## Troubleshooting

### Models Not Found

```bash
# Check setup status
python scripts/setup_diffusers.py --check

# Download missing models
python scripts/setup_diffusers.py --download
```

### Out of VRAM

Use lower resolution preset:
```bash
python scripts/wan_video.py --preset low ...
```

The diffusers pipeline automatically applies memory optimization based on available VRAM:
- **<8GB**: Sequential CPU offloading
- **8-12GB**: Model CPU offloading
- **12-16GB**: Attention slicing
- **16GB+**: Full GPU inference

### Slow Generation

Ensure LightX2V LoRA is loaded (check setup):
```bash
python scripts/validate_diffusers.py --detailed
```

### Poor Quality

- Verify CFG is 1.0 (not higher)
- Verify LoRA strength is 1.25
- Check that models are fully downloaded

See [references/troubleshooting.md](references/troubleshooting.md) for more solutions.

## Performance

### Generation Times (RTX 3080 10GB)

| Preset | Resolution | Frames | Time |
|--------|------------|--------|------|
| low | 640x384 | 49 | ~1.5 min |
| medium | 832x480 | 81 | ~2.5 min |
| high | 1280x720 | 81 | ~4 min |

### Optimization Credits

The fast generation is made possible by:
- [LightX2V](https://huggingface.co/lightx2v) - Step/CFG distillation LoRA
- [HuggingFace Diffusers](https://github.com/huggingface/diffusers) - Unified inference library
- [Wan-AI](https://github.com/Wan-Video/Wan2.2) - WAN 2.2 video model

## Contributing

Contributions welcome! Areas for improvement:

- Additional video model support
- More resolution presets
- Audio generation integration
- Batch processing tools

## License

MIT License - See LICENSE.txt

## Acknowledgments

- WAN 2.2 model by Wan-AI
- LightX2V distillation by lightx2v team
- Qwen Image Edit by Alibaba Qwen team
- HuggingFace diffusers team for the inference library
