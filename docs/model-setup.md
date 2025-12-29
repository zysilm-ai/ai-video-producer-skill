# Model Setup Guide

This guide covers all models required for the AI Video Producer skill.

## Overview

| Model Type | Purpose | Auto-Download | Manual Required |
|------------|---------|---------------|-----------------|
| WAN 2.2 GGUF | Video generation | Yes | No |
| Flux GGUF | Keyframe generation | Yes | No |
| Flux VAE | Image decoding | **No** | **Yes** |
| UMT5 Text Encoder | Text encoding | Yes | No |
| WAN VAE | Video decoding | Yes | No |
| CLIP Text Encoder | Flux text encoding | Yes | No |
| WAN ControlNet | Video consistency (optional) | **No** | **Yes** |

---

## Required Models

### 1. WAN 2.2 GGUF Models (Video Generation)

**Location**: `{comfyui}/models/diffusion_models/`

| File | Size | Purpose |
|------|------|---------|
| `wan2.2_i2v_high_noise_14B_Q4_K_M.gguf` | ~8GB | High noise expert |
| `wan2.2_i2v_low_noise_14B_Q4_K_M.gguf` | ~8GB | Low noise expert |

**Source**: https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF

**Auto-downloaded by setup script.**

---

### 2. Flux GGUF Model (Keyframe Generation)

**Location**: `{comfyui}/models/unet/`

| File | Size | Purpose |
|------|------|---------|
| `flux1-schnell-Q4_K_S.gguf` | ~6GB | Fast image generation |

**Source**: https://huggingface.co/city96/FLUX.1-schnell-gguf

**Auto-downloaded by setup script.**

---

### 3. Flux VAE (MANUAL DOWNLOAD REQUIRED)

**Location**: `{comfyui}/models/vae/`

| File | Size | Purpose |
|------|------|---------|
| `ae.safetensors` | ~300MB | Flux image decoding |

**Source**: https://huggingface.co/black-forest-labs/FLUX.1-schnell/blob/main/ae.safetensors

**Why manual?** Requires HuggingFace authentication (accept model license).

**Steps:**
1. Go to https://huggingface.co/black-forest-labs/FLUX.1-schnell
2. Accept the license agreement
3. Log in to HuggingFace
4. Download `ae.safetensors` from the Files tab
5. Move to `{comfyui}/models/vae/ae.safetensors`

---

### 4. Text Encoders

**Location**: `{comfyui}/models/clip/`

| File | Size | Purpose |
|------|------|---------|
| `t5xxl_fp8_e4m3fn.safetensors` | ~4.6GB | Flux text encoding |
| `clip_l.safetensors` | ~250MB | Flux CLIP encoding |

**Location**: `{comfyui}/models/text_encoders/` or `{comfyui}/models/clip/`

| File | Size | Purpose |
|------|------|---------|
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | ~2GB | WAN text encoding |

**Auto-downloaded by setup script.**

---

### 5. WAN VAE

**Location**: `{comfyui}/models/vae/`

| File | Size | Purpose |
|------|------|---------|
| `wan_2.1_vae.safetensors` | ~300MB | WAN video decoding |

**Source**: https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged

**Auto-downloaded by setup script.**

---

## Optional Models

### 6. WAN ControlNet (MANUAL DOWNLOAD)

**Location**: `{comfyui}/models/controlnet/`

ControlNet provides structural guidance during video generation for better consistency.

| File | Size | Purpose |
|------|------|---------|
| `wan2.2-ti2v-5b-controlnet-depth-v1/diffusion_pytorch_model.safetensors` | ~700MB | Depth-based control |

**Source**: https://huggingface.co/TheDenk/wan2.2-ti2v-5b-controlnet-depth-v1

**Steps:**
1. Go to the HuggingFace URL above
2. Download `diffusion_pytorch_model.safetensors`
3. Create folder: `{comfyui}/models/controlnet/wan2.2-ti2v-5b-controlnet-depth-v1/`
4. Move the file into that folder

**Other ControlNet options:**
- `TheDenk/wan2.2-ti2v-5b-controlnet-tile-v1` - Tile-based control
- `TheDenk/wan2.2-ti2v-5b-controlnet-canny-v1` - Edge detection control
- `TheDenk/wan2.2-ti2v-5b-controlnet-hed-v1` - HED edge control

---

## Directory Structure

After setup, your ComfyUI models folder should look like:

```
{comfyui}/models/
├── diffusion_models/
│   ├── wan2.2_i2v_high_noise_14B_Q4_K_M.gguf
│   └── wan2.2_i2v_low_noise_14B_Q4_K_M.gguf
├── unet/
│   └── flux1-schnell-Q4_K_S.gguf
├── clip/
│   ├── t5xxl_fp8_e4m3fn.safetensors
│   └── clip_l.safetensors
├── vae/
│   ├── ae.safetensors              # MANUAL DOWNLOAD
│   └── wan_2.1_vae.safetensors
├── clip_vision/
│   └── sigclip_vision_patch14_384.safetensors
└── controlnet/                      # OPTIONAL
    └── wan2.2-ti2v-5b-controlnet-depth-v1/
        └── diffusion_pytorch_model.safetensors
```

---

## Validation

Run the validation script to check which models are present:

```bash
python scripts/validate_setup.py
```

This will output:
- Which models are found
- Which models are missing
- Instructions for manual downloads

---

## Troubleshooting

### Model Not Found Errors

If ComfyUI reports a model not found:
1. Check the file is in the correct directory
2. Verify the filename matches exactly (case-sensitive on Linux)
3. Restart ComfyUI after adding new models

### Corrupted Downloads

If a model file is corrupted:
1. Delete the corrupted file
2. Re-download from the source
3. Verify file size matches expected size

**Expected file sizes:**
| File | Expected Size |
|------|---------------|
| `ae.safetensors` | ~300MB |
| `t5xxl_fp8_e4m3fn.safetensors` | ~4.6GB |
| `wan2.2_i2v_high_noise_14B_Q4_K_M.gguf` | ~8GB |
| `wan2.2_i2v_low_noise_14B_Q4_K_M.gguf` | ~8GB |

### Authentication Errors

For HuggingFace authenticated downloads:
1. Create a HuggingFace account
2. Accept the model license on the model page
3. Generate an access token at https://huggingface.co/settings/tokens
4. Use the token when prompted or set `HF_TOKEN` environment variable
