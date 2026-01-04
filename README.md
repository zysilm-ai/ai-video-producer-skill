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
# Step 1: Generate character asset (neutral A-pose, clean background)
python scripts/asset_generator.py character \
  --name warrior \
  --description "A warrior in dramatic lighting, anime style, red armor" \
  --output outputs/assets/warrior.png

# Step 2: Generate pose skeleton from reference image
python scripts/asset_generator.py pose \
  --source references/charge_pose.jpg \
  --output outputs/assets/charge_skeleton.png

# Step 3: Generate keyframe with character + pose
python scripts/keyframe_generator.py \
  --prompt "Warrior charging forward, cape flowing, dramatic lighting" \
  --character outputs/assets/warrior.png \
  --pose outputs/assets/charge_skeleton.png \
  --output outputs/keyframes/KF-A.png

# Step 4: Generate a video from the keyframe
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

# Pose reference + skeleton (RECOMMENDED - generates clean image for reliable extraction)
python scripts/asset_generator.py pose-ref \
  --name [pose_name] \
  --pose "[pose description, e.g., 'fighting stance, fists raised']" \
  --output path/to/pose_ref.png \
  --extract-skeleton \
  --skeleton-output path/to/pose_skeleton.png

# Pose skeleton from existing image (may fail on complex images)
python scripts/asset_generator.py pose \
  --source path/to/reference_image.jpg \
  --output path/to/pose_skeleton.png

# Style reference
python scripts/asset_generator.py style \
  --name [style_name] \
  --description "[style description]" \
  --output path/to/style.png
```

### keyframe_generator.py

Generate keyframes using character assets and pose control.

```bash
python scripts/keyframe_generator.py \
  --prompt "Action/scene description" \
  --output path/to/keyframe.png \
  --character path/to/character.png      # Character identity (WHO)
  --pose path/to/pose_skeleton.png       # Pose skeleton (WHAT position)
  [--pose-image path/to/ref.jpg]         # Extract pose on-the-fly
  [--background path/to/background.png]  # Background reference
  [--control-strength 0.8]               # ControlNet strength
  [--preset low|medium|high]             # Resolution preset
  [--free-memory]                        # Clear VRAM before generation
```

**Key Principle:** Separate identity (--character) from pose (--pose) to generate the same character in dramatically different poses.

**Multi-Character Generation:**

```bash
# Two characters (up to 3 supported)
python scripts/keyframe_generator.py \
  --prompt "On the left: warrior attacking. On the right: ninja defending." \
  --character assets/warrior.png \
  --character assets/ninja.png \
  --pose assets/poses/combat_skeleton.png \
  --output keyframes/KF-battle.png

# Two characters with background reference
python scripts/keyframe_generator.py \
  --prompt "Warriors facing off in temple courtyard" \
  --background assets/backgrounds/temple.png \
  --character assets/warrior.png \
  --character assets/ninja.png \
  --pose assets/poses/standoff_skeleton.png \
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
│   ├── asset_generator.py      # Generate character/background/pose/style assets
│   ├── keyframe_generator.py   # Generate keyframes with identity+pose separation
│   ├── angle_transformer.py    # Transform keyframe camera angles
│   ├── wan_video_comfyui.py    # Video generation (ComfyUI)
│   ├── setup_comfyui.py        # ComfyUI setup and server management
│   ├── core.py                 # Shared generation utilities
│   ├── comfyui_client.py       # ComfyUI API client
│   ├── utils.py                # Shared utilities
│   └── workflows/              # ComfyUI workflow JSON files
│       ├── qwen_t2i.json       # Text-to-Image
│       ├── qwen_edit.json      # Edit with reference
│       ├── qwen_pose.json      # Pose-guided generation
│       ├── qwen_multiangle.json # Camera angle transformation
│       ├── dwpose_extract.json # Skeleton extraction
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

### Output Directory Structure (Per Project)

When generating videos, the workflow creates this structure:

```
outputs/my-project/
├── philosophy.md              # Production philosophy
├── style.json                 # Style configuration
├── scene-breakdown.md         # Scene plan with unique keyframes
├── assets.json                # Asset definitions
├── assets/
│   ├── characters/           # Character identity assets
│   ├── backgrounds/          # Environment references
│   ├── poses/                # Skeleton files
│   └── styles/               # Style references
├── keyframes/                # Centralized unique keyframes
│   ├── KF-A.png              # Scene 1 start
│   ├── KF-B.png              # Scene 1 end = Scene 2 start (SHARED)
│   └── KF-C.png              # Scene 2 end
├── scene-01/
│   └── video.mp4
└── scene-02/
    └── video.mp4
```

**Shared Keyframes:** Adjacent scenes share boundary keyframes for perfect continuity. For example, KF-B serves as both the end frame of Scene 1 and the start frame of Scene 2. Generate once, use in both scenes.

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
