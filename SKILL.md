---
name: ai-video-producer
description: >
  Complete AI video production workflow using WAN 2.2 and SD 3.5 models via ComfyUI.
  Creates any video type: promotional, educational, narrative, social media,
  animations, game trailers, music videos, product demos, and more. Use when
  users want to create videos with AI, need help with video storyboarding,
  keyframe generation, or video prompt writing. Follows a philosophy-first
  approach: establish visual style and production philosophy, then execute
  scene by scene with user feedback at each stage. Runs locally on RTX 3080+.
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion, TodoWrite
---

# AI Video Producer

Create professional AI-generated videos through a structured, iterative workflow using local models.

## Prerequisites & Auto-Setup

**This skill requires ComfyUI with WAN 2.2 models. The setup script handles everything automatically.**

### First-Time Setup (Automatic)

If ComfyUI is not detected, run the auto-setup script:

```bash
# Full automatic setup (~33GB download)
python {baseDir}/scripts/setup_comfyui.py

# Check setup status
python {baseDir}/scripts/setup_comfyui.py --check

# Start ComfyUI server
python {baseDir}/scripts/setup_comfyui.py --start
```

The setup script will:
1. Clone and configure ComfyUI
2. Install required custom nodes (ComfyUI-GGUF, VideoHelperSuite, ComfyUI-Manager)
3. Download WAN 2.2 GGUF model (Q4_K_M for 10GB VRAM)
4. Download UMT5-XXL text encoder
5. Download LightX2V distillation LoRA (enables fast 8-step generation)
6. Install all Python dependencies

### Before Each Session

**Claude Code automatically handles ComfyUI:**
- Checks if ComfyUI is running
- Starts it if needed
- Verifies the connection before generating

No manual intervention required - just start your video project conversation.

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM | 10GB | 12GB+ |
| RAM | 16GB | 32GB |
| Storage | 30GB free | 50GB+ |
| OS | Windows/Linux/macOS | Ubuntu 22.04+ |

**See `SETUP.md` for detailed manual installation instructions.**

## MANDATORY WORKFLOW REQUIREMENTS

**YOU MUST FOLLOW THESE RULES:**

1. **ALWAYS use TodoWrite** at the start to create a task list for the entire workflow
2. **NEVER skip phases** - complete each phase in order before proceeding
3. **ALWAYS create required files** - philosophy.md, style.json, and scene-breakdown.md are REQUIRED
4. **ALWAYS break videos into multiple scenes** - minimum 2 scenes for any video over 5 seconds
5. **ALWAYS ask user for approval** before proceeding to the next phase
6. **NEVER generate video without scene breakdown** - plan first, execute second

## Standard Checkpoint Format (ALL PHASES)

**Every checkpoint uses the same pattern:**

1. Show the output to user (file path or display content)
2. Ask for approval using AskUserQuestion:
   - **"Approve"** - Proceed to next step
   - User can select **"Other"** to specify what needs to be changed

3. **If user does not approve:**
   - User specifies what to change
   - Make the requested adjustments
   - Show updated result
   - Ask for approval again
   - **Repeat until approved**

4. **Do NOT proceed to next phase until current checkpoint is approved**

## Workflow Phases (MUST COMPLETE IN ORDER)

| Phase | Required Outputs | Checkpoint |
|-------|------------------|------------|
| 1. Production Philosophy | `philosophy.md`, `style.json` | Ask user to review before Phase 2 |
| 2. Scene Breakdown | `scene-breakdown.md` | Ask user to approve scene plan before Phase 3 |
| 3. Keyframe Generation | `scene-XX/keyframe-*.png` | Show user each keyframe, get approval |
| 4. Video Synthesis | `scene-XX/video.mp4` | Show user each video segment |
| 5. Review & Iterate | Refinements as needed | User signs off on final result |

---

## Phase 1: Production Philosophy (REQUIRED)

**DO NOT PROCEED TO PHASE 2 UNTIL BOTH FILES EXIST:**
- `{output_dir}/philosophy.md`
- `{output_dir}/style.json`

### Step 1.1: Create philosophy.md

Create this file with ALL sections filled in:

```markdown
# Production Philosophy: [Project Name]

## Visual Identity
- **Art Style**: [e.g., cinematic realistic, stylized animation, painterly]
- **Color Palette**: [primary colors, mood, temperature]
- **Lighting**: [natural, dramatic, soft, high-contrast]
- **Composition**: [rule of thirds, centered, dynamic angles]

## Motion Language
- **Movement Quality**: [smooth/fluid, dynamic/energetic, subtle/minimal]
- **Pacing**: [fast cuts, slow contemplative, rhythmic]
- **Camera Style**: [static, tracking, handheld, cinematic sweeps]

## Subject Consistency
- **Characters/Products**: [detailed descriptions for consistency]
- **Environment**: [setting details that persist across scenes]
- **Props/Elements**: [recurring visual elements]

## Constraints
- **Avoid**: [unwanted elements, styles, or actions]
- **Maintain**: [elements that must stay consistent]
```

### Step 1.2: Create style.json

Create this file for programmatic use with generation scripts:

```json
{
  "project_name": "Project Name Here",
  "visual_style": {
    "art_style": "description",
    "color_palette": "description",
    "lighting": "description",
    "composition": "description"
  },
  "motion_language": {
    "movement_quality": "description",
    "pacing": "description",
    "camera_style": "description"
  },
  "subject_consistency": {
    "main_subject": "detailed description",
    "environment": "detailed description"
  },
  "constraints": {
    "avoid": ["list", "of", "things"],
    "maintain": ["list", "of", "things"]
  }
}
```

### Step 1.3: CHECKPOINT - Get User Approval

1. Inform user that `philosophy.md` and `style.json` have been created
2. Use AskUserQuestion:
   - **"Approve"** - Proceed to scene breakdown
   - User selects **"Other"** to specify changes

If user requests changes → make adjustments → ask again → repeat until approved

---

## Phase 2: Scene Breakdown (REQUIRED)

**DO NOT PROCEED TO PHASE 3 UNTIL `scene-breakdown.md` EXISTS AND USER APPROVES**

### Step 2.1: Analyze Video Requirements

Before creating scenes, determine:
- Total video duration needed
- Number of scenes required (minimum 2 for videos > 5 seconds)
- Key story beats or content moments
- Transitions between scenes

### Step 2.2: Create scene-breakdown.md

**MANDATORY FORMAT - Include ALL scenes:**

```markdown
# Scene Breakdown: [Project Name]

## Overview
- **Total Duration**: [X seconds]
- **Number of Scenes**: [N]
- **Video Type**: [promotional/narrative/educational/etc.]

---

## Scene 1: [Title]

**Duration**: [X seconds] (max 5 seconds per scene)
**Purpose**: [What this scene communicates]

**Keyframes Required**:
- Start frame: [detailed description]
- End frame: [detailed description if using dual-frame mode]

**Motion Description**:
[Specific actions and movements that occur]

**Camera**: [static/tracking/pan/zoom - be specific]

**Transition to Next**: [cut/fade/continuous]

---

## Scene 2: [Title]

[Same format as Scene 1]

---

[Continue for all scenes...]

---

## Generation Strategy

| Scene | Mode | Keyframes | Notes |
|-------|------|-----------|-------|
| 1 | [single/dual] | [1-2] | [any special notes] |
| 2 | [single/dual] | [1-2] | [any special notes] |
```

### Scene Count Guidelines

**WAN generates 5-second clips (81 frames at 16fps)**

| Total Video Length | Minimum Scenes | Recommended Scenes |
|--------------------|----------------|-------------------|
| 1-5 seconds | 1 | 1 |
| 6-10 seconds | 2 | 2 |
| 11-15 seconds | 3 | 3 |
| 16-20 seconds | 4 | 4 |
| 20+ seconds | 5+ | Break into 5s beats |

### Step 2.3: CHECKPOINT - Get User Approval

1. Inform user that `scene-breakdown.md` has been created with [N] scenes
2. Use AskUserQuestion:
   - **"Approve"** - Proceed to keyframe generation
   - User selects **"Other"** to specify changes

If user requests changes → make adjustments → ask again → repeat until approved

---

## Phase 3: Keyframe Generation

**FOR EACH SCENE, generate keyframes before moving to the next scene.**

### CRITICAL: Reference Image Rules for Consistency

**YOU MUST follow these rules to maintain character/background consistency:**

1. **First keyframe of Scene 1**: No reference needed (establishes the visual style)
2. **All subsequent keyframes**: MUST use `--reference` flag with previous keyframe(s)
3. **End keyframe**: ALWAYS reference the start keyframe of the same scene
4. **Next scene's start keyframe**: ALWAYS reference the previous scene's end keyframe (or start if no end)

**Reference Chain Example:**
```
Scene 1 start → (reference for) → Scene 1 end
Scene 1 end   → (reference for) → Scene 2 start
Scene 2 start → (reference for) → Scene 2 end
... and so on
```

### Step 3.1: Set Up Scene Directory

```bash
mkdir -p {output_dir}/scene-01
mkdir -p {output_dir}/scene-02
# ... for each scene
```

### Step 3.2: Generate Keyframes Per Scene

**Scene 1 - First keyframe (no reference needed):**
```bash
# Scene 1: Start keyframe - establishes visual style
python {baseDir}/scripts/sd35_image.py \
  --prompt "[Detailed prompt from scene-breakdown.md]" \
  --style-ref {output_dir}/style.json \
  --output {output_dir}/scene-01/keyframe-start.png
```

**Scene 1 - End keyframe (MUST reference start):**
```bash
# Scene 1: End keyframe - MUST reference start for consistency
python {baseDir}/scripts/sd35_image.py \
  --prompt "[Detailed prompt - same characters in new pose/state]" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/scene-01/keyframe-start.png \
  --output {output_dir}/scene-01/keyframe-end.png
```

**Scene 2+ - Start keyframe (MUST reference previous scene):**
```bash
# Scene 2: Start keyframe - MUST reference Scene 1's end keyframe
python {baseDir}/scripts/sd35_image.py \
  --prompt "[Detailed prompt for scene 2 start]" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/scene-01/keyframe-end.png \
  --output {output_dir}/scene-02/keyframe-start.png
```

**Multiple references for complex consistency:**
```bash
# You can pass multiple --reference flags for better consistency
python {baseDir}/scripts/sd35_image.py \
  --prompt "[Detailed prompt]" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/scene-01/keyframe-start.png \
  --reference {output_dir}/scene-01/keyframe-end.png \
  --output {output_dir}/scene-02/keyframe-start.png
```

### Step 3.3: Keyframe Quality Checklist

Before proceeding to video, verify EACH keyframe:
- [ ] Subject appears correctly (no distortion)
- [ ] Style matches Production Philosophy
- [ ] Composition allows for intended motion
- [ ] Characters are consistent with reference keyframes
- [ ] Background/environment is consistent with reference keyframes
- [ ] Lighting direction is consistent

**If consistency check fails**: Regenerate the keyframe with the same reference images. Do NOT proceed with inconsistent keyframes.

### Step 3.4: MANDATORY CHECKPOINT - Human Review After EACH Keyframe

**After generating EACH keyframe, you MUST:**

1. **Show the keyframe to the user** (display the image or provide file path)
2. **Ask user for approval using AskUserQuestion with simple options:**
   - "Approve" - Keyframe looks good, proceed
   - (User can select "Other" to specify what needs to be fixed)

**Example checkpoint:**
> "Generated keyframe: `scene-02/keyframe-start.png`
>
> Please review. Approve to proceed, or describe what needs to be fixed."

**If user does not approve:**
- User will specify what needs to be fixed
- Regenerate with adjusted prompt based on user feedback
- Repeat checkpoint until user approves
- Do NOT proceed to next keyframe or video until current keyframe is approved

---

## Phase 4: Video Synthesis

**Generate video for EACH scene according to the scene breakdown.**

### Step 4.1: Generate Video Per Scene

**Single-frame mode (Image-to-Video):**
```bash
python {baseDir}/scripts/wan_video.py \
  --prompt "[Motion description from scene-breakdown.md]" \
  --start-frame {output_dir}/scene-01/keyframe-start.png \
  --style-ref {output_dir}/style.json \
  --output {output_dir}/scene-01/video.mp4
```

**Dual-frame mode (First-Last-Frame):**
```bash
python {baseDir}/scripts/wan_video.py \
  --prompt "[Motion description from scene-breakdown.md]" \
  --start-frame {output_dir}/scene-01/keyframe-start.png \
  --end-frame {output_dir}/scene-01/keyframe-end.png \
  --style-ref {output_dir}/style.json \
  --output {output_dir}/scene-01/video.mp4
```

### Step 4.2: CHECKPOINT - Show User Each Video

**After each video generation, inform the user:**
> "Generated video for Scene [N]: `scene-XX/video.mp4`
> Duration: ~5 seconds (81 frames at 16fps)
>
> Please review. Any issues to address before proceeding to the next scene?"

### Step 4.3: Repeat for All Scenes

Continue generating keyframes and videos for each scene in the breakdown.

---

## Phase 5: Review & Iterate

### Step 5.1: Summary for User

After all scenes are complete, provide a summary:

```
## Generation Complete

**Files Created:**
- philosophy.md
- style.json
- scene-breakdown.md
- scene-01/keyframe-start.png, keyframe-end.png, video.mp4
- scene-02/keyframe-start.png, keyframe-end.png, video.mp4
- [etc.]

**Total Duration**: [sum of all scene durations]
**Number of Scenes**: [N]

The videos are ready for assembly in a video editor.
```

### Step 5.2: Handle Iteration Requests

If user requests changes:
1. Identify which scene(s) need modification
2. Determine if keyframe or prompt adjustment is needed
3. Regenerate only the affected assets
4. Never adjust both keyframes AND prompts simultaneously

---

## Output Directory Structure (REQUIRED)

```
{output_dir}/
├── philosophy.md           # REQUIRED - Production philosophy
├── style.json             # REQUIRED - Style configuration
├── scene-breakdown.md     # REQUIRED - Full scene breakdown
├── scene-01/
│   ├── keyframe-start.png
│   ├── keyframe-end.png   # If using dual-frame
│   └── video.mp4
├── scene-02/
│   ├── keyframe-start.png
│   ├── keyframe-end.png
│   └── video.mp4
└── [additional scenes...]
```

---

## TodoWrite Template

At the START of the workflow, create this todo list:

```
1. Check ComfyUI setup and start server (automatic)
2. Create philosophy.md
3. Create style.json
4. Get user approval on production philosophy
5. Create scene-breakdown.md
6. Get user approval on scene breakdown
7. Generate Scene 1 keyframes
8. Get user approval on Scene 1 keyframes
9. Generate Scene 1 video
10. [Repeat 7-9 for each scene]
11. Provide final summary to user
```

### Auto-Setup Check (Step 1)

Before starting video generation, automatically check and start ComfyUI:

```bash
# Check setup status
python {baseDir}/scripts/setup_comfyui.py --check

# If setup incomplete, run full setup
python {baseDir}/scripts/setup_comfyui.py

# Verify ComfyUI is accessible, start if needed
python {baseDir}/scripts/comfyui_client.py
```

If ComfyUI is not running, start it in the background before proceeding.

---

## Quick Reference

| Script | Purpose | Key Arguments |
|--------|---------|---------------|
| `sd35_image.py` | Generate keyframes (SD 3.5 + IP-Adapter) | `--prompt`, `--output`, `--style-ref`, `--reference` |
| `wan_video.py` | Generate videos (WAN 2.2) | `--prompt`, `--start-frame`, `--end-frame`, `--output` |
| `comfyui_client.py` | Test ComfyUI connection | (run directly to test) |

### Video Generation Modes

| Mode | Inputs | Use Case |
|------|--------|----------|
| I2V (Image-to-Video) | `--start-frame` | Continuous motion from single frame |
| FLF2V (First-Last-Frame) | `--start-frame` + `--end-frame` | Precise control over motion |

### Technical Specs

| Parameter | Value |
|-----------|-------|
| Video Duration | ~5 seconds (81 frames) |
| Frame Rate | 16 fps |
| Resolution | Up to 832x480 (medium preset) |
| VRAM Required | 10GB (GGUF Q4_K_M quantization) |
| Steps | 8 (with LightX2V LoRA) |
| CFG | 1.0 (guidance baked into LoRA) |
| LoRA Strength | 1.25 (for I2V mode) |

### Models Required

**Video Generation (WAN 2.2):**
| Model | Size | Purpose |
|-------|------|---------|
| wan2.2_i2v_low_noise_14B_Q4_K_M.gguf | 8.5GB | Video generation |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | 4.9GB | WAN text encoder |
| wan_2.1_vae.safetensors | 0.2GB | WAN VAE |
| Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors | 0.7GB | Fast generation LoRA |

**Keyframe Generation (SD 3.5 Large):**
| Model | Size | Purpose |
|-------|------|---------|
| sd3.5_large-Q4_K_S.gguf | 4.8GB | SD 3.5 Large (GGUF quantized) |
| clip_g.safetensors | 1.4GB | CLIP-G text encoder |
| clip_l.safetensors | 0.2GB | CLIP-L text encoder |
| t5xxl_fp8_e4m3fn.safetensors | 4.9GB | T5-XXL text encoder |
| sd3.5_vae.safetensors | 0.2GB | SD 3.5 VAE |

**Consistency Tools (ControlNet + IP-Adapter):**
| Model | Size | Purpose |
|-------|------|---------|
| sd3.5_large_controlnet_canny.safetensors | 2.5GB | Edge-based control |
| sd3.5_large_controlnet_depth.safetensors | 2.5GB | Depth-based control |
| ip-adapter-sd3.bin | 1.0GB | Character consistency |
| siglip_vision_patch14_384.safetensors | 0.9GB | IP-Adapter vision encoder |

See `SETUP.md` for installation instructions.
See `references/prompt-engineering.md` for detailed prompt writing guidance.
See `references/troubleshooting.md` for common issues and solutions.
