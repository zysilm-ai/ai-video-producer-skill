---
name: ai-video-producer
description: >
  Complete AI video production workflow using WAN 2.1 and Qwen Image Edit 2511 models via ComfyUI.
  Creates any video type: promotional, educational, narrative, social media,
  animations, game trailers, music videos, product demos, and more. Use when
  users want to create videos with AI, need help with video storyboarding,
  keyframe generation, or video prompt writing. Follows a philosophy-first
  approach: establish visual style and production philosophy, then execute
  scene by scene with user feedback at each stage. Supports advanced features
  like layer-based compositing, pose transfer (ControlNet), and style
  consistency. Runs locally on RTX 3080+ (10GB+ VRAM).
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion, TodoWrite
---

# AI Video Producer

Create professional AI-generated videos through a structured, iterative workflow using local models.

## Prerequisites & Auto-Setup

**This skill requires WAN 2.1 and Qwen Image Edit 2511 models via ComfyUI with GGUF quantization. The setup script handles everything automatically.**

### First-Time Setup (Automatic)

Run the setup script to install ComfyUI and download models:

```bash
# Full setup (installs ComfyUI + downloads models ~40GB)
python {baseDir}/scripts/setup_comfyui.py

# Or check current setup status
python {baseDir}/scripts/setup_comfyui.py --check

# Download models only (if ComfyUI already installed)
python {baseDir}/scripts/setup_comfyui.py --models
```

The setup script will:
1. Clone ComfyUI into `{baseDir}/comfyui/`
2. Install custom nodes (GGUF, VideoHelperSuite, Manager)
3. Download WAN 2.1 I2V GGUF model (~11GB)
4. Download Qwen Image Edit 2511 GGUF model (~13GB)
5. Download text encoders, VAEs, and distillation LoRAs (~14GB)

### Before Each Session

**Start the ComfyUI server** before generating:

```bash
# Start ComfyUI server (keep running in background)
# This automatically uses --cache-none for optimal VRAM management
python {baseDir}/scripts/setup_comfyui.py --start

# Or manually (IMPORTANT: include --cache-none for 10GB VRAM systems):
cd {baseDir}/comfyui && python main.py --listen 0.0.0.0 --port 8188 --cache-none
```

The server must be running at `http://127.0.0.1:8188` for generation scripts to work.

**IMPORTANT:** The `--cache-none` flag is critical for multi-reference keyframe generation on 10GB VRAM systems. It allows ComfyUI to unload the text encoder (~8GB) after encoding, freeing VRAM for the diffusion model. Without it, multi-reference workflows may take 30+ minutes instead of ~5 minutes.

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM | 10GB | 12GB+ |
| RAM | 16GB | 32GB |
| Storage | 40GB free | 60GB+ |
| OS | Windows/Linux/macOS | Ubuntu 22.04+ |

**See `README.md` for detailed setup instructions.**

## MANDATORY WORKFLOW REQUIREMENTS

**YOU MUST FOLLOW THESE RULES:**

1. **ALWAYS use TodoWrite** at the start to create a task list for the entire workflow
2. **NEVER skip phases** - complete each phase in order before proceeding
3. **ALWAYS create required files** - philosophy.md, style.json, scene-breakdown.md, and pipeline.json are REQUIRED
4. **ALWAYS break videos into multiple scenes** - minimum 2 scenes for any video over 5 seconds
5. **ALWAYS ask user for approval** before proceeding to the next phase
6. **NEVER generate without a complete pipeline.json** - plan ALL prompts first, execute second
7. **ALWAYS use execute_pipeline.py** for generation - deterministic execution, no ad-hoc commands
8. **ALWAYS review generated outputs using VLM** - view images after each stage, assess quality

## Pipeline-Based Architecture

**This skill uses a two-phase approach:**

### Phase A: Planning (LLM-Driven)
- LLM creates philosophy.md, style.json, scene-breakdown.md
- LLM generates ALL prompts and stores in `pipeline.json`
- User reviews and approves the complete plan before any generation

### Phase B: Execution (Programmatic)
- `execute_pipeline.py` reads pipeline.json and executes deterministically
- LLM reviews outputs using VLM capability after each stage
- User approves or requests regeneration

**Benefits:**
- All prompts visible before ANY generation starts
- Deterministic execution - no LLM deviation during generation
- Reproducible - same pipeline.json = same commands executed
- Traceable - status tracking in pipeline.json

## Standard Checkpoint Format (ALL PHASES)

**Every checkpoint uses the same pattern:**

1. Show the output to user (file path or display content)
2. Ask for approval using AskUserQuestion:
   - **"Approve"** - Proceed to next step
   - User can select **"Other"** to specify what needs to be changed

3. **If user does not approve:**
   - User specifies what to change
   - Make the requested adjustments (update pipeline.json)
   - Show updated result
   - Ask for approval again
   - **Repeat until approved**

4. **Do NOT proceed to next phase until current checkpoint is approved**

## Workflow Phases (MUST COMPLETE IN ORDER)

| Phase | LLM Actions | Required Outputs | Checkpoint |
|-------|-------------|------------------|------------|
| 1. Production Philosophy | Create visual identity & style | `philosophy.md`, `style.json` | User approval |
| 2. Scene Breakdown | Plan scenes & keyframes | `scene-breakdown.md` | User approval |
| 3. Pipeline Generation | Generate ALL prompts | `pipeline.json` | User approval |
| 4. Asset Execution | Run `execute_pipeline.py --stage assets` | `assets/` folder | LLM reviews with VLM, user approval |
| 5. Keyframe Execution | Run `execute_pipeline.py --stage keyframes` | `keyframes/*.png` | LLM reviews with VLM, user approval |
| 6. Video Execution | Run `execute_pipeline.py --stage videos` | `scene-*/video.mp4` | User approval |
| 7. Review & Iterate | Handle regeneration requests | Refinements | User signs off |

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
- **Number of Unique Keyframes**: [M] (adjacent scenes share boundary keyframes)
- **Video Type**: [promotional/narrative/educational/etc.]

---

## Unique Keyframes

Define all unique keyframes first. **Adjacent scenes share their boundary keyframe for perfect continuity.**

| ID | Description | Pose Asset | Character | Background | Used In |
|----|-------------|------------|-----------|------------|---------|
| KF-A | [Description of this moment] | [pose].png | [character] | [background] | Scene 1 start |
| KF-B | [Description of this moment] | [pose].png | [character] | [background] | Scene 1 end, Scene 2 start |
| KF-C | [Description of this moment] | [pose].png | [character] | [background] | Scene 2 end |

**Important:** Keyframes marked with multiple scenes (e.g., "Scene 1 end, Scene 2 start") are SHARED.
Generate once in \ folder, use for both scenes. This ensures perfect video continuity.

---

## Scenes

### Scene 1: [Title]

**Type**: character | landscape
**Duration**: [X seconds] (max 5 seconds per scene)
**Purpose**: [What this scene communicates]

**Start Keyframe**: KF-A
**End Keyframe**: KF-B

**Motion Description**:
[Specific actions and movements that occur between start and end keyframes]

**Camera**: [static/tracking/pan/zoom - be specific]

**Transition to Next**: [cut/fade/continuous]

---

### Scene 2: [Title]

**Type**: character | landscape
**Duration**: [X seconds]
**Purpose**: [What this scene communicates]

**Start Keyframe**: KF-B (shared from Scene 1 end - do NOT regenerate)
**End Keyframe**: KF-C

**Motion Description**:
[Specific actions and movements that occur between start and end keyframes]

**Camera**: [static/tracking/pan/zoom - be specific]

**Transition to Next**: [cut/fade/continuous]

---

[Continue for all scenes - remember adjacent scenes share boundary keyframes]

---

## Generation Strategy

| Scene | Start KF | End KF | Type | Notes |
|-------|----------|--------|------|-------|
| 1 | KF-A | KF-B | character | Generate KF-A and KF-B |
| 2 | KF-B | KF-C | character | Reuse KF-B (shared), generate KF-C only |
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

**Generate each asset using `asset_generator.py`:**

```bash
# Character identity (neutral A-pose, clean white background)
python {baseDir}/scripts/asset_generator.py character \
  --name [character_name] \
  --description "[detailed character description]" \
  --output {output_dir}/assets/characters/[name].png

# Background (no people, establishing shot)
python {baseDir}/scripts/asset_generator.py background \
  --name [background_name] \
  --description "[detailed environment description]" \
  --output {output_dir}/assets/backgrounds/[name].png

# Pose reference + skeleton (RECOMMENDED - generates clean image for reliable extraction)
# Step 1: Generate a clean pose reference image optimized for skeleton detection
# Step 2: Extract skeleton from the clean reference
python {baseDir}/scripts/asset_generator.py pose-ref \
  --name [pose_name] \
  --pose "[pose description - just the body position, e.g., 'fighting stance fists raised']" \
  --output {output_dir}/assets/poses/refs/[pose_name].png \
  --extract-skeleton \
  --skeleton-output {output_dir}/assets/poses/[pose_name]_skeleton.png

# Alternative: Extract skeleton from existing image (may fail on complex images)
# python {baseDir}/scripts/asset_generator.py pose \
#   --source [path/to/reference_image.jpg] \
#   --output {output_dir}/assets/poses/[pose_name]_skeleton.png

# Style reference (example image in target style)
python {baseDir}/scripts/asset_generator.py style \
  --name [style_name] \
  --description "[style description]" \
  --output {output_dir}/assets/styles/[name].png
```

**IMPORTANT - Pose Assets:**
- Pose assets are **skeletons only** (stick figures on black background)
- They are extracted from reference images using DWPose
- They do NOT contain any character appearance - only body position
- This allows applying any pose to any character without identity leakage

**POSE REFERENCE IMAGE REQUIREMENTS (for reliable skeleton extraction):**
When generating pose reference images, follow these rules to ensure DWPose can detect the skeleton:
1. **SINGLE CHARACTER ONLY** - never multiple people in frame
2. **PLAIN BACKGROUND** - solid gray/white, no scenery or architecture
3. **FULL BODY VISIBLE** - all limbs shown, not cropped
4. **CENTERED COMPOSITION** - character in middle of frame
5. **NO VISUAL EFFECTS** - no explosions, auras, particles, energy, fire
6. **CLEAR SILHOUETTE** - body outline easy to distinguish
7. **SIMPLE CLOTHING** - avoid flowing capes/robes that obscure body shape

**BAD pose description:** "Epic fighting stance with energy explosion in temple arena"
**GOOD pose description:** "fighting stance, fists raised, legs apart"

### Step 2.5.4: CHECKPOINT - Get User Approval

1. Inform user that `assets.json` and asset images have been created
2. Show the generated assets to user
3. Use AskUserQuestion:
   - **"Approve"** - Proceed to keyframe generation
   - User selects **"Other"** to specify which assets need adjustment

If user requests changes → regenerate specific assets → ask again → repeat until approved

---

## Phase 3: Pipeline Generation (REQUIRED)

**DO NOT PROCEED TO EXECUTION UNTIL `pipeline.json` EXISTS AND USER APPROVES**

This phase consolidates all prompts into a single structured file that will be executed deterministically.

### Step 3.1: Create pipeline.json

Based on philosophy.md, style.json, scene-breakdown.md, and assets.json, create a complete pipeline.json:

```json
{
  "version": "1.0",
  "project_name": "project-name",

  "metadata": {
    "created_at": "ISO timestamp",
    "philosophy_file": "philosophy.md",
    "style_file": "style.json",
    "scene_breakdown_file": "scene-breakdown.md"
  },

  "assets": {
    "characters": {
      "<character_id>": {
        "prompt": "Detailed character description for generation...",
        "output": "assets/characters/<character_id>.png",
        "status": "pending"
      }
    },
    "backgrounds": {
      "<background_id>": {
        "prompt": "Detailed background description...",
        "output": "assets/backgrounds/<background_id>.png",
        "status": "pending"
      }
    },
    "poses": {
      "<pose_id>": {
        "type": "generate",
        "prompt": "Pose description for skeleton generation",
        "output": "assets/poses/<pose_id>_skeleton.png",
        "status": "pending"
      }
    }
  },

  "keyframes": [
    {
      "id": "KF-A",
      "prompt": "Scene description with character positions and actions...",
      "background": "<background_id>",
      "characters": ["<character_id_1>", "<character_id_2>"],
      "pose": "<pose_id>",
      "settings": {
        "control_strength": 0.8,
        "preset": "medium"
      },
      "output": "keyframes/KF-A.png",
      "status": "pending"
    }
  ],

  "videos": [
    {
      "id": "scene-01",
      "prompt": "Motion description - what happens between keyframes...",
      "start_keyframe": "KF-A",
      "end_keyframe": "KF-B",
      "output": "scene-01/video.mp4",
      "status": "pending"
    }
  ]
}
```

### Step 3.2: Pipeline Prompt Writing Guidelines

**For Character Prompts:**
- Include full physical description (hair, eyes, clothing, distinguishing features)
- Mention "anime style character sheet, A-pose, full body, white background"
- Include multiple views: "front view, side view, back view"

**For Background Prompts:**
- Describe setting, lighting, atmosphere
- Include "no people, establishing shot"
- Match style from philosophy.md

**For Pose Prompts:**
- Describe body positions only, NO character appearance
- Use simple language: "two people, left person [action], right person [action]"
- Follow pose reference image requirements from Phase 2.5

**For Keyframe Prompts:**
- Use positional language: "On the left:", "On the right:", "In the center:"
- Reference character appearance from assets
- Include background context and lighting
- Match style from philosophy.md

**For Video Prompts:**
- Describe the MOTION, not static appearance
- What action happens between start and end keyframes
- Include camera movement if any

### Step 3.3: CHECKPOINT - Get User Approval

1. Show the complete pipeline.json to user
2. Highlight all prompts for review
3. Use AskUserQuestion:
   - **"Approve"** - Proceed to execution
   - User selects **"Other"** to specify which prompts need adjustment

If user requests changes → update pipeline.json → ask again → repeat until approved

---

## Phase 4: Asset Execution

**Execute asset generation using the pipeline executor.**

### Step 4.1: Run Asset Stage

```bash
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --stage assets
```

This will:
- Generate all characters, backgrounds, poses defined in pipeline.json
- Automatically use `--free-memory` for each generation
- Update status in pipeline.json as items complete

### Step 4.2: Review Assets with VLM

After execution completes, use the Read tool to view each generated asset:

```
1. View each character asset - verify appearance matches description
2. View each background asset - verify setting and style
3. View each pose skeleton - verify body positions are correct
```

### Step 4.3: CHECKPOINT - Get User Approval

1. Show generated assets to user (use Read tool to display images)
2. Report on quality and any issues noticed
3. Use AskUserQuestion:
   - **"Approve"** - Proceed to keyframes
   - User selects **"Other"** to specify which assets need regeneration

If regeneration needed:
1. Update the prompt in pipeline.json
2. Run: `python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --regenerate <asset_id>`
3. Review again → repeat until approved

---

## Phase 5: Keyframe Execution

**Execute keyframe generation using the pipeline executor.**

### Step 5.1: Run Keyframe Stage

```bash
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --stage keyframes
```

This will:
- Generate all keyframes defined in pipeline.json
- Reference assets by ID (resolved to file paths automatically)
- Use `--free-memory` for EVERY keyframe (mandatory)
- Update status in pipeline.json as items complete

### Step 5.2: Review Keyframes with VLM

After execution completes, use the Read tool to view each keyframe:

```
1. View each keyframe image
2. Check character consistency with assets
3. Check pose matches skeleton
4. Check background consistency
5. Check style matches philosophy
```

### Step 5.3: CHECKPOINT - Get User Approval

1. Show generated keyframes to user (use Read tool to display images)
2. Report on quality and consistency
3. Use AskUserQuestion:
   - **"Approve"** - Proceed to videos
   - User selects **"Other"** to specify which keyframes need regeneration

If regeneration needed:
1. Update the prompt in pipeline.json
2. Run: `python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --regenerate <KF-id>`
3. Review again → repeat until approved

---

## Phase 6: Video Execution

**Execute video generation using the pipeline executor.**

### Step 6.1: Run Video Stage

```bash
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --stage videos
```

This will:
- Generate all videos defined in pipeline.json
- Reference keyframes by ID (resolved to file paths automatically)
- Use `--free-memory` only on first video (switching from image to video models)
- Update status in pipeline.json as items complete

### Step 6.2: CHECKPOINT - Get User Approval

1. Inform user of generated video locations
2. Use AskUserQuestion:
   - **"Approve"** - Complete
   - User selects **"Other"** to specify which videos need regeneration

If regeneration needed:
1. Update the prompt in pipeline.json
2. Run: `python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --regenerate <scene-id>`
3. Review again → repeat until approved

---

## Phase 7: Review & Iterate

Handle any final adjustments requested by user.

---

## Reference: Keyframe Generation Details

**The following sections provide reference information used by the pipeline executor.**

### Keyframe Generation Principle

Instead of generating keyframes per-scene (which causes discontinuity), generate all unique keyframes first:

```
UNIQUE KEYFRAMES:              SCENES USE THEM:
┌─────────────────┐        
│ KF-A            │──────────→ Scene 1: KF-A → KF-B
├─────────────────┤                       ↓
│ KF-B (shared)   │──────────→ Scene 2: KF-B → KF-C
├─────────────────┤                       
│ KF-C            │
└─────────────────┘

Result: 3 keyframes for 2 scenes (not 4)
        Perfect continuity at scene boundaries
```

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

### Step 3.1: Set Up Directory Structure

```bash
# Create centralized keyframes folder
mkdir -p {output_dir}/keyframes

# Create scene folders (for videos only)
mkdir -p {output_dir}/scene-01
mkdir -p {output_dir}/scene-02
# ... for each scene
```

### Step 3.2: Generate Keyframes with `keyframe_generator.py`

**Use `keyframe_generator.py` which properly separates:**
- **Identity** (WHO) - from `--character` asset
- **Pose** (WHAT position) - from `--pose` skeleton
- **Action** (WHAT happening) - from `--prompt`

**Single character keyframe:**
```bash
python {baseDir}/scripts/keyframe_generator.py \
  --free-memory \
  --prompt "[Action description], [expression], [environment context]" \
  --character {output_dir}/assets/characters/[character_name].png \
  --pose {output_dir}/assets/poses/[pose_name]_skeleton.png \
  --output {output_dir}/keyframes/KF-A.png
```

**Multi-character keyframe (no background):**
```bash
# Up to 3 characters can be specified
# Characters use image1, image2, image3 reference slots
python {baseDir}/scripts/keyframe_generator.py \
  --free-memory \
  --prompt "On the left: [Character A action]. On the right: [Character B action]. [Scene context]" \
  --character {output_dir}/assets/characters/[character_a].png \
  --character {output_dir}/assets/characters/[character_b].png \
  --pose {output_dir}/assets/poses/[pose_name]_skeleton.png \
  --output {output_dir}/keyframes/KF-B.png
```

**Multi-character with background (RECOMMENDED for consistent scenes):**
```bash
# Background uses image1 slot, characters use image2/image3 slots
# This ensures both character identity AND background consistency
python {baseDir}/scripts/keyframe_generator.py \
  --free-memory \
  --prompt "On the left: [Character A action]. On the right: [Character B action]. [Scene context]" \
  --background {output_dir}/assets/backgrounds/[background_name].png \
  --character {output_dir}/assets/characters/[character_a].png \
  --character {output_dir}/assets/characters/[character_b].png \
  --pose {output_dir}/assets/poses/[pose_name]_skeleton.png \
  --output {output_dir}/keyframes/KF-B.png
```

**Reference Slot Allocation:**
| Slot | Without --background | With --background |
|------|---------------------|-------------------|
| image1 | Character 1 | Background |
| image2 | Character 2 | Character 1 |
| image3 | Character 3 | Character 2 |

**Note:** With `--background`, maximum 2 characters are supported (3 reference slots total).

**Extract pose on-the-fly from reference image:**
```bash
# If you have a reference photo/artwork showing the desired pose
python {baseDir}/scripts/keyframe_generator.py \
  --free-memory \
  --prompt "[Action description]" \
  --character {output_dir}/assets/characters/[character_name].png \
  --pose-image [path/to/reference_photo.jpg] \
  --output {output_dir}/keyframes/KF-C.png
```

### Step 3.3: Landscape Scene Generation (type: landscape)

**Landscape scenes use `asset_generator.py` for background only:**

```bash
python {baseDir}/scripts/asset_generator.py background \
  --name scene02_bg \
  --description "[Background description with scene details], [style] style" \
  --output {output_dir}/keyframes/KF-landscape.png
```

### Step 3.4: Key Principles

**NEVER chain keyframes as references:**
```bash
# WRONG - causes similar keyframes
--reference {output_dir}/keyframes/KF-A.png  # DON'T DO THIS

# CORRECT - always use original character asset
--character {output_dir}/assets/characters/[character_name].png
```

**Pose skeletons control body position without identity leakage:**
- The skeleton is just a stick figure - no character appearance
- Different skeletons = dramatically different poses
- Same character asset + different skeleton = same character in different pose

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

**IMPORTANT:** Use `--free-memory` on the FIRST video generation after keyframe generation to clear Qwen models from VRAM.

**Single-frame mode (Image-to-Video):**
```bash
# First video after images - use --free-memory
python {baseDir}/scripts/wan_video_comfyui.py \
  --free-memory \
  --prompt "[Motion description from scene-breakdown.md]" \
  --start-frame {output_dir}/scene-01/keyframe-start.png \
  --output {output_dir}/scene-01/video.mp4

# Subsequent videos - no --free-memory needed (WAN stays warm)
python {baseDir}/scripts/wan_video_comfyui.py \
  --prompt "[Motion description]" \
  --start-frame {output_dir}/scene-02/keyframe-start.png \
  --output {output_dir}/scene-02/video.mp4
```

**Dual-frame mode (First-Last-Frame):**
```bash
python {baseDir}/scripts/wan_video_comfyui.py \
  --free-memory \
  --prompt "[Motion description from scene-breakdown.md]" \
  --start-frame {output_dir}/scene-01/keyframe-start.png \
  --end-frame {output_dir}/scene-01/keyframe-end.png \
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
├── scene-breakdown.md         # REQUIRED - Full scene breakdown with unique keyframes
├── assets.json                # REQUIRED - Asset definitions
│
├── assets/                    # Reusable generation assets
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
├── keyframes/                 # CENTRALIZED unique keyframes
│   ├── KF-A.png              # Scene 1 start
│   ├── KF-B.png              # Scene 1 end = Scene 2 start (SHARED)
│   └── KF-C.png              # Scene 2 end
│
├── scene-01/
│   └── video.mp4             # Video only - keyframes in /keyframes/
│
├── scene-02/
│   └── video.mp4
│
└── [additional scenes...]
```

**Note:** Keyframes are stored centrally in `keyframes/` folder, not per-scene.
Adjacent scenes share boundary keyframes (e.g., KF-B is used by both Scene 1 and Scene 2).

---

## TodoWrite Template

At the START of the workflow, create this todo list:

```
1. Check ComfyUI setup and start server
2. Create philosophy.md
3. Create style.json
4. Get user approval on production philosophy
5. Create scene-breakdown.md with unique keyframes table
6. Get user approval on scene breakdown
7. Create pipeline.json with ALL prompts (assets, keyframes, videos)
8. Get user approval on pipeline.json
9. Execute asset stage: python execute_pipeline.py pipeline.json --stage assets
10. Review assets with VLM, get user approval
11. Execute keyframe stage: python execute_pipeline.py pipeline.json --stage keyframes
12. Review keyframes with VLM, get user approval
13. Execute video stage: python execute_pipeline.py pipeline.json --stage videos
14. Get user approval on videos
15. Provide final summary to user
```

**Key points:**
- ALL prompts are written to pipeline.json BEFORE any generation starts
- User approves the complete plan before execution
- execute_pipeline.py handles VRAM management automatically
- LLM reviews outputs with VLM after each stage

### Auto-Setup Check (Step 1)

Before starting video generation, verify ComfyUI is running:

```bash
# Check setup status
python {baseDir}/scripts/setup_comfyui.py --check

# If models missing, download them
python {baseDir}/scripts/setup_comfyui.py --models

# Start ComfyUI server (keep running in background)
python {baseDir}/scripts/setup_comfyui.py --start
```

If models are missing, the setup script will download them automatically.

### VRAM Management (IMPORTANT for 10GB GPUs)

**The Qwen image model and WAN video model cannot both fit in 10GB VRAM simultaneously.**

**RULES:**

1. **ALWAYS use `--free-memory` for EVERY keyframe generation** - Memory fragmentation between generations can cause ControlNet to consume all VRAM, leaving no room for the diffusion model (resulting in 20+ minute generation times instead of ~5 minutes)

2. **ALWAYS use `--free-memory` when switching between image and video generation**

| Operation | Command |
|-----------|---------|
| Generate keyframe | `keyframe_generator.py --free-memory ...` (ALWAYS) |
| Generate video (first) | `wan_video_comfyui.py --free-memory ...` |
| Generate video (subsequent) | `wan_video_comfyui.py ...` (no flag needed) |
| Switch back to images | `keyframe_generator.py --free-memory ...` |

**Example workflow:**
```bash
# Generate assets (Qwen stays warm between asset generations)
python asset_generator.py character --name hero --description "..." --output assets/hero.png
python asset_generator.py pose --source ref.jpg --output assets/poses/action.png

# Generate keyframes - ALWAYS use --free-memory to prevent VRAM fragmentation
python keyframe_generator.py --free-memory --character assets/hero.png --pose assets/poses/action.png --prompt "..." --output keyframes/KF-A.png
python keyframe_generator.py --free-memory --character assets/hero.png --pose assets/poses/rest.png --prompt "..." --output keyframes/KF-B.png
python keyframe_generator.py --free-memory --character assets/hero.png --pose assets/poses/fall.png --prompt "..." --output keyframes/KF-C.png

# Switch to video - FREE MEMORY FIRST
python wan_video_comfyui.py --free-memory --prompt "..." --start-frame keyframes/KF-A.png --end-frame keyframes/KF-B.png --output video1.mp4

# Generate more videos (WAN stays warm)
python wan_video_comfyui.py --prompt "..." --start-frame keyframes/KF-B.png --end-frame keyframes/KF-C.png --output video2.mp4
```

**Why `--free-memory` is mandatory for keyframes:**
- Multi-reference keyframe generation uses: Text Encoder (~8GB) + ControlNet (~3GB) + Diffusion Model (~12GB)
- Without clearing memory between generations, ControlNet may load first and consume all available VRAM
- This forces the diffusion model to run from CPU offload (0 MB in VRAM), causing 20+ minute generation times
- With `--free-memory`, each generation starts fresh with optimal memory allocation (~5 minutes)

---

## Quick Reference

| Script | Purpose | Key Arguments |
|--------|---------|---------------|
| `asset_generator.py` | Generate reusable assets | `character`, `background`, `pose`, `style` subcommands |
| `keyframe_generator.py` | Generate keyframes with identity+pose separation | `--prompt`, `--character`, `--background`, `--pose`, `--output` |
| `angle_transformer.py` | Transform keyframe camera angles | `--input`, `--output`, `--rotate`, `--tilt`, `--zoom` |
| `wan_video_comfyui.py` | Generate videos (WAN 2.1) | `--prompt`, `--start-frame`, `--end-frame`, `--output`, `--free-memory` |
| `setup_comfyui.py` | Setup and manage ComfyUI | `--check`, `--start`, `--models` |

**Remember:** Use `--free-memory` when switching between image and video generation!

### Asset Generation

| Asset Type | Command | Output |
|------------|---------|--------|
| **Character** | `asset_generator.py character --name X --description "..." -o path` | Neutral A-pose, white background |
| **Background** | `asset_generator.py background --name X --description "..." -o path` | Environment, no people |
| **Pose Reference** | `asset_generator.py pose-ref --name X --pose "..." -o path --extract-skeleton` | Clean ref + skeleton (RECOMMENDED) |
| **Pose Skeleton** | `asset_generator.py pose --source ref.jpg -o path` | Extract from existing image |
| **Style** | `asset_generator.py style --name X --description "..." -o path` | Style reference |

### Keyframe Generation

**IMPORTANT:** Always use `--free-memory` for every keyframe generation to prevent VRAM fragmentation.

| Mode | Command | Description |
|------|---------|-------------|
| **Single Character** | `keyframe_generator.py --free-memory --character X --pose Y --prompt "..."` | Character with pose control |
| **Multi-Character** | `keyframe_generator.py --free-memory --character A --character B --pose Y --prompt "..."` | Up to 3 characters |
| **Pose from Image** | `keyframe_generator.py --free-memory --character X --pose-image ref.jpg --prompt "..."` | Extract pose on-the-fly |
| **With Background** | `keyframe_generator.py --free-memory --background B --character X --character Y ...` | Background + 2 chars |

### Camera Angle Transformation

For scenes requiring dynamic camera angles, use the angle transformer after generating keyframes:

```bash
# Transform keyframe to low angle shot
python {baseDir}/scripts/angle_transformer.py \
  --input {output_dir}/keyframes/KF-A.png \
  --output {output_dir}/keyframes/KF-A-lowangle.png \
  --tilt -30 \
  --prompt "dramatic low angle action shot"

# Rotate camera 45 degrees left
python {baseDir}/scripts/angle_transformer.py \
  --input {output_dir}/keyframes/KF-B.png \
  --output {output_dir}/keyframes/KF-B-rotated.png \
  --rotate -45

# Wide angle with camera rotation
python {baseDir}/scripts/angle_transformer.py \
  --input {output_dir}/keyframes/KF-C.png \
  --output {output_dir}/keyframes/KF-C-wide.png \
  --rotate 30 \
  --zoom wide
```

**Angle Transformer Parameters:**
| Parameter | Range | Description |
|-----------|-------|-------------|
| `--rotate` | -180 to 180 | Horizontal rotation (negative = left) |
| `--tilt` | -90 to 90 | Vertical tilt (negative = look up) |
| `--zoom` | wide/normal/close | Lens type |
| `--prompt` | text | Custom angle description (optional) |

**Note:** Requires Multi-Angle LoRA. Run `setup_comfyui.py --models` to download.

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
| Image Steps | 4 (with Lightning LoRA) |
| Video Steps | 8 (with LightX2V LoRA) |

### Models Required (ComfyUI + GGUF)

**Video Generation (WAN 2.1):**
| Model | Size | Purpose |
|-------|------|---------|
| WAN 2.1 I2V Q4_K_M GGUF | ~11GB | Video generation |
| LightX2V LoRA | ~0.7GB | Fast 8-step generation |
| UMT5-XXL FP8 | ~5GB | Text encoder |
| WAN VAE | ~0.2GB | Video decoding |

**Keyframe Generation (Qwen Image Edit 2511):**
| Model | Size | Purpose |
|-------|------|---------|
| Qwen Image Edit Q4_K_M GGUF | ~13GB | Image generation |
| Lightning LoRA | ~0.8GB | Fast 4-step generation |
| Qwen VL 7B FP8 | ~8GB | Text encoder |
| Qwen VAE | ~0.2GB | Image decoding (tiled) |

Models are stored in `{baseDir}/comfyui/models/` directory.

See `README.md` for installation instructions.
See `references/prompt-engineering.md` for detailed prompt writing guidance.
See `references/troubleshooting.md` for common issues and solutions.
