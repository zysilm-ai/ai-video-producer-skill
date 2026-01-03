# Setup Guide: WAN 2.2 Video + Qwen Image Edit 2511 (Diffusers)

This guide covers setting up the local environment for AI video generation using WAN 2.2 and Qwen Image Edit 2511 via HuggingFace diffusers.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 3060 12GB | RTX 3080 10GB+ |
| VRAM | 10GB | 12GB+ |
| RAM | 16GB | 32GB |
| Storage | 60GB free | 100GB+ free |
| OS | Windows 10/11, Linux | Ubuntu 22.04+ |
| Python | 3.10+ | 3.11 |

---

## Quick Setup (Automatic)

```bash
cd gemini-video-producer-skill

# Install Python dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA 12.4
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Check setup and download models
python scripts/setup_diffusers.py --download
```

That's it! The setup script will download all required models from HuggingFace.

---

## Step-by-Step Setup

### Step 1: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install base requirements
pip install -r requirements.txt
```

### Step 2: Install PyTorch with CUDA

Choose the appropriate command for your CUDA version:

```bash
# CUDA 12.4 (recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 3: Verify CUDA

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Expected output:
```
CUDA available: True
Device: NVIDIA GeForce RTX 3080
```

### Step 4: Download Models

```bash
# Check current status
python scripts/setup_diffusers.py --check

# Download required models (~50GB)
python scripts/setup_diffusers.py --download

# Or download all including optional ControlNet (~55GB)
python scripts/setup_diffusers.py --download-all
```

---

## Model Details

### Required Models

| Model | HuggingFace ID | Size | Purpose |
|-------|----------------|------|---------|
| WAN 2.2 I2V | `Wan-AI/Wan2.2-I2V-A14B-Diffusers` | ~28GB | Video generation |
| LightX2V LoRA | `lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v` | ~0.7GB | Fast 8-step generation |
| Qwen Image Edit | `Qwen/Qwen-Image-Edit-2511` | ~20GB | Keyframe generation |

### Optional Models

| Model | HuggingFace ID | Size | Purpose |
|-------|----------------|------|---------|
| ControlNet Union | `InstantX/Qwen-Image-ControlNet-Union` | ~3.5GB | Pose-guided generation |

### Model Cache Location

Models are stored in the `models/` directory within this repository:

```
gemini-video-producer-skill/
└── models/
    └── hub/
        ├── models--Wan-AI--Wan2.2-I2V-A14B-Diffusers/
        ├── models--Qwen--Qwen-Image-Edit-2511/
        ├── models--lightx2v--Wan2.1-I2V-14B-480P-StepDistill.../
        └── models--InstantX--Qwen-Image-ControlNet-Union/
```

This directory is gitignored and keeps models local to the project.

---

## Verify Installation

```bash
# Full validation
python scripts/validate_diffusers.py

# Detailed output
python scripts/validate_diffusers.py --detailed

# JSON output (for automation)
python scripts/validate_diffusers.py --json
```

Expected output:
```
[+] Python: 3.11.x
[+] torch: 2.x.x
[+] diffusers: 0.31.x
[+] CUDA: NVIDIA GeForce RTX 3080
[+] VRAM: 10.0GB
[+] Qwen Image Edit 2511 (20.5GB)
[+] WAN 2.2 I2V 14B (28.0GB)
[+] LightX2V LoRA (0.7GB)
[+] Setup complete! Ready for generation.
```

---

## Memory Optimization

The diffusers pipeline automatically optimizes memory usage based on your VRAM:

| VRAM | Optimization Applied | Notes |
|------|---------------------|-------|
| <8GB | Sequential CPU offload | Slowest, but works |
| 8-12GB | Model CPU offload | Good balance |
| 12-16GB | Attention slicing | Fast |
| 16GB+ | Full GPU | Fastest |

You can also use resolution presets:

| Preset | Resolution | Frames | VRAM Usage |
|--------|------------|--------|------------|
| low | 640x384 | 49 | ~8GB |
| medium | 832x480 | 81 | ~10GB |
| high | 1280x720 | 81 | ~16GB |

---

## Troubleshooting

### Out of Memory (OOM) Errors

1. Use lower resolution preset:
   ```bash
   python scripts/wan_video.py --preset low ...
   ```

2. The pipeline automatically applies offloading, but you can force aggressive mode by reducing VRAM detection.

### Models Not Downloading

1. Check internet connection
2. Try logging in to HuggingFace:
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   ```

3. Some models may require accepting terms on HuggingFace website first.

### CUDA Not Available

1. Check NVIDIA driver: `nvidia-smi`
2. Reinstall PyTorch with CUDA:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

### Slow Generation

1. Ensure LightX2V LoRA is loaded (check with `validate_diffusers.py`)
2. Install xformers for memory-efficient attention:
   ```bash
   pip install xformers
   ```

### Import Errors

Make sure you're using the latest diffusers:
```bash
pip install --upgrade diffusers transformers accelerate
```

---

## Environment Variables

Optional environment variables:

```bash
# Disable progress bars (for CI/scripts)
export HF_HUB_DISABLE_PROGRESS_BARS=1

# Offline mode (use only cached models)
export HF_HUB_OFFLINE=1
```

Note: `HF_HOME` is automatically set to `models/` by the scripts.

---

## Next Steps

Once setup is complete:
1. Run `python scripts/validate_diffusers.py` to confirm everything works
2. Try generating a test image: `python scripts/qwen_image.py --prompt "A beautiful sunset" --output test.png`
3. Check `references/troubleshooting.md` for additional help
