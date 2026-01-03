# Diffusers Speed Optimization Plan

## Problem Analysis

**Current Issue:** With 10GB VRAM, the BF16 Qwen model (~40GB for BF16) triggers CPU offloading, resulting in 10-20 minute generation times.

**Root Causes:**
1. BF16 model requires ~40GB VRAM - far exceeds available 10GB
2. Standard diffusers CPU offload is extremely slow
3. Lightning LoRA reduces steps but doesn't reduce memory footprint
4. Diffusers is ~15% slower than ComfyUI even with adequate VRAM ([issue #12645](https://github.com/huggingface/diffusers/issues/12645))

## Options Analysis

### Option 1: Nunchaku (Recommended for 10GB VRAM)
**Memory: 3-4GB VRAM | Speed: Fast | Complexity: Medium**

Nunchaku uses INT4/FP4 quantization with smart per-layer offloading:
- Only loads one layer at a time to GPU
- 3-4GB VRAM requirement
- Works with diffusers pipeline API
- Auto-detects optimal precision

```python
from nunchaku import NunchakuQwenImageTransformer2DModel
transformer = NunchakuQwenImageTransformer2DModel.from_pretrained(
    "nunchaku-tech/nunchaku-qwen-image-edit/svdq-int4_r128-qwen-image-edit.safetensors"
)
pipeline = QwenImageEditPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit", transformer=transformer, torch_dtype=torch.bfloat16
)
transformer.set_offload(True, num_blocks_on_gpu=1)
```

**Pros:** Fastest for low VRAM, diffusers-compatible
**Cons:** Requires installing nunchaku package, potential quality loss from INT4

### Option 2: DiffSynth-Studio with FP8
**Memory: 4-16GB VRAM | Speed: Medium-Fast | Complexity: Medium**

Different framework with better memory management:
- Layer-by-layer offload to disk/CPU
- FP8 quantization (~16GB) or aggressive offload (~4GB)
- Different API (not diffusers)

```python
from diffsynth.pipelines.qwen_image import QwenImagePipeline, ModelConfig
pipe = QwenImagePipeline.from_pretrained(
    model_configs=[ModelConfig(model_id="Qwen/Qwen-Image", onload_dtype=torch.float8_e4m3fn, ...)]
)
```

**Pros:** Official Qwen support, FP8 quantization
**Cons:** Different API, learning curve, not diffusers

### Option 3: Pre-quantized FP8 + Lightning Fused Model
**Memory: ~16GB VRAM | Speed: Fast | Complexity: Low**

The `qwen_image_edit_2511_fp8_e4m3fn_scaled_lightning.safetensors` file is FP8 with Lightning baked in:
- 4 steps + FP8 = fast + smaller
- BUT still needs ~16GB VRAM (too much for 10GB)

**Pros:** Simple, fast generation
**Cons:** Still exceeds 10GB VRAM

### Option 4: Return to ComfyUI with GGUF
**Memory: 6-8GB VRAM | Speed: Medium | Complexity: High (setup)**

GGUF Q4_K_M format is ~14GB on disk, runs in ~8GB VRAM:
- Proven to work on user's hardware
- ComfyUI is faster than diffusers
- Already have working workflows

**Pros:** Known to work, smallest VRAM footprint
**Cons:** Back to ComfyUI complexity, JSON workflow management

### Option 5: Bitsandbytes INT8 Quantization (Runtime)
**Memory: ~20GB VRAM | Speed: Medium | Complexity: Low**

Load model with bitsandbytes 8-bit quantization:
```python
from transformers import BitsAndBytesConfig
bnb_config = BitsAndBytesConfig(load_in_8bit=True)
pipe = QwenImageEditPlusPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2511",
    quantization_config=bnb_config,
)
```

**Pros:** Simple integration, quality preserved
**Cons:** Still ~20GB needed, not enough for 10GB

## Recommendation for 10GB VRAM

**Primary: Option 1 - Nunchaku**
- Best VRAM efficiency (3-4GB)
- Maintains diffusers API compatibility
- Can combine with Lightning LoRA for 4-step generation

**Fallback: Option 4 - ComfyUI GGUF**
- If Nunchaku quality is insufficient
- Proven workflow exists

## Implementation Steps

1. Install Nunchaku: `pip install nunchaku`
2. Download Nunchaku quantized model (~4GB)
3. Update qwen_image.py to use NunchakuQwenImageTransformer2DModel
4. Configure per-layer offloading
5. Test with boxing keyframe generation
6. If quality acceptable, proceed with video generation

## References

- [Nunchaku Qwen-Image-Edit Documentation](https://nunchaku.tech/docs/nunchaku/usage/qwen-image-edit.html)
- [DiffSynth-Studio Qwen-Image](https://github.com/modelscope/DiffSynth-Studio/blob/main/docs/en/Model_Details/Qwen-Image.md)
- [Diffusers Quantization Blog](https://huggingface.co/blog/diffusers-quantization)
- [Qwen-Image-Lightning](https://github.com/ModelTC/Qwen-Image-Lightning)
- [LightX2V Qwen-Image-Edit-2511-Lightning](https://huggingface.co/lightx2v/Qwen-Image-Edit-2511-Lightning)
