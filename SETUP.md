# Setup Guide: WAN 2.2 Video + Qwen Image Edit 2511

This guide covers setting up the local environment for AI video generation using WAN 2.2 GGUF models and Qwen Image Edit 2511 for keyframes via ComfyUI.

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 3060 12GB | RTX 3080 10GB+ |
| VRAM | 10GB | 12GB+ |
| RAM | 16GB | 32GB |
| Storage | 50GB free | 100GB+ free |
| OS | Windows 10/11, Linux | Ubuntu 22.04+ |

## Step 1: Install ComfyUI

### Option A: Standalone (Recommended)

```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

### Option B: Using comfy-cli

```bash
pip install comfy-cli
comfy install
```

### Start ComfyUI

```bash
python main.py --listen 0.0.0.0 --port 8188
```

Verify it's running by visiting: http://localhost:8188

---

## Step 2: Install Required Custom Nodes

### Via ComfyUI Manager (Recommended)

1. Install ComfyUI Manager:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

2. Restart ComfyUI and use the Manager to install:
   - **ComfyUI-GGUF** (City96) - Required for GGUF models
   - **ComfyUI-WanVideoWrapper** (Kijai) - WAN model support
   - **ComfyUI-VideoHelperSuite** - Video export utilities
   - **ComfyUI_RH_Qwen-Image** - Qwen Image Edit 2511 support
   - **comfyui_controlnet_aux** - Pose preprocessors for ControlNet

### Manual Installation

```bash
cd ComfyUI/custom_nodes

# GGUF support
git clone https://github.com/city96/ComfyUI-GGUF.git

# WAN wrapper
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git

# Video utilities
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git

# Qwen Image Edit support
git clone https://github.com/Robinyo/ComfyUI_RH_Qwen-Image.git

# ControlNet preprocessors (for pose guidance)
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
```

Restart ComfyUI after installing nodes.

---

## Step 3: Download Models

### 3.1 WAN 2.2 GGUF Models (for Video Generation)

Download from [bullerwins/Wan2.2-I2V-A14B-GGUF](https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF):

For **10GB VRAM**, use Q4_K_M quantization:

```bash
# Create directories
mkdir -p ComfyUI/models/diffusion_models

# Download high-noise model
wget -P ComfyUI/models/diffusion_models/ \
  https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/wan2.2_i2v_high_noise_14B_Q4_K_M.gguf

# Download low-noise model
wget -P ComfyUI/models/diffusion_models/ \
  https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/wan2.2_i2v_low_noise_14B_Q4_K_M.gguf
```

**Alternative quantizations:**
| Quantization | VRAM | File |
|--------------|------|------|
| Q4_K_S | 8.75GB | `*_Q4_K_S.gguf` |
| Q4_K_M | 9.65GB | `*_Q4_K_M.gguf` |
| Q5_K_S | 10.1GB | `*_Q5_K_S.gguf` |

### 3.2 Text Encoder

```bash
mkdir -p ComfyUI/models/clip

# Download UMT5 text encoder (FP8 quantized)
wget -P ComfyUI/models/clip/ \
  https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors
```

### 3.3 VAE

```bash
mkdir -p ComfyUI/models/vae

# Download WAN VAE
wget -P ComfyUI/models/vae/ \
  https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors
```

### 3.4 Qwen Image Edit 2511 (for Keyframe Generation)

```bash
mkdir -p ComfyUI/models/unet
mkdir -p ComfyUI/models/clip
mkdir -p ComfyUI/models/vae

# Download Qwen Image Edit 2511 model (FP8 mixed)
wget -P ComfyUI/models/unet/ \
  https://huggingface.co/Comfy-Org/Qwen_Image_Edit_2511_ComfyUI_Repackaged/resolve/main/split_files/unet/qwen_image_edit_2511_fp8mixed.safetensors

# Download Qwen VL text encoder
wget -P ComfyUI/models/clip/ \
  https://huggingface.co/Comfy-Org/Qwen_Image_Edit_2511_ComfyUI_Repackaged/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors

# Download Qwen VAE
wget -P ComfyUI/models/vae/ \
  https://huggingface.co/Comfy-Org/Qwen_Image_Edit_2511_ComfyUI_Repackaged/resolve/main/split_files/vae/qwen_image_vae.safetensors
```

### 3.5 ControlNet Union (for Pose Guidance)

```bash
mkdir -p ComfyUI/models/controlnet

# Download Qwen-compatible ControlNet Union
wget -P ComfyUI/models/controlnet/ \
  https://huggingface.co/Comfy-Org/Qwen-Image-InstantX-ControlNets/resolve/main/split_files/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors
```

---

## Step 4: Verify Directory Structure

After setup, your ComfyUI models folder should look like:

```
ComfyUI/models/
├── diffusion_models/
│   └── wan2.2_i2v_low_noise_14B_Q4_K_M.gguf
├── unet/
│   └── qwen_image_edit_2511_fp8mixed.safetensors
├── clip/
│   ├── umt5_xxl_fp8_e4m3fn_scaled.safetensors
│   └── qwen_2.5_vl_7b_fp8_scaled.safetensors
├── vae/
│   ├── wan_2.1_vae.safetensors
│   └── qwen_image_vae.safetensors
├── controlnet/
│   └── Qwen-Image-InstantX-ControlNet-Union.safetensors
└── loras/
    └── Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors
```

---

## Step 5: Test Installation

### Test ComfyUI API

```python
import requests

response = requests.get("http://localhost:8188/system_stats")
if response.status_code == 200:
    print("ComfyUI is running!")
    print(response.json())
else:
    print("ComfyUI not accessible")
```

### Test Model Loading

1. Open ComfyUI web UI: http://localhost:8188
2. Create a simple workflow with WAN nodes
3. Verify models load without OOM errors

---

## Troubleshooting

### Out of Memory (OOM) Errors

1. Use smaller quantization (Q4_K_S instead of Q4_K_M)
2. Reduce resolution to 480p
3. Enable `--lowvram` flag when starting ComfyUI:
   ```bash
   python main.py --lowvram --listen 0.0.0.0 --port 8188
   ```

### Models Not Found

Ensure models are in correct directories:
- GGUF models → `models/diffusion_models/`
- CLIP/Text encoders → `models/clip/`
- VAE → `models/vae/`

### ComfyUI Won't Start

1. Check Python version (3.10-3.12 recommended)
2. Verify CUDA installation: `python -c "import torch; print(torch.cuda.is_available())"`
3. Check GPU driver is up to date

### Slow Generation

1. Install xformers: `pip install xformers`
2. Use sage attention if available
3. Consider Lightning LoRAs for faster inference

---

## Optional: Lightning LoRAs (4x Faster)

For faster generation (4 steps instead of 20+):

```bash
mkdir -p ComfyUI/models/loras

# Download Lightning LoRA
wget -P ComfyUI/models/loras/ \
  https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/wan2.2_i2v_lightning_lora.safetensors
```

---

## Environment Variables

Set these for the video skill scripts:

```bash
# ComfyUI server address (default)
export COMFYUI_HOST="127.0.0.1"
export COMFYUI_PORT="8188"
```

---

## Next Steps

Once setup is complete:
1. Verify ComfyUI is running on port 8188
2. Run the video skill to generate videos
3. Check `references/troubleshooting.md` for common issues
