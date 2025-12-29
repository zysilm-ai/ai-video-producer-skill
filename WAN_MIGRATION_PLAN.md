# Migration Plan: Google Gemini/Veo to WAN 2.2 GGUF

## Overview

Migrate the AI video production skill from Google Gemini/Veo APIs to WAN 2.2 GGUF models running locally via ComfyUI, enabling cost-free video generation on RTX 3080 10GB.

---

## Current Architecture

```
scripts/
├── gemini_image.py    # Image generation (Gemini API)
├── veo_video.py       # Video generation (Veo API)
├── status_checker.py  # Job monitoring
└── utils.py           # Shared utilities
```

**Current Capabilities:**
| Feature | Current Implementation |
|---------|----------------------|
| Text-to-Image | Gemini gemini-3-pro-image-preview |
| Reference Images | PIL Image passed to Gemini |
| Text-to-Video | Veo generate_videos |
| Image-to-Video | Veo with start_frame |
| Dual-frame (FLF) | Veo with start_frame + last_frame |
| Duration | Up to 8 seconds |
| Resolution | 720p/1080p |

---

## Target Architecture

```
scripts/
├── wan_image.py       # Image generation (Flux/SDXL via ComfyUI)
├── wan_video.py       # Video generation (WAN 2.2 GGUF via ComfyUI)
├── comfyui_client.py  # ComfyUI API client wrapper
├── status_checker.py  # Job monitoring (updated)
├── utils.py           # Shared utilities (updated)
└── workflows/
    ├── flux_t2i.json           # Text-to-image workflow
    ├── flux_t2i_reference.json # T2I with reference image
    ├── wan_i2v.json            # Image-to-video workflow
    ├── wan_flf2v.json          # First-Last-Frame workflow
    └── wan_t2v.json            # Text-to-video workflow
```

**Target Capabilities:**
| Feature | New Implementation |
|---------|-------------------|
| Text-to-Image | Flux.1 dev/schnell via ComfyUI |
| Reference Images | IP-Adapter or reference in prompt |
| Text-to-Video | WAN 2.2 T2V GGUF |
| Image-to-Video | WAN 2.2 I2V GGUF (Q4_K_M) |
| Dual-frame (FLF) | WAN 2.2 FLF2V via ComfyUI |
| Duration | 5 seconds per segment |
| Resolution | 480p/720p |

---

## Phase 1: ComfyUI Setup & Client

### 1.1 Prerequisites Document

Create `SETUP.md` with:
- ComfyUI installation instructions
- Required custom nodes:
  - ComfyUI-GGUF (City96)
  - ComfyUI-WanVideoWrapper (Kijai)
  - ComfyUI-VideoHelperSuite
- Model download links:
  - WAN 2.2 I2V GGUF (Q4_K_M high-noise + low-noise)
  - Text encoder: umt5_xxl_fp8_e4m3fn_scaled.safetensors
  - VAE: wan_2.1_vae.safetensors
  - Flux.1 schnell (for image generation)
- Directory structure for models

### 1.2 ComfyUI API Client

Create `comfyui_client.py`:

```python
class ComfyUIClient:
    def __init__(self, host="127.0.0.1", port=8188):
        self.base_url = f"http://{host}:{port}"

    def queue_prompt(self, workflow: dict) -> str:
        """Submit workflow and return prompt_id"""

    def get_history(self, prompt_id: str) -> dict:
        """Get execution history/status"""

    def get_image(self, filename: str, subfolder: str) -> bytes:
        """Download generated image"""

    def upload_image(self, image_path: str) -> dict:
        """Upload image for use in workflow"""

    def wait_for_completion(self, prompt_id: str, timeout: int) -> dict:
        """Poll until job completes"""
```

### 1.3 Workflow Templates

Create JSON workflow templates that can be parameterized:
- Load workflow JSON
- Replace placeholder values (prompt, paths, settings)
- Submit to ComfyUI API

---

## Phase 2: Image Generation

### 2.1 Create `wan_image.py`

Since WAN video models don't include image generation, use Flux via ComfyUI:

```python
def generate_image(
    prompt: str,
    output_path: str,
    style_ref: str | None = None,
    reference_images: list[str] | None = None,
    width: int = 1280,
    height: int = 720,
) -> str:
    """Generate image using Flux via ComfyUI"""
```

**Workflow options:**
1. **Flux.1 schnell** - Fast, 4-step generation
2. **Flux.1 dev** - Higher quality, more steps
3. **With IP-Adapter** - For reference image consistency

### 2.2 Reference Image Handling

For character/style consistency:
- Option A: IP-Adapter integration (requires additional model)
- Option B: Include reference description in prompt (simpler)
- Option C: Use ControlNet for structural consistency

**Recommendation:** Start with Option B (prompt-based), add IP-Adapter later if needed.

---

## Phase 3: Video Generation

### 3.1 Create `wan_video.py`

```python
def generate_video(
    prompt: str,
    output_path: str,
    start_frame: str | None = None,
    end_frame: str | None = None,
    style_ref: str | None = None,
    duration: int = 5,  # WAN default is 5 seconds
) -> str:
    """Generate video using WAN 2.2 GGUF via ComfyUI"""
```

**Mode detection:**
- No frames → Text-to-Video (wan_t2v.json)
- Start frame only → Image-to-Video (wan_i2v.json)
- Start + End frames → First-Last-Frame (wan_flf2v.json)

### 3.2 WAN 2.2 GGUF Workflow Components

For I2V and FLF2V workflows:

```
Nodes required:
├── UNETLoaderGGUF (high-noise model)
├── UNETLoaderGGUF (low-noise model)
├── CLIPLoader (umt5 text encoder)
├── VAELoader (wan_2.1_vae)
├── WanFirstLastFrameToVideo (for FLF2V)
├── WanImageToVideo (for I2V)
├── KSampler
└── SaveVideo
```

### 3.3 Duration Adjustment

Since WAN generates 5-second clips vs Veo's 8 seconds:
- Update `scene-breakdown.md` template to use 5-second scenes
- Or generate longer videos by chaining segments (advanced)

---

## Phase 4: SKILL.md Updates

### 4.1 Update Workflow Documentation

Modify SKILL.md:
- Change script references from `gemini_image.py` → `wan_image.py`
- Change script references from `veo_video.py` → `wan_video.py`
- Update duration guidelines (5 seconds per scene)
- Add ComfyUI prerequisite check
- Remove Google API key requirement
- Add ComfyUI server requirement

### 4.2 Update Scene Guidelines

| Total Video Length | Minimum Scenes | Recommended Scenes |
|--------------------|----------------|-------------------|
| 1-5 seconds | 1 | 1 |
| 6-10 seconds | 2 | 2 |
| 11-15 seconds | 3 | 3 |
| 16-20 seconds | 4 | 4 |
| 20+ seconds | 5+ | Break into 5s beats |

### 4.3 Add Setup Section

```markdown
## Prerequisites

Before using this skill, ensure:
1. ComfyUI is installed and running on port 8188
2. Required custom nodes are installed
3. WAN 2.2 GGUF models are downloaded
4. Flux model is available for image generation

See `SETUP.md` for detailed installation instructions.
```

---

## Phase 5: Testing & Validation

### 5.1 Test Cases

1. **Image Generation**
   - [ ] Text-to-image basic
   - [ ] Text-to-image with style.json
   - [ ] Multiple reference images (if IP-Adapter added)

2. **Video Generation**
   - [ ] Text-to-video (no frames)
   - [ ] Image-to-video (start frame only)
   - [ ] First-Last-Frame (both frames)
   - [ ] With style.json enhancement

3. **Full Workflow**
   - [ ] Complete 3-scene video (like KOF test)
   - [ ] Keyframe approval checkpoints work
   - [ ] Output file structure correct

### 5.2 Performance Benchmarks

Record on RTX 3080 10GB:
- Image generation time (Flux)
- Video generation time (WAN I2V)
- Video generation time (WAN FLF2V)
- Total workflow time for 3-scene video

---

## Implementation Order

```
Step 1: ComfyUI Setup
├── Write SETUP.md documentation
├── Create comfyui_client.py
└── Test API connectivity

Step 2: Image Generation
├── Create flux_t2i.json workflow
├── Create wan_image.py script
└── Test image generation

Step 3: Video Generation
├── Create wan_i2v.json workflow
├── Create wan_flf2v.json workflow
├── Create wan_video.py script
└── Test all video modes

Step 4: Integration
├── Update SKILL.md
├── Update utils.py if needed
├── Remove/deprecate Google scripts
└── Full workflow test

Step 5: Documentation
├── Update README.md
├── Finalize SETUP.md
└── Add troubleshooting guide
```

---

## File Changes Summary

| Action | File | Description |
|--------|------|-------------|
| CREATE | `SETUP.md` | Installation prerequisites |
| CREATE | `scripts/comfyui_client.py` | ComfyUI API wrapper |
| CREATE | `scripts/wan_image.py` | Image generation via Flux |
| CREATE | `scripts/wan_video.py` | Video generation via WAN |
| CREATE | `scripts/workflows/*.json` | ComfyUI workflow templates |
| UPDATE | `SKILL.md` | New script references, durations |
| UPDATE | `scripts/utils.py` | Add ComfyUI helpers |
| DEPRECATE | `scripts/gemini_image.py` | Keep for reference |
| DEPRECATE | `scripts/veo_video.py` | Keep for reference |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ComfyUI not running | Skill fails | Add server health check at start |
| VRAM OOM on 10GB | Generation fails | Use Q4_K_M, add memory tips |
| Longer generation times | User impatience | Add progress feedback |
| Image consistency lower | Visual quality | Document IP-Adapter as upgrade path |
| 5s vs 8s duration | More scenes needed | Update guidelines in SKILL.md |

---

## Success Criteria

1. Generate keyframe images locally (no API cost)
2. Generate I2V videos on RTX 3080 10GB
3. Generate FLF2V videos (dual keyframe mode)
4. Complete 3-scene video workflow end-to-end
5. Generation time under 10 minutes per scene
6. No VRAM out-of-memory errors
