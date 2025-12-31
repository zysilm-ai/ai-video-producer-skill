# AI Video Producer Skill

A Claude Code skill for complete AI video production workflows using **WAN 2.2** video generation via **ComfyUI**. Runs entirely locally on consumer GPUs (RTX 3080+).

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
- Check and run setup if needed (downloads ~33GB of models on first run)
- Start ComfyUI server
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

# Full automatic setup (~33GB download)
python scripts/setup_comfyui.py

# Check setup status
python scripts/setup_comfyui.py --check
```

This will:
1. Clone ComfyUI
2. Install custom nodes (ComfyUI-GGUF, VideoHelperSuite, etc.)
3. Download WAN 2.2 GGUF model (~8.5GB)
4. Download UMT5-XXL text encoder (~4.9GB)
5. Download WAN VAE (~0.2GB)
6. Download LightX2V distillation LoRA (~0.7GB)
7. Download SD 3.5 Large GGUF model (~4.8GB)
8. Download SD 3.5 text encoders (~6.5GB)
9. Download SD 3.5 VAE (~0.2GB)
10. Download SD 3.5 ControlNet models (~5GB)
11. Download IP-Adapter for character consistency (~2GB)

See [SETUP.md](SETUP.md) for detailed manual installation instructions.

#### 2. Start ComfyUI Server

```bash
# Using setup script
python scripts/setup_comfyui.py --start

# Or manually
cd D:/ComfyUI && python main.py --listen 0.0.0.0 --port 8188
```

#### 3. Generate Keyframe Image

```bash
python scripts/sd35_image.py \
  --prompt "A warrior stands ready for battle, dramatic lighting" \
  --output outputs/scene-01/keyframe-start.png \
  --width 832 --height 480
```

#### 4. Generate Video (Image-to-Video)

```bash
python scripts/wan_video.py \
  --prompt "The warrior charges forward, cape flowing in the wind" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --output outputs/scene-01/video.mp4 \
  --preset medium
```

#### 5. Generate Video (First-Last-Frame)

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

### Workflow Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Prompt    │────▶│  Text Enc   │────▶│   CLIP      │
│   (user)    │     │  (UMT5-XXL) │     │  Encode     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐            │
│   Image     │────▶│   Scale &   │────────────┤
│   (keyframe)│     │   Encode    │            │
└─────────────┘     └─────────────┘            │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  GGUF Model │────▶│  LightX2V   │────▶│  KSampler   │
│  (WAN 2.2)  │     │    LoRA     │     │  (8 steps)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ VAE Decode  │
                                        │  + Video    │
                                        └─────────────┘
```

### Key Components

| Component | Model | Purpose |
|-----------|-------|---------|
| Video Model | WAN 2.2 I2V (GGUF Q4_K_M) | 14B parameter video generation |
| Text Encoder | UMT5-XXL (FP8) | Text understanding |
| Distillation LoRA | LightX2V rank64 | Enables 8-step generation |
| VAE | WAN 2.1 VAE | Latent encoding/decoding |

### Generation Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Steps | 8 | With LightX2V LoRA |
| CFG | 1.0 | Guidance baked into LoRA |
| Sampler | uni_pc | Fast, stable |
| Scheduler | simple | |
| LoRA Strength | 1.25 | Optimized for I2V |
| Resolution | Up to 832x480 | Adjustable presets |
| Frame Rate | 16 fps | ~5 sec per clip |

### Model Locations

After setup, models are stored in:

```
ComfyUI/models/
├── diffusion_models/
│   └── wan2.2_i2v_low_noise_14B_Q4_K_M.gguf
├── text_encoders/
│   └── umt5_xxl_fp8_e4m3fn_scaled.safetensors
├── vae/
│   └── wan_2.1_vae.safetensors
└── loras/
    └── Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors
```

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

### sd35_image.py

Generate keyframe images with character and spatial consistency.

```bash
python scripts/sd35_image.py \
  --prompt "Image description" \
  --output path/to/output.png \
  [--style-ref path/to/style.json] \
  [--reference path/to/reference.png] \
  [--mode action|static] \
  [--controlnet-strength 0.7] \
  [--width 832] [--height 480]
```

#### Mode Selection

| Mode | Workflow | Best For |
|------|----------|----------|
| `action` | IP-Adapter only | Fighting, sports, dancing - allows position changes |
| `static` | Depth + IP-Adapter | Talking, standing, camera moves - locks positions |

#### ControlNet Strength (static mode)

| Strength | Effect |
|----------|--------|
| `0.7-1.0` | Strong spatial lock (default) |
| `0.4-0.6` | Moderate - allows slight shifts |
| `0.2-0.3` | Light guidance |

**Example - Action scene (boxing):**
```bash
python scripts/sd35_image.py \
  --prompt "Boxer lands a powerful punch" \
  --reference keyframe-start.png \
  --mode action \
  --output keyframe-end.png
```

**Example - Static scene with custom strength:**
```bash
python scripts/sd35_image.py \
  --prompt "Character turns head slightly" \
  --reference keyframe-start.png \
  --mode static --controlnet-strength 0.5 \
  --output keyframe-end.png
```

### setup_comfyui.py

Setup and manage ComfyUI installation.

```bash
python scripts/setup_comfyui.py              # Full setup
python scripts/setup_comfyui.py --check      # Check status
python scripts/setup_comfyui.py --start      # Start server
python scripts/setup_comfyui.py --models     # Download models only
```

## Directory Structure

```
gemini-video-producer-skill/
├── SKILL.md                 # Claude Code skill instructions
├── README.md                # This file
├── SETUP.md                 # Detailed setup guide
├── requirements.txt         # Python dependencies
├── scripts/
│   ├── wan_video.py         # Video generation
│   ├── sd35_image.py        # Keyframe image generation (SD 3.5 + IP-Adapter)
│   ├── setup_comfyui.py     # Auto-setup script
│   ├── comfyui_client.py    # ComfyUI API client
│   └── workflows/
│       ├── wan_i2v.json     # Image-to-Video workflow
│       └── wan_flf2v.json   # First-Last-Frame workflow
├── references/
│   ├── prompt-engineering.md
│   ├── style-systems.md
│   └── troubleshooting.md
└── outputs/                 # Generated content
```

## Workflow JSON Structure

The video generation uses optimized ComfyUI workflows:

### Image-to-Video (wan_i2v.json)

```
UnetLoaderGGUF → ModelSamplingSD3 → LoraLoader (LightX2V)
                                          ↓
CLIPLoader → CLIPTextEncode (pos/neg) → WanImageToVideo
                                          ↓
LoadImage → ImageScale → ─────────────────┘
                                          ↓
                            KSampler (8 steps, CFG 1.0)
                                          ↓
                            VAEDecode → VHS_VideoCombine
```

### Key Workflow Features

- **LightX2V LoRA**: Enables 8-step generation (vs 20-40 without)
- **CFG 1.0**: Guidance baked into distillation LoRA
- **Native nodes**: Uses stable ComfyUI core nodes
- **GGUF quantization**: Reduces VRAM from 24GB to 10GB

## Troubleshooting

### ComfyUI Not Running

```bash
# Check if ComfyUI is accessible
python scripts/comfyui_client.py

# Start ComfyUI
python scripts/setup_comfyui.py --start
```

### Out of VRAM

Use lower resolution preset:
```bash
python scripts/wan_video.py --preset low ...
```

### Slow Generation

Ensure LightX2V LoRA is loaded (check setup):
```bash
python scripts/setup_comfyui.py --check
```

### Poor Quality

- Verify CFG is 1.0 (not 5.0)
- Verify LoRA strength is 1.25
- Check that LightX2V LoRA is installed

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
- [CGPixel](https://www.patreon.com/cgpixel) - Optimized ComfyUI workflows
- [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) - GGUF model support

## Contributing

Contributions welcome! Areas for improvement:

- Additional video model support
- More resolution presets
- Audio generation integration
- Batch processing tools

## License

MIT License - See LICENSE.txt

## Acknowledgments

- WAN 2.2 model by Alibaba
- LightX2V distillation by lightx2v team
- CGPixel for workflow optimization techniques
- ComfyUI community for excellent tooling
