# Keyframe Quality Improvement Report

**Date:** December 30, 2025
**Hardware:** NVIDIA RTX 3080 (10GB VRAM)
**Current Setup:** Flux Schnell Q4_K_S via ComfyUI

---

## Executive Summary

The current keyframe generation produces **inconsistent characters** between frames, making them unsuitable for video interpolation. The root cause is using Flux Schnell without consistency tools (IP-Adapter, ControlNet, PuLID).

**Key Recommendations:**
1. **Quick Fix:** Add PuLID-Flux + ControlNet to current Flux workflow
2. **Best Long-term:** Consider SD 3.5 Medium for mature ecosystem support
3. **Hybrid Approach:** Use Flux with full consistency stack (PuLID + ControlNet + IP-Adapter)

---

## Part 1: Problem Analysis

### Generated Keyframes Comparison

| Aspect | Start Frame | End Frame | Issue Severity |
|--------|-------------|-----------|----------------|
| **Face** | Bearded, long dark hair | Different face, shorter hair | **CRITICAL** |
| **Armor** | Dark leather/metal with orange accents | Plate armor with cape | **CRITICAL** |
| **Weapon** | Staff/spear raised | Sword pulled back | **CRITICAL** |
| **Background** | Battlefield with fires | Similar battlefield | Minor |
| **Style** | Cinematic, dramatic lighting | Similar cinematic style | Minor |

### Root Cause Analysis

The current `flux_t2i.json` workflow:
- Uses only text prompting (no image reference integration)
- Lacks IP-Adapter for style/character transfer
- Lacks ControlNet for structural consistency
- Lacks PuLID for face identity preservation
- Reference image upload exists but workflow doesn't use it

**Result:** Each generation is independent, producing different interpretations of the prompt.

---

## Part 2: Available Consistency Tools for Flux

### 2.1 PuLID-Flux (Face/Identity Consistency)

**Purpose:** Preserve facial identity across generations using a reference image.

**Capabilities:**
- 90%+ facial feature restoration
- Works with any pose/angle
- Maintains identity across styles
- Compatible with TeaCache and WaveSpeed for faster processing

**Models Required:**
| Model | Size | Source |
|-------|------|--------|
| pulid_flux_v0.9.1.safetensors | ~1GB | [Guozinan/PuLID](https://huggingface.co/guozinan/PuLID) |
| EVA02_CLIP_L_336_psz14_s6B.pt | ~1.7GB | CLIP Vision |

**ComfyUI Nodes:** [ComfyUI-PuLID-Flux](https://github.com/balazik/ComfyUI-PuLID-Flux)

**Best For:** Character consistency when face matters most.

Sources: [PuLID Flux II](https://www.runcomfy.com/comfyui-workflows/pulid-flux-ii-in-comfyui-consistent-character-ai-generation), [Flux Kontext PuLID](https://www.runcomfy.com/comfyui-workflows/flux-kontext-pulid-consistent-character-generation)

---

### 2.2 Flux ControlNet (Structural Consistency)

**Purpose:** Control composition, pose, and structure using reference images.

**Available Models (V3 - trained at 1024x1024):**
| Model | Size | Use Case |
|-------|------|----------|
| flux-canny-controlnet-v3.safetensors | ~3.9GB | Edge preservation |
| flux-depth-controlnet-v3.safetensors | ~3.9GB | Spatial/3D consistency |
| flux-hed-controlnet-v3.safetensors | ~3.9GB | Soft edge detection |

**ControlNet Union Pro 2.0 (Multi-Condition):**
- Supports: Canny, Depth, Soft Edge, Pose, Grayscale simultaneously
- Single model: 3.98GB
- Source: [Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0](https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0)

**Recommended Settings:**
- Control Weight: 0.7-0.9 for strong consistency
- Multi-ControlNet: Keep total weights ≤2.0 (e.g., Depth 0.8 + Canny 0.7)

Sources: [ComfyUI Flux ControlNet](https://docs.comfy.org/tutorials/flux/flux-1-controlnet), [XLabs ControlNet V3](https://openart.ai/workflows/ailab/flux-controlnet-v3-canny-depth-hed/1VE0TT4f8ohI8fQp6wNb)

---

### 2.3 Flux IP-Adapter (Style/Character Transfer)

**Purpose:** Transfer style and character appearance from reference images.

**Available Models:**
| Model | Training | Status |
|-------|----------|--------|
| XLabs IP-Adapter V1 | 50K steps | Stable |
| XLabs IP-Adapter V2 | 500K steps | Better quality |
| Shakker-Labs IP-Adapter | Variable | Character focus |

**Limitations (Current State):**
- Still in beta - may require multiple attempts
- Not suitable for fine-grained style transfer yet
- Trade-offs between content leakage and style transfer
- Limited diversity in outputs

**Sources:** [XLabs IP-Adapter V2](https://huggingface.co/XLabs-AI/flux-ip-adapter-v2), [Shakker-Labs IPAdapter](https://github.com/Shakker-Labs/ComfyUI-IPAdapter-Flux)

---

## Part 3: Alternative Model Comparison

### 3.1 Stable Diffusion 3.5 Medium (2.5B Parameters)

**VRAM:** Fits natively on RTX 3080 10GB (no quantization needed)

**Pros:**
- Full ControlNet support (official models)
- Mature IP-Adapter ecosystem (via SDXL adapters)
- Well-documented AnimateDiff integration
- Free commercial license (up to $1M revenue)
- Designed for consumer hardware

**Cons:**
- Less photorealistic than Flux
- IP-Adapter support still developing (mostly SDXL-based)
- ControlNet variants for Medium still forthcoming

**Models:**
| Model | Size | Source |
|-------|------|--------|
| sd3.5_medium.safetensors | ~5GB | [stabilityai](https://huggingface.co/stabilityai/stable-diffusion-3.5-medium) |

**Best For:** Complete video workflows with maximum tooling support.

Sources: [SD 3.5 Medium Launch](https://dataconomy.com/2024/11/01/stable-diffusion-3-5-medium-is-launched/), [SD 3.5 ComfyUI Tutorial](https://comfyui-wiki.com/en/tutorial/advanced/stable-diffusion-3-5-comfyui-workflow)

---

### 3.2 Stable Diffusion 3.5 Large Q4 GGUF (8B Parameters)

**VRAM:** Q4 quantization fits in 8GB (some quality loss)

**Pros:**
- Better quality than Medium
- Official ControlNet models available (Canny, Depth, Blur)
- 8B parameters = more complex understanding

**Cons:**
- Q4 quantization loses some detail
- Q8 needs 16GB VRAM
- Slower than Medium

**Models:**
| Model | Quantization | Size | Quality |
|-------|--------------|------|---------|
| sd3.5_large-Q4_K_M.gguf | Q4 | ~5GB | Good (minor loss) |
| sd3.5_large-Q8_0.gguf | Q8 | ~9GB | Near-lossless |

**Source:** [city96/stable-diffusion-3.5-large-gguf](https://huggingface.co/city96/stable-diffusion-3.5-large-gguf)

---

### 3.3 HiDream-I1 (17B Parameters)

**VRAM:** NF4 quantization required for 10GB

**Pros:**
- Best overall image quality (benchmark leader)
- Superior prompt adherence
- MIT License (fully open)

**Cons:**
- **No ControlNet implementation**
- **No IP-Adapter support**
- **No video workflow integration**
- Slow generation times

**Recommendation:** NOT suitable for video keyframe work. Use for static images only.

---

## Part 4: Model Comparison Summary

| Criteria | Flux Schnell | SD 3.5 Medium | SD 3.5 Large Q4 | HiDream-I1 |
|----------|--------------|---------------|-----------------|------------|
| **VRAM (10GB)** | ✅ Native | ✅ Native | ✅ Q4 | ✅ NF4 |
| **Image Quality** | ★★★★☆ | ★★★☆☆ | ★★★★☆ | ★★★★★ |
| **ControlNet** | ✅ V3 models | ✅ Official | ✅ Official | ❌ None |
| **IP-Adapter** | ⚠️ Beta | ⚠️ SDXL-based | ⚠️ SDXL-based | ❌ None |
| **PuLID** | ✅ Available | ❌ None | ❌ None | ❌ None |
| **Generation Speed** | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ |
| **Video Ecosystem** | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ★☆☆☆☆ |
| **License** | Apache 2.0 | Community | Community | MIT |

**Winner for Video Keyframes:** Flux Schnell with PuLID + ControlNet OR SD 3.5 Medium

---

## Part 5: Recommended Improvements

### Option A: Enhance Current Flux Setup (Recommended)

**Additional Downloads Required (~10GB):**

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| PuLID | pulid_flux_v0.9.1.safetensors | ~1GB | Face consistency |
| CLIP Vision | EVA02_CLIP_L_336_psz14_s6B.pt | ~1.7GB | PuLID requirement |
| ControlNet | flux-controlnet-union-pro-2.0 | ~4GB | Multi-condition control |
| IP-Adapter | flux-ip-adapter-v2 | ~2GB | Style transfer |

**Custom Nodes Required:**
```bash
# PuLID-Flux
git clone https://github.com/balazik/ComfyUI-PuLID-Flux custom_nodes/ComfyUI-PuLID-Flux

# ControlNet (if not using XLabs)
git clone https://github.com/Shakker-Labs/ComfyUI-IPAdapter-Flux custom_nodes/ComfyUI-IPAdapter-Flux
```

**Workflow Changes:**
1. Generate first keyframe with base prompt
2. Use PuLID with first keyframe as face reference for subsequent frames
3. Use ControlNet Depth to maintain spatial consistency
4. Use IP-Adapter for style consistency (lower weight ~0.3-0.5)

**Expected Improvement:** 70-80% character consistency

---

### Option B: Switch to SD 3.5 Medium

**Why Consider:**
- Most mature ecosystem for character consistency
- Native fit on 10GB VRAM
- Better documented workflows
- Official ControlNet support coming

**Downloads Required (~12GB):**

| Component | Model | Size |
|-----------|-------|------|
| Base Model | sd3.5_medium.safetensors | ~5GB |
| ControlNet Canny | sd3.5_large_controlnet_canny | ~2GB |
| ControlNet Depth | sd3.5_large_controlnet_depth | ~2GB |
| Text Encoders | T5/CLIP | ~3GB |

**Limitation:** IP-Adapter for SD3.5 specifically is still developing. Most workflows use SDXL adapters.

---

### Option C: Hybrid Approach (Best Quality)

Use different models for different purposes:

| Task | Model | Reason |
|------|-------|--------|
| First keyframe | Flux Schnell | Fast, high quality |
| Face reference | PuLID extraction | Capture identity |
| Subsequent keyframes | Flux + PuLID + ControlNet | Maintain consistency |
| Complex scenes | SD 3.5 Medium | Better multi-object handling |

---

## Part 6: Implementation Priority

### Phase 1: Quick Wins (Immediate)

1. **Add PuLID-Flux** - Biggest impact for character consistency
2. **Add ControlNet Depth** - Maintain spatial relationships
3. **Update workflow** to use reference images properly

### Phase 2: Enhanced Pipeline (Next)

1. Add IP-Adapter V2 for style consistency
2. Implement multi-keyframe workflow with progressive refinement
3. Add ControlNet Union Pro for multi-condition control

### Phase 3: Alternative Exploration (Future)

1. Test SD 3.5 Medium when IP-Adapter support matures
2. Evaluate HiDream-I1 for hero shots (single images)
3. Monitor Flux IP-Adapter development

---

## Part 7: Updated Model Downloads for setup_comfyui.py

```python
# Add to MODELS dictionary for character consistency
CONSISTENCY_MODELS = {
    # PuLID for face consistency
    "pulid/pulid_flux_v0.9.1.safetensors": {
        "url": "https://huggingface.co/guozinan/PuLID/resolve/main/pulid_flux_v0.9.1.safetensors",
        "size_gb": 1.0,
        "required": False,  # Optional enhancement
    },
    # ControlNet Union Pro (multi-condition)
    "controlnet/flux-controlnet-union-pro-2.0.safetensors": {
        "url": "https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro-2.0/resolve/main/diffusion_pytorch_model.safetensors",
        "size_gb": 4.0,
        "required": False,
    },
    # IP-Adapter V2
    "ipadapter/flux-ip-adapter-v2.safetensors": {
        "url": "https://huggingface.co/XLabs-AI/flux-ip-adapter-v2/resolve/main/flux-ip-adapter-v2.safetensors",
        "size_gb": 2.0,
        "required": False,
    },
}
```

---

## Conclusion

### Current State
- Flux Schnell produces high-quality individual images
- Lacks consistency tools = different characters each generation
- Reference image feature not integrated into workflow

### Recommended Action
**Implement Option A (Enhance Flux):**
1. Add PuLID-Flux for face/identity consistency
2. Add ControlNet Depth for structural consistency
3. Create new workflow: `flux_consistent_keyframes.json`
4. Update `flux_image.py` to support consistency modes

### Expected Outcome
- 70-80% character consistency between keyframes
- Same face, armor, weapon across frames
- Suitable for WAN 2.2 video interpolation

---

## References

- [PuLID Flux II Workflow](https://www.runcomfy.com/comfyui-workflows/pulid-flux-ii-in-comfyui-consistent-character-ai-generation)
- [Flux ControlNet V3](https://openart.ai/workflows/ailab/flux-controlnet-v3-canny-depth-hed/1VE0TT4f8ohI8fQp6wNb)
- [XLabs IP-Adapter V2](https://huggingface.co/XLabs-AI/flux-ip-adapter-v2)
- [SD 3.5 Large GGUF](https://huggingface.co/city96/stable-diffusion-3.5-large-gguf)
- [ComfyUI Flux ControlNet Docs](https://docs.comfy.org/tutorials/flux/flux-1-controlnet)
- [Consistent Characters Guide](https://learn.runcomfy.com/create-consistent-characters-with-controlnet-ipadapter)

---

*Report generated: December 30, 2025*
