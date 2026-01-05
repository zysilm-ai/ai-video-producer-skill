# AI Video Producer Skill

A Claude Code skill for complete AI video production workflows using **WAN 2.1** video generation and **Qwen Image Edit 2511** keyframe generation via **ComfyUI**. Runs entirely locally on consumer GPUs (RTX 3080+ with 10GB+ VRAM).

## Overview

This skill guides you through creating professional AI-generated videos with a structured, iterative workflow:

0. **Pipeline Mode Selection** - Choose Video-First (recommended) or Keyframe-First
1. **Production Philosophy** - Define visual style, motion language, and narrative approach
2. **Scene Breakdown** - Decompose video into scenes with motion requirements
3. **Asset Generation** - Create reusable character and background assets
4. **Keyframe/Video Generation** - Execute pipeline deterministically via `execute_pipeline.py`
5. **Review & Iterate** - Refine based on feedback

The philosophy-first approach ensures visual coherence across all scenes, resulting in professional, cohesive videos.

### Pipeline Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **Video-First** (Recommended) | Generate first keyframe only, then videos sequentially. Last frame of each video becomes next scene's start. | Visual continuity between scenes |
| **Keyframe-First** | Generate all keyframes independently, then videos between them. | Precise control over end frames |

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
# Automatically uses --cache-none for optimal 10GB VRAM performance
python scripts/setup_comfyui.py --start
```

Keep this running in the background. The server must be running for generation.

**Note:** The `--cache-none` flag is automatically used to enable sequential model loading, which is critical for multi-reference keyframe generation on 10GB VRAM systems.

### 3. Generate!

```bash
# Step 1: Generate character asset (neutral A-pose, clean background)
python scripts/asset_generator.py character \
  --name warrior \
  --description "A warrior in dramatic lighting, anime style, red armor" \
  --output outputs/assets/warrior.png

# Step 2: Generate keyframe with character (--free-memory is MANDATORY)
python scripts/keyframe_generator.py \
  --free-memory \
  --prompt "Warrior charging forward, cape flowing, dramatic lighting" \
  --character outputs/assets/warrior.png \
  --output outputs/keyframes/KF-A.png

# Step 3: Generate a video from the keyframe
python scripts/wan_video_comfyui.py \
  --free-memory \
  --prompt "The warrior charges forward, cape flowing" \
  --start-frame outputs/keyframes/KF-A.png \
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

**Default Models (~40GB):**

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| Video Generation | WAN 2.1 I2V Q4_K_M | 11.3GB | 14B video transformer |
| Video LoRA | LightX2V | 0.7GB | 8-step distillation |
| Image Generation | Qwen Image Edit Q4_K_M | 13.1GB | 20B image transformer |
| Image LoRA | Lightning | 0.8GB | 4-step distillation |
| Text Encoders | UMT5-XXL + Qwen VL 7B | 13GB | FP8 quantized |
| VAEs | WAN + Qwen | 0.4GB | Video/Image decoding |

**Optional WAN 2.2 MoE Models (+24GB):**

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| HighNoise Expert | WAN 2.2 I2V Q6_K | 12GB | MoE early denoising |
| LowNoise Expert | WAN 2.2 I2V Q6_K | 12GB | MoE refinement |

Download with: `python scripts/setup_comfyui.py --q6k`

**Total: ~40GB base** (+ ~24GB optional for WAN 2.2)

### Performance (RTX 3080 10GB)

| Task | Cold Start | Warm |
|------|------------|------|
| Image Generation | ~63s | ~36s |
| Video Generation (81 frames) | ~3 min | ~2 min |

---

## Script Reference

### execute_pipeline.py

Execute a complete pipeline.json file deterministically.

```bash
# Check pipeline status
python scripts/execute_pipeline.py output/project/pipeline.json --status

# Validate pipeline structure
python scripts/execute_pipeline.py output/project/pipeline.json --validate

# Execute specific stage (video-first mode)
python scripts/execute_pipeline.py output/project/pipeline.json --stage assets
python scripts/execute_pipeline.py output/project/pipeline.json --stage first_keyframe
python scripts/execute_pipeline.py output/project/pipeline.json --stage scenes

# Execute specific stage (keyframe-first mode)
python scripts/execute_pipeline.py output/project/pipeline.json --stage assets
python scripts/execute_pipeline.py output/project/pipeline.json --stage keyframes
python scripts/execute_pipeline.py output/project/pipeline.json --stage videos

# Execute all stages with review pauses
python scripts/execute_pipeline.py output/project/pipeline.json --all

# Regenerate a specific item
python scripts/execute_pipeline.py output/project/pipeline.json --regenerate KF-A
```

The pipeline executor automatically:
- Detects pipeline mode (video-first or keyframe-first) from schema
- Manages VRAM by using `--free-memory` appropriately
- Tracks status in pipeline.json
- Extracts last frames for video-first scene continuity

### asset_generator.py

Generate reusable assets for keyframe generation.

```bash
# Character identity (neutral A-pose, clean white background)
python scripts/asset_generator.py character \
  --name [character_name] \
  --description "[detailed character description]" \
  --output path/to/character.png

# Background (no people, environment only)
python scripts/asset_generator.py background \
  --name [background_name] \
  --description "[environment description]" \
  --output path/to/background.png

# Style reference
python scripts/asset_generator.py style \
  --name [style_name] \
  --description "[style description]" \
  --output path/to/style.png
```

### keyframe_generator.py

Generate keyframes using character reference images.

**IMPORTANT:** Always use `--free-memory` for EVERY keyframe generation to prevent VRAM fragmentation.

```bash
python scripts/keyframe_generator.py \
  --free-memory \                        # MANDATORY - prevents VRAM fragmentation
  --prompt "Action/scene description" \
  --output path/to/keyframe.png \
  --character path/to/character.png      # Character identity (WHO)
  [--background path/to/background.png]  # Background reference
  [--preset low|medium|high]             # Resolution preset
```

**Multi-Character Generation:**

```bash
# Two characters (up to 3 supported) - always use --free-memory
python scripts/keyframe_generator.py \
  --free-memory \
  --prompt "On the left: warrior attacking. On the right: ninja defending." \
  --character assets/warrior.png \
  --character assets/ninja.png \
  --output keyframes/KF-battle.png

# Two characters with background reference
python scripts/keyframe_generator.py \
  --free-memory \
  --prompt "Warriors facing off in temple courtyard" \
  --background assets/backgrounds/temple.png \
  --character assets/warrior.png \
  --character assets/ninja.png \
  --output keyframes/KF-standoff.png
```

**Reference Slot Allocation:**

| Slot | Without --background | With --background |
|------|---------------------|-------------------|
| image1 | Character 1 | Background |
| image2 | Character 2 | Character 1 |
| image3 | Character 3 | Character 2 |

**Note:** With `--background`, maximum 2 characters are supported (3 reference slots total).

### wan_video_comfyui.py

Generate videos from keyframes using WAN 2.1/2.2.

```bash
python scripts/wan_video_comfyui.py \
  --prompt "Motion description" \
  --output path/to/output.mp4 \
  --start-frame path/to/start.png \
  [--end-frame path/to/end.png]     # For First-Last-Frame mode
  [--preset low|medium|high]        # Resolution preset
  [--steps 8]                       # Sampling steps
  [--seed 0]                        # Random seed
  [--moe]                           # WAN 2.2 MoE (best quality, slow)
  [--moe-fast]                      # WAN 2.2 MoE + LoRA (better quality)
  [--alg]                           # WAN 2.2 MoE + ALG (enhanced motion)
```

**Video Modes:**

| Mode | Arguments | Use Case |
|------|-----------|----------|
| I2V | `--start-frame` only | Continuous motion from single frame |
| FLF2V | `--start-frame` + `--end-frame` | Precise control over motion |

**Model Selection:**

| Flag | Model | Time | Best For |
|------|-------|------|----------|
| (none) | WAN 2.1 Q4K + LoRA | ~6 min | Default, fastest |
| `--moe-fast` | WAN 2.2 MoE + LoRA | ~7 min | Better quality |
| `--alg` | WAN 2.2 MoE + ALG | ~7 min | Action/dynamic scenes |
| `--moe` | WAN 2.2 MoE (20 steps) | ~30 min | Maximum quality |

**Note:** WAN 2.2 modes require additional models. Download with: `python scripts/setup_comfyui.py --q6k`

### angle_transformer.py

Transform keyframe camera angles without regenerating the base image.

```bash
python scripts/angle_transformer.py \
  --input path/to/keyframe.png \
  --output path/to/transformed.png \
  [--rotate -45]                    # Horizontal rotation (-180 to 180)
  [--tilt -30]                      # Vertical tilt (-90 to 90)
  [--zoom wide|normal|close]        # Lens type
  [--prompt "custom angle desc"]    # Override auto-generated description
```

**Examples:**

```bash
# Low angle dramatic shot
python scripts/angle_transformer.py \
  --input keyframes/KF-A.png \
  --output keyframes/KF-A-lowangle.png \
  --tilt -30

# Rotated wide shot
python scripts/angle_transformer.py \
  --input keyframes/KF-B.png \
  --output keyframes/KF-B-wide.png \
  --rotate 45 \
  --zoom wide
```

### setup_comfyui.py

Setup and manage ComfyUI installation.

```bash
python scripts/setup_comfyui.py              # Full setup
python scripts/setup_comfyui.py --check      # Check status
python scripts/setup_comfyui.py --start      # Start server
python scripts/setup_comfyui.py --models     # Download models only
python scripts/setup_comfyui.py --q6k        # Download WAN 2.2 MoE models (optional)
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
├── scripts/
│   ├── execute_pipeline.py     # Pipeline executor
│   ├── asset_generator.py      # Generate character/background/style assets
│   ├── keyframe_generator.py   # Generate keyframes with character references
│   ├── angle_transformer.py    # Transform keyframe camera angles
│   ├── wan_video_comfyui.py    # Video generation (WAN 2.1/2.2)
│   ├── setup_comfyui.py        # ComfyUI setup and server management
│   ├── core.py                 # Shared generation utilities
│   ├── comfyui_client.py       # ComfyUI API client
│   ├── utils.py                # Shared utilities
│   └── workflows/              # ComfyUI workflow JSON files
│       ├── qwen_*.json         # Image generation workflows
│       ├── wan_i2v.json        # Image-to-Video (WAN 2.1)
│       ├── wan_flf2v.json      # First-Last-Frame-to-Video
│       ├── wan_i2v_moe.json    # WAN 2.2 MoE (20 steps)
│       ├── wan_i2v_moe_fast.json    # WAN 2.2 MoE + LoRA
│       └── wan_i2v_moe_fast_alg.json # WAN 2.2 MoE + ALG
├── comfyui/                    # ComfyUI installation (gitignored)
│   ├── models/                 # All models stored here
│   └── output/                 # ComfyUI output directory
├── references/
│   ├── prompt-engineering.md
│   ├── style-systems.md
│   └── troubleshooting.md
└── outputs/                    # Your generated content
```

### Output Directory Structure (Per Project)

When generating videos, the workflow creates this structure:

```
outputs/my-project/
├── philosophy.md              # Production philosophy
├── style.json                 # Style configuration
├── scene-breakdown.md         # Scene plan
├── pipeline.json              # Execution pipeline (all prompts)
├── assets/
│   ├── characters/           # Character identity assets
│   ├── backgrounds/          # Environment references
│   └── styles/               # Style references
├── keyframes/                # Generated/extracted keyframes
│   ├── KF-A.png              # First keyframe (generated)
│   ├── KF-B.png              # Extracted from scene-01 (video-first)
│   └── KF-C.png              # Extracted from scene-02 (video-first)
├── scene-01/
│   └── video.mp4
└── scene-02/
    └── video.mp4
```

**Video-First Mode:** Only KF-A is generated traditionally. KF-B, KF-C, etc. are automatically extracted from the last frame of each video, ensuring perfect visual continuity between scenes.

**Keyframe-First Mode:** All keyframes are generated independently, then videos interpolate between them.

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

### Multi-Reference Keyframes Very Slow (30+ minutes)

If multi-reference keyframe generation (background + 2 characters) takes longer than expected:

1. **Ensure `--cache-none` is enabled**: The ComfyUI server must be started with `--cache-none` flag
   ```bash
   # Correct - uses --cache-none automatically
   python scripts/setup_comfyui.py --start

   # Or manually:
   python main.py --listen 0.0.0.0 --port 8188 --cache-none
   ```

2. **Why this happens**: On 10GB VRAM, the Qwen VL 7B text encoder (~8GB) and diffusion model (~12GB) cannot both fit in VRAM simultaneously. Without `--cache-none`, they compete for memory causing constant CPU↔GPU swapping.

3. **What `--cache-none` does**: Allows ComfyUI to unload the text encoder after encoding is complete, freeing ~8GB VRAM for the diffusion sampling stage.

See [references/troubleshooting.md](references/troubleshooting.md) for more solutions.

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
