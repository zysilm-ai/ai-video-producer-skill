# AI Video Producer Skill

A Claude Code skill for complete AI video production workflows using **WAN 2.1** video generation and **Qwen Image Edit 2511** keyframe generation via **ComfyUI**. Runs entirely locally on consumer GPUs (RTX 3080+ with 10GB+ VRAM).

## Overview

This skill guides you through creating professional AI-generated videos with a structured, iterative workflow:

1. **Production Philosophy** - Define visual style, motion language, and narrative approach
2. **Scene Breakdown** - Decompose video into scenes with keyframe requirements
3. **Asset Generation** - Create reusable character, background, and pose assets
4. **Keyframe Generation** - Create start/end frames with visual consistency
5. **Video Synthesis** - Generate video segments using WAN 2.1
6. **Review & Iterate** - Refine based on feedback

The philosophy-first approach ensures visual coherence across all scenes, resulting in professional, cohesive videos.

## Key Features

- **100% Local** - No cloud APIs needed, runs on your GPU
- **Fast Generation** - ~36 seconds per image (warm), ~2 minutes per 5-second video
- **Low VRAM** - Works on 10GB GPUs using GGUF quantization
- **High Quality** - Lightning LoRA (4-step) for images, LightX2V (8-step) for video
- **Two Video Modes** - Image-to-Video (I2V) and First-Last-Frame (FLF2V)
- **Tiled VAE** - Memory-efficient decoding for constrained VRAM

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
| Storage | 40GB free | 60GB+ |
| OS | Windows/Linux | Windows 10/11, Ubuntu 22.04+ |

**Required Software:** Python 3.10+, Git, CUDA 12.x

---

## Quick Start

### 1. Setup (First Time Only)

```bash
cd gemini-video-producer-skill

# Full automatic setup (installs ComfyUI + downloads models ~40GB)
python scripts/setup_comfyui.py
```

This will:
1. Clone ComfyUI into `./comfyui/`
2. Install custom nodes (GGUF, VideoHelperSuite, Manager)
3. Download all required models:
   - WAN 2.1 I2V GGUF (~11GB)
   - Qwen Image Edit 2511 GGUF (~13GB)
   - Text encoders, VAEs, and LoRAs (~14GB)

### 2. Start ComfyUI Server

```bash
python scripts/setup_comfyui.py --start
```

Keep this running in the background. The server must be running for generation.

### 3. Generate!

```bash
# Generate a keyframe image
python scripts/qwen_image_comfyui.py \
  --prompt "A warrior in dramatic lighting, anime style" \
  --output outputs/keyframe.png

# Generate a video from the keyframe
python scripts/wan_video_comfyui.py \
  --prompt "The warrior charges forward, cape flowing" \
  --start-frame outputs/keyframe.png \
  --output outputs/video.mp4
```

---

## Usage with Claude Code

Simply describe what video you want to create. Claude will automatically:
- Start ComfyUI server if needed
- Guide you through the production workflow
- Generate keyframes and videos with your approval at each step

**Example conversation:**
```
You: Create a 15-second anime fight scene with two warriors

Claude: I'll help you create that video. Let me start by establishing
a Production Philosophy and breaking down the scenes...
```

---

## Architecture

### ComfyUI Pipeline

The skill uses ComfyUI with GGUF quantized models for efficient GPU memory usage:

```
┌─────────────────────────────────────────────────────────────┐
│                    ComfyUI Server (:8188)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌──────────────────────────────────┐  │
│  │   Prompt    │────▶│  Qwen Image Edit 2511            │  │
│  └─────────────┘     │  ├─ GGUF Q4_K_M (13GB)           │  │
│                      │  ├─ Lightning LoRA (4-step)      │  │
│                      │  └─ Tiled VAE Decode             │  │
│                      └──────────────┬───────────────────┘  │
│                                     │                      │
│                                     ▼                      │
│                              ┌─────────────┐               │
│                              │  Keyframe   │               │
│                              │   (PNG)     │               │
│                              └──────┬──────┘               │
│                                     │                      │
│                                     ▼                      │
│                      ┌──────────────────────────────────┐  │
│                      │  WAN 2.1 I2V                     │  │
│                      │  ├─ GGUF Q4_K_M (11GB)           │  │
│                      │  ├─ LightX2V LoRA (8-step)       │  │
│                      │  └─ VAE Decode                   │  │
│                      └──────────────┬───────────────────┘  │
│                                     │                      │
│                                     ▼                      │
│                              ┌─────────────┐               │
│                              │   Video     │               │
│                              │  (81 frames)│               │
│                              └─────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Models (GGUF Quantized)

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| Video Generation | WAN 2.1 I2V Q4_K_M | 11.3GB | 14B video transformer |
| Video LoRA | LightX2V | 0.7GB | 8-step distillation |
| Image Generation | Qwen Image Edit Q4_K_M | 13.1GB | 20B image transformer |
| Image LoRA | Lightning | 0.8GB | 4-step distillation |
| Text Encoders | UMT5-XXL + Qwen VL 7B | 13GB | FP8 quantized |
| VAEs | WAN + Qwen | 0.4GB | Video/Image decoding |

**Total: ~40GB** (stored in `./comfyui/models/`)

### Performance (RTX 3080 10GB)

| Task | Cold Start | Warm |
|------|------------|------|
| Image Generation | ~63s | ~36s |
| Video Generation (81 frames) | ~3 min | ~2 min |

---

## Script Reference

### qwen_image_comfyui.py

Generate keyframe images using Qwen Image Edit 2511.

```bash
python scripts/qwen_image_comfyui.py \
  --prompt "Description of the image" \
  --output path/to/output.png \
  [--reference path/to/reference.png]  # For edit mode
  [--pose path/to/pose.png]            # For pose-guided mode
  [--control-strength 0.9]             # ControlNet strength
  [--preset low|medium|high]           # Resolution preset
  [--seed 0]                           # Random seed
```

**Generation Modes:**

| Mode | Arguments | Use Case |
|------|-----------|----------|
| T2I | No reference | Initial keyframe, establishing shots |
| Edit | `--reference` | Maintain consistency with existing image |
| Pose | `--reference` + `--pose` | Change pose while keeping identity |

### wan_video_comfyui.py

Generate videos from keyframes using WAN 2.1.

```bash
python scripts/wan_video_comfyui.py \
  --prompt "Motion description" \
  --output path/to/output.mp4 \
  --start-frame path/to/start.png \
  [--end-frame path/to/end.png]     # For First-Last-Frame mode
  [--preset low|medium|high]        # Resolution preset
  [--steps 8]                       # Sampling steps
  [--seed 0]                        # Random seed
```

**Video Modes:**

| Mode | Arguments | Use Case |
|------|-----------|----------|
| I2V | `--start-frame` only | Continuous motion from single frame |
| FLF2V | `--start-frame` + `--end-frame` | Precise control over motion |

### setup_comfyui.py

Setup and manage ComfyUI installation.

```bash
python scripts/setup_comfyui.py              # Full setup
python scripts/setup_comfyui.py --check      # Check status
python scripts/setup_comfyui.py --start      # Start server
python scripts/setup_comfyui.py --models     # Download models only
```

---

## Resolution Presets

| Preset | Resolution | Frames | VRAM Usage |
|--------|------------|--------|------------|
| low | 640x384 | 49 | ~8GB |
| medium | 832x480 | 81 | ~10GB |
| high | 1280x720 | 81 | ~16GB |

---

## Directory Structure

```
gemini-video-producer-skill/
├── SKILL.md                    # Claude Code skill instructions
├── README.md                   # This file
├── SETUP.md                    # Detailed diffusers setup (legacy)
├── scripts/
│   ├── qwen_image_comfyui.py   # Image generation (ComfyUI)
│   ├── wan_video_comfyui.py    # Video generation (ComfyUI)
│   ├── setup_comfyui.py        # ComfyUI setup and server management
│   ├── comfyui_client.py       # ComfyUI API client
│   ├── utils.py                # Shared utilities
│   └── workflows/              # ComfyUI workflow JSON files
│       ├── qwen_t2i.json       # Text-to-Image
│       ├── qwen_edit.json      # Edit with reference
│       ├── qwen_pose.json      # Pose-guided generation
│       ├── wan_i2v.json        # Image-to-Video
│       └── wan_flf2v.json      # First-Last-Frame-to-Video
├── comfyui/                    # ComfyUI installation (gitignored)
│   ├── models/                 # All models stored here
│   └── output/                 # ComfyUI output directory
├── references/
│   ├── prompt-engineering.md
│   ├── style-systems.md
│   └── troubleshooting.md
└── outputs/                    # Your generated content
```

---

## Troubleshooting

### ComfyUI Server Not Running

```bash
# Check if server is running
curl http://127.0.0.1:8188/system_stats

# Start the server
python scripts/setup_comfyui.py --start
```

### Models Not Found

```bash
# Check setup status
python scripts/setup_comfyui.py --check

# Download missing models
python scripts/setup_comfyui.py --models
```

### Out of VRAM / Generation Hanging

The tiled VAE decode should handle most VRAM issues. If problems persist:

1. Use lower resolution preset: `--preset low`
2. Restart ComfyUI server to clear memory
3. Close other GPU applications

### Slow Generation

First run is slower due to model loading (~60s). Subsequent runs with warm models are faster (~36s for images).

See [references/troubleshooting.md](references/troubleshooting.md) for more solutions.

---

## Legacy: Diffusers Backend

The `scripts/qwen_image.py` and `scripts/wan_video.py` scripts use HuggingFace diffusers directly. These are kept for compatibility but are **not recommended** for 10GB VRAM cards due to slower performance from CPU offloading.

Use the ComfyUI scripts (`*_comfyui.py`) for best performance.

---

## Contributing

Contributions welcome! Areas for improvement:

- Additional model support (SD3.5, FLUX)
- ControlNet workflows (depth, canny)
- Audio generation integration
- Batch processing tools

## License

MIT License - See LICENSE.txt

## Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - Node-based UI framework
- [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) - GGUF model support
- [WAN 2.1/2.2](https://github.com/Wan-Video/Wan2.1) - Video generation model
- [LightX2V](https://huggingface.co/lightx2v) - Step/CFG distillation LoRA
- [Qwen Image Edit](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) - Image generation model
- [Lightning LoRA](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning) - Fast 4-step generation
