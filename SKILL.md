---
name: ai-video-producer
description: >
  Complete AI video production workflow using WAN 2.2 and Qwen Image Edit 2511 models via ComfyUI.
  Creates any video type: promotional, educational, narrative, social media,
  animations, game trailers, music videos, product demos, and more. Use when
  users want to create videos with AI, need help with video storyboarding,
  keyframe generation, or video prompt writing. Follows a philosophy-first
  approach: establish visual style and production philosophy, then execute
  scene by scene with user feedback at each stage. Supports advanced features
  like layer-based compositing, pose transfer (AnyPose LoRA), and style
  consistency (InStyle LoRA). Runs locally on RTX 3080+.
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion, TodoWrite
---

# AI Video Producer

Create professional AI-generated videos through a structured, iterative workflow using local models.

## Prerequisites & Auto-Setup

**This skill requires ComfyUI with WAN 2.2 and Qwen Image Edit 2511 models. The setup script handles everything automatically.**

### First-Time Setup (Automatic)

If ComfyUI is not detected, run the auto-setup script:

```bash
# Full automatic setup (~40GB download)
python {baseDir}/scripts/setup_comfyui.py

# Check setup status
python {baseDir}/scripts/setup_comfyui.py --check

# Start ComfyUI server
python {baseDir}/scripts/setup_comfyui.py --start
```

The setup script will:
1. Clone and configure ComfyUI
2. Install required custom nodes (ComfyUI-GGUF, ComfyUI_RH_Qwen-Image, comfyui_controlnet_aux, etc.)
3. Download WAN 2.2 GGUF model (Q4_K_M for 10GB VRAM)
4. Download Qwen Image Edit 2511 models (FP8)
5. Download ControlNet Union model for pose-guided generation
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
| Storage | 40GB free | 60GB+ |
| OS | Windows/Linux/macOS | Ubuntu 22.04+ |

**See `SETUP.md` for detailed manual installation instructions.**

## MANDATORY WORKFLOW REQUIREMENTS

**YOU MUST FOLLOW THESE RULES:**

1. **ALWAYS use TodoWrite** at the start to create a task list for the entire workflow
2. **NEVER skip phases** - complete each phase in order before proceeding
3. **ALWAYS create required files** - philosophy.md, style.json, scene-breakdown.md, and assets.json are REQUIRED
4. **ALWAYS break videos into multiple scenes** - minimum 2 scenes for any video over 5 seconds
5. **ALWAYS ask user for approval** before proceeding to the next phase
6. **NEVER generate video without scene breakdown and assets** - plan first, execute second
7. **ALWAYS use layer-based generation** for character scenes (background → character → composite)

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
| 2. Scene Breakdown | `scene-breakdown.md` | Ask user to approve scene plan before Phase 2.5 |
| 2.5. Asset Generation | `assets.json`, `assets/` folder | Ask user to review assets before Phase 3 |
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

**Type**: character | landscape
**Duration**: [X seconds] (max 5 seconds per scene)
**Purpose**: [What this scene communicates]

**Characters**: [asset name from assets.json, e.g., "samurai"] (only for type: character)
**Background**: [asset name from assets.json, e.g., "temple_courtyard"]
**Style**: [asset name from assets.json, e.g., "ghibli"]

**Start Frame**:
- pose: [asset name from assets.json, e.g., "standing"]
- expression: [description]
- additional details: [any other specific details]

**End Frame**:
- pose: [asset name from assets.json, e.g., "meditation"]
- expression: [description]
- additional details: [any other specific details]

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

| Scene | Type | Mode | Keyframes | Notes |
|-------|------|------|-----------|-------|
| 1 | character | composite | 2 | Uses layers/ for background + character |
| 2 | landscape | single | 2 | Background only, no character layer |
```

**Scene Type Explanation:**
- `character`: Scenes with characters - uses 3-step composite flow (background → character → composite)
- `landscape`: Scenes without characters - uses single background generation

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
   - **"Approve"** - Proceed to asset generation
   - User selects **"Other"** to specify changes

If user requests changes → make adjustments → ask again → repeat until approved

---

## Phase 2.5: Asset Generation (REQUIRED)

**DO NOT PROCEED TO PHASE 3 UNTIL `assets.json` EXISTS AND USER APPROVES**

This phase creates reusable assets that maintain consistency across all scenes.

### Step 2.5.1: Analyze Required Assets

Review `scene-breakdown.md` and identify all unique:
- Characters (each character that appears in scenes)
- Backgrounds (each unique location/environment)
- Poses (each unique character pose needed)
- Styles (the visual style to apply consistently)
- Objects (any recurring props or items)

### Step 2.5.2: Create assets.json

**MANDATORY FORMAT:**

```json
{
  "characters": {
    "samurai": {
      "description": "Feudal Japanese warrior, red armor, stern expression, dark hair",
      "identity_ref": "assets/characters/samurai.png"
    }
  },
  "backgrounds": {
    "temple_courtyard": {
      "description": "Ancient temple with cherry blossoms, stone paths, morning light",
      "ref_image": "assets/backgrounds/temple_courtyard.png"
    }
  },
  "poses": {
    "standing": {
      "description": "Upright neutral stance, arms at sides",
      "ref_image": "assets/poses/standing.png"
    },
    "meditation": {
      "description": "Seated cross-legged, hands on knees, eyes closed",
      "ref_image": "assets/poses/meditation.png"
    }
  },
  "styles": {
    "ghibli": {
      "description": "Studio Ghibli anime aesthetic, soft colors, painterly",
      "ref_image": "assets/styles/ghibli.png"
    }
  },
  "objects": {
    "katana": {
      "description": "Traditional Japanese sword with black sheath",
      "ref_image": "assets/objects/katana.png"
    }
  }
}
```

### Step 2.5.3: Generate Asset Images

Create the `assets/` directory structure and generate each asset:

```bash
mkdir -p {output_dir}/assets/characters
mkdir -p {output_dir}/assets/backgrounds
mkdir -p {output_dir}/assets/poses
mkdir -p {output_dir}/assets/styles
mkdir -p {output_dir}/assets/objects
```

**Generate each asset using T2I mode:**
```bash
# Character identity (use detailed description)
python {baseDir}/scripts/qwen_image.py \
  --prompt "Portrait of [character description], neutral pose, clean background" \
  --output {output_dir}/assets/characters/[name].png

# Background (use detailed environment description)
python {baseDir}/scripts/qwen_image.py \
  --prompt "[Background description], no people, establishing shot" \
  --output {output_dir}/assets/backgrounds/[name].png

# Pose reference (simple figure showing pose)
python {baseDir}/scripts/qwen_image.py \
  --prompt "Simple figure demonstrating [pose description], minimal background" \
  --output {output_dir}/assets/poses/[name].png

# Style reference (example image in target style)
python {baseDir}/scripts/qwen_image.py \
  --prompt "Example scene in [style description] style, demonstration of artistic style" \
  --output {output_dir}/assets/styles/[name].png
```

### Step 2.5.4: CHECKPOINT - Get User Approval

1. Inform user that `assets.json` and asset images have been created
2. Show the generated assets to user
3. Use AskUserQuestion:
   - **"Approve"** - Proceed to keyframe generation
   - User selects **"Other"** to specify which assets need adjustment

If user requests changes → regenerate specific assets → ask again → repeat until approved

---

## Phase 3: Keyframe Generation

**FOR EACH SCENE, generate keyframes before moving to the next scene.**

### Generation Flow by Scene Type

Keyframe generation uses different flows based on scene type from `scene-breakdown.md`:

| Scene Type | Generation Flow |
|------------|-----------------|
| `character` | 3-step composite: background → character → composite |
| `landscape` | Single step: background only |

### Reference Chain Rules

**These rules ensure consistency across scenes:**

| Asset Type | Chain Behavior |
|------------|----------------|
| **Character Identity** | ALWAYS use original asset from `assets/characters/` (never chain) |
| **Character Pose** | Reference from `assets/poses/` per keyframe |
| **Background** | Chain from previous scene's background for continuity |
| **Style** | ALWAYS apply with style asset reference |

### Step 3.1: Set Up Scene Directories

```bash
mkdir -p {output_dir}/scene-01/layers
mkdir -p {output_dir}/scene-02/layers
# ... for each scene
```

### Step 3.2: Character Scene Generation (type: character)

**Character scenes use a 3-step composite flow:**

```
Step 1: Generate Background Layer
         ↓
Step 2: Generate Character Layer (with pose)
         ↓
Step 3: Composite Layers Together
         ↓
Output: keyframe-start.png
```

**Step 1 - Generate Background Layer:**
```bash
# Use background asset OR chain from previous scene
python {baseDir}/scripts/qwen_image.py \
  --prompt "[Background description], [style] style, no people, establishing shot" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/assets/backgrounds/[background_name].png \
  --output {output_dir}/scene-01/layers/background.png
```

**Step 2 - Generate Character Layer (with pose transfer):**
```bash
# Character identity + pose reference
python {baseDir}/scripts/qwen_image.py \
  --prompt "[Character] in [pose description], [expression], transparent background" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/assets/characters/[character_name].png \
  --pose {output_dir}/assets/poses/[pose_name].png \
  --control-strength 0.8 \
  --output {output_dir}/scene-01/layers/character.png
```

**Step 3 - Composite Layers:**
```bash
# Combine background + character into final keyframe
python {baseDir}/scripts/qwen_image.py \
  --prompt "Place [character] naturally in [background] scene, [style] style" \
  --reference {output_dir}/scene-01/layers/background.png \
  --reference {output_dir}/scene-01/layers/character.png \
  --output {output_dir}/scene-01/keyframe-start.png
```

**End Keyframe (different pose):**
Repeat Steps 2-3 with the end frame pose from `scene-breakdown.md`.

### Step 3.3: Landscape Scene Generation (type: landscape)

**Landscape scenes generate background only:**

```bash
# Scene 2: Landscape - background only
python {baseDir}/scripts/qwen_image.py \
  --prompt "[Background description with scene details], [style] style" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/assets/backgrounds/[background_name].png \
  --output {output_dir}/scene-02/keyframe-start.png

# Also save to layers for reference chain
cp {output_dir}/scene-02/keyframe-start.png {output_dir}/scene-02/layers/background.png
```

### Step 3.4: Scene Continuity

**For consecutive scenes sharing backgrounds:**
```bash
# Scene 3 uses Scene 2's background as reference (chaining)
python {baseDir}/scripts/qwen_image.py \
  --prompt "[Modified background description]" \
  --reference {output_dir}/scene-02/layers/background.png \
  --output {output_dir}/scene-03/layers/background.png
```

**For character identity (NEVER chain - always use original):**
```bash
# ALWAYS reference original character asset, not previous keyframe
--reference {output_dir}/assets/characters/[character_name].png
```

### Step 3.5: Keyframe Quality Checklist

Before proceeding to video, verify EACH keyframe:
- [ ] Subject appears correctly (no distortion)
- [ ] Style matches Production Philosophy
- [ ] Composition allows for intended motion
- [ ] Characters are consistent with reference keyframes
- [ ] Background/environment is consistent with reference keyframes
- [ ] Lighting direction is consistent

**If consistency check fails**: Regenerate the keyframe with the same reference images. Do NOT proceed with inconsistent keyframes.

### Step 3.6: MANDATORY CHECKPOINT - Human Review After EACH Keyframe

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
├── philosophy.md              # REQUIRED - Production philosophy
├── style.json                 # REQUIRED - Style configuration
├── scene-breakdown.md         # REQUIRED - Full scene breakdown
├── assets.json                # REQUIRED - Asset definitions
│
├── assets/                    # Reusable assets
│   ├── characters/
│   │   ├── samurai.png
│   │   └── ninja.png
│   ├── backgrounds/
│   │   ├── temple_courtyard.png
│   │   └── mountain_sunset.png
│   ├── poses/
│   │   ├── standing.png
│   │   ├── meditation.png
│   │   └── fighting.png
│   ├── styles/
│   │   └── ghibli.png
│   └── objects/
│       └── katana.png
│
├── scene-01/
│   ├── layers/                # Intermediate layers (character scenes)
│   │   ├── background.png
│   │   └── character.png
│   ├── keyframe-start.png     # Final composite
│   ├── keyframe-end.png
│   └── video.mp4
│
├── scene-02/
│   ├── layers/
│   │   └── background.png     # Landscape - no character layer
│   ├── keyframe-start.png
│   ├── keyframe-end.png
│   └── video.mp4
│
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
7. Analyze required assets from scene breakdown
8. Create assets.json
9. Generate asset images (characters, backgrounds, poses, styles)
10. Get user approval on assets
11. Generate Scene 1 keyframes (layers → composite)
12. Get user approval on Scene 1 keyframes
13. Generate Scene 1 video
14. [Repeat 11-13 for each scene]
15. Provide final summary to user
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
| `qwen_image.py` | Generate keyframes (Qwen Image Edit) | `--prompt`, `--output`, `--style-ref`, `--reference`, `--pose`, `--control-strength` |
| `wan_video.py` | Generate videos (WAN 2.2) | `--prompt`, `--start-frame`, `--end-frame`, `--output` |
| `comfyui_client.py` | Test ComfyUI connection | (run directly to test) |

### Keyframe Generation Modes

| Mode | Command | Description |
|------|---------|-------------|
| **T2I** | `qwen_image.py ...` (no ref) | Create initial image from scratch. |
| **Edit** | `qwen_image.py ... --reference ...` | Edit existing image while maintaining consistency. |
| **Pose** | `qwen_image.py ... --reference ... --pose ...` | Generate with pose transfer (ControlNet). |
| **Composite** | `qwen_image.py ... --reference [bg] --reference [char] ...` | Combine multiple images. |

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
| VRAM Required | 10GB (WAN Q4_K_M + Qwen FP8) |
| Steps | 20 (Qwen), 8 (WAN) |

### Models Required

**Video Generation (WAN 2.2):**
| Model | Size | Purpose |
|-------|------|---------|
| wan2.2_i2v_low_noise_14B_Q4_K_M.gguf | 8.5GB | Video generation |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | 4.9GB | WAN text encoder |
| wan_2.1_vae.safetensors | 0.2GB | WAN VAE |
| Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors | 0.7GB | Fast generation LoRA |

**Keyframe Generation (Qwen Image Edit 2511):**
| Model | Size | Purpose |
|-------|------|---------|
| qwen_image_edit_2511_fp8mixed.safetensors | 12.0GB | Main Image Model (FP8) |
| qwen_2.5_vl_7b_fp8_scaled.safetensors | 7.5GB | Vision-Language Text Encoder |
| qwen_image_vae.safetensors | 0.2GB | Qwen VAE |

**ControlNet (for pose-guided generation):**
| Model | Size | Purpose |
|-------|------|---------|
| Qwen-Image-InstantX-ControlNet-Union.safetensors | 3.54GB | Pose/depth/canny control |

See `SETUP.md` for installation instructions.
See `references/prompt-engineering.md` for detailed prompt writing guidance.
See `references/troubleshooting.md` for common issues and solutions.
See `docs/ADVANCED_KEYFRAME_PLAN.md` for advanced layer-based generation details.
