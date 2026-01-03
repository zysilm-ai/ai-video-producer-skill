# Diffusers Migration Research

**Date:** 2026-01-02
**Goal:** Determine if `diffusers` library can replace ComfyUI for all workflows

---

## Current ComfyUI Workflows Analysis

### Qwen Image Edit 2511 Workflows

| Workflow | File | Nodes Used | Purpose |
|----------|------|------------|---------|
| **T2I** | `qwen_t2i.json` | UNETLoader, CLIPLoader, VAELoader, TextEncodeQwenImageEditPlus, EmptyQwenImageLayeredLatentImage, ModelSamplingAuraFlow, KSampler, VAEDecode | Text-to-Image generation |
| **Edit** | `qwen_edit.json` | Same + LoadImage for reference | Image editing with 1 reference |
| **Pose** | `qwen_pose.json` | Same + ControlNetLoader, SetUnionControlNetType, OpenposePreprocessor, ControlNetApplySD3 | Pose-guided generation with ControlNet |

**Key Qwen Parameters:**
- `shift`: 4.0-5.0 (ModelSamplingAuraFlow - flow matching)
- `steps`: 20
- `cfg`: 1.0 (flow matching models use low CFG)
- `sampler`: euler
- `scheduler`: simple
- Resolution: 832x480 (medium preset)

### WAN 2.2 Video Workflows

| Workflow | File | Nodes Used | Purpose |
|----------|------|------------|---------|
| **I2V** | `wan_i2v.json` | UnetLoaderGGUF, ModelSamplingSD3, CLIPLoader, LoraLoader (LightX2V), VAELoader, WanImageToVideo, KSampler, VAEDecode, VHS_VideoCombine | Image-to-Video |
| **FLF2V** | `wan_flf2v.json` | Same + WanFirstLastFrameToVideo | First-Last-Frame-to-Video |

**Key WAN Parameters:**
- `shift`: 8.0 (ModelSamplingSD3)
- `steps`: 8 (with LightX2V distillation LoRA)
- `cfg`: 1.0
- `lora_strength`: 1.25 (LightX2V)
- `sampler`: uni_pc
- `length`: 81 frames (~5 seconds at 16fps)
- Resolution: 832x480

---

## Diffusers Equivalent Pipelines

### Qwen Image Edit 2511

| Feature | ComfyUI | Diffusers | Status |
|---------|---------|-----------|--------|
| T2I | `qwen_t2i.json` | `QwenImageEditPlusPipeline` | **SUPPORTED** |
| Edit (1 ref) | `qwen_edit.json` | `QwenImageEditPlusPipeline` with `image=[img]` | **SUPPORTED** |
| Edit (multi-ref) | Not implemented | `QwenImageEditPlusPipeline` with `image=[img1, img2, img3]` | **NATIVE - UP TO 3 IMAGES** |
| Pose ControlNet | `qwen_pose.json` | `QwenImageControlNetPipeline` + `QwenImageControlNetModel` | **SUPPORTED** |

**Diffusers Qwen Example:**
```python
from diffusers import QwenImageEditPlusPipeline

pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511", torch_dtype=torch.bfloat16
)
pipe.to("cuda")

# Multi-image reference - NATIVE SUPPORT!
output = pipe(
    image=[background_img, character_img],  # Up to 3 images
    prompt="Boxer in the ring",
    true_cfg_scale=4.0,
    num_inference_steps=40,
)
```

**ControlNet Pose Example:**
```python
from diffusers import QwenImageControlNetPipeline, QwenImageControlNetModel

controlnet = QwenImageControlNetModel.from_pretrained(
    "InstantX/Qwen-Image-ControlNet-Union", torch_dtype=torch.bfloat16
)
pipe = QwenImageControlNetPipeline.from_pretrained(
    "Qwen/Qwen-Image", controlnet=controlnet, torch_dtype=torch.bfloat16
)
# controlnet_conditioning_scale: 0.8-1.0 for pose
```

### WAN 2.x Video Generation

| Feature | ComfyUI | Diffusers | Status |
|---------|---------|-----------|--------|
| T2V | Not in our workflows | `WanPipeline` | **SUPPORTED** |
| I2V | `wan_i2v.json` | `WanImageToVideoPipeline` | **SUPPORTED** |
| FLF2V | `wan_flf2v.json` | `WanImageToVideoPipeline` with `last_image=` | **SUPPORTED** |
| V2V | Not in our workflows | `WanVideoToVideoPipeline` | **SUPPORTED** |
| VACE | Not in our workflows | `WanVACEPipeline` | **SUPPORTED** |
| Animate | Not in our workflows | `WanAnimatePipeline` | **SUPPORTED** |
| LightX2V LoRA | `wan_i2v.json` | `pipe.load_lora_weights()` | **SUPPORTED** |

**Diffusers WAN I2V Example:**
```python
from diffusers import WanImageToVideoPipeline, AutoencoderKLWan
from diffusers.utils import export_to_video, load_image

vae = AutoencoderKLWan.from_pretrained(model_id, subfolder="vae", torch_dtype=torch.float32)
pipe = WanImageToVideoPipeline.from_pretrained(model_id, vae=vae, torch_dtype=torch.bfloat16)
pipe.to("cuda")

output = pipe(
    image=start_frame,
    prompt="Boxer throwing a punch",
    height=480, width=832,
    num_frames=81,
    guidance_scale=5.0,
).frames[0]
export_to_video(output, "output.mp4", fps=16)
```

**Diffusers FLF2V Example:**
```python
output = pipe(
    image=first_frame,
    last_image=last_frame,  # Enable FLF2V mode
    prompt="...",
    guidance_scale=5.5,
).frames[0]
```

---

## GGUF / Low VRAM Support

| Approach | ComfyUI | Diffusers | Notes |
|----------|---------|-----------|-------|
| GGUF Models | `UnetLoaderGGUF` node | `GGUFQuantizationConfig` | Both support GGUF |
| FP8 Quantization | Native | `PipelineQuantizationConfig` | Both support FP8 |
| CPU Offloading | Manual | `enable_sequential_cpu_offload()` | Diffusers more automated |
| Group Offloading | Manual | `apply_group_offloading()` | Advanced memory optimization |

**Diffusers GGUF Example:**
```python
from diffusers import QwenImageTransformer2DModel, GGUFQuantizationConfig

transformer = QwenImageTransformer2DModel.from_single_file(
    "path/to/model.gguf",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16)
)
```

---

## Feature Comparison Summary

| Feature | ComfyUI | Diffusers | Winner |
|---------|---------|-----------|--------|
| **Multi-image Reference** | 1 ref only (our scripts) | Up to 3 native | **Diffusers** |
| **ControlNet Pose** | Supported | Supported | Tie |
| **WAN I2V** | Supported | Supported | Tie |
| **WAN FLF2V** | Supported | Supported | Tie |
| **WAN Animate** | Not implemented | Supported | **Diffusers** |
| **GGUF Support** | Native | Supported | Tie |
| **LightX2V LoRA** | Native | Supported | Tie |
| **Memory Optimization** | Manual | Automated APIs | **Diffusers** |
| **Server Dependency** | Requires running server | No server needed | **Diffusers** |
| **Stability** | Server can hang/crash | Direct Python | **Diffusers** |

---

## Recommendation

### **Migrate to Diffusers**

**Advantages:**
1. **No server dependency** - Direct Python execution, no ComfyUI hanging
2. **Native multi-image support** - Up to 3 reference images for Qwen
3. **Better memory management** - Built-in offloading APIs
4. **More features** - WanAnimate, VACE, V2V not in current ComfyUI scripts
5. **Simpler code** - Single pipeline call vs. workflow JSON manipulation

**Migration Steps:**
1. Install diffusers from git: `pip install git+https://github.com/huggingface/diffusers`
2. Create `qwen_image_diffusers.py` - Replace `qwen_image.py`
3. Create `wan_video_diffusers.py` - Replace `wan_video.py`
4. Download models from HuggingFace instead of GGUF
5. Update SKILL.md to use new scripts

**VRAM Considerations:**
- Full BF16 models require more VRAM than GGUF quantized
- Use FP8 or enable offloading for 10GB cards
- DiffSynth-Studio offers 4GB VRAM inference option

---

## Sources

- [Diffusers WAN Documentation](https://huggingface.co/docs/diffusers/en/api/pipelines/wan)
- [Qwen-Image-Edit-2511 HuggingFace](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)
- [InstantX ControlNet Union](https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union)
- [Wan2.2-I2V-A14B-Diffusers](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B-Diffusers)
- [Wan2.1-FLF2V-14B-720P-diffusers](https://huggingface.co/Wan-AI/Wan2.1-FLF2V-14B-720P-diffusers)
- [WanLM/Qwen-Image GitHub](https://github.com/QwenLM/Qwen-Image)
- [Wan-Video/Wan2.2 GitHub](https://github.com/Wan-Video/Wan2.2)
