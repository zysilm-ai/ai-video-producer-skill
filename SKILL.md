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
  like layer-based compositing, reference-based generation, and style
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

## Pipeline Modes

The pipeline supports three execution modes:

### v1.0 Keyframe-First Mode (Legacy)
Generate all keyframes first, then generate videos between keyframe pairs (FLF2V mode).

```
KF-A ─────────────→ Scene 1 ←───────────── KF-B
                                            │
KF-B ─────────────→ Scene 2 ←───────────── KF-C
```

**Pros:** Precise control over start and end frames
**Cons:** Each keyframe generated independently can cause background inconsistency

### v2.0 Video-First Mode
Generate only the first keyframe, then generate videos sequentially using I2V mode.
Each video's last frame becomes the next scene's start keyframe.

```
KF-A (generated) → Scene 1 → KF-B (extracted) → Scene 2 → KF-C (extracted)
```

**Pros:** Perfect visual continuity between scenes (same camera, lighting, position)
**Cons:** Less control over specific end frame composition

### v3.0 Scene/Segment Mode (Recommended)
Proper hierarchical structure distinguishing **Scenes** (narrative/cinematographic units) from **Segments** (5-second technical chunks).

**Key Concepts:**
- **Scene**: A continuous shot from a single camera perspective (e.g., "woman at cafe table", "phone screen close-up")
- **Segment**: A 5-second video chunk within a scene (due to model limitations)
- **Transition**: How scenes connect ("cut", "continuous", "fade", "dissolve")

```
Scene 1 (cut)           Scene 2 (continuous)       Scene 3 (fade)
┌─────────────────┐     ┌─────────────────┐       ┌─────────────────┐
│ KF (generated)  │     │ KF (extracted)  │       │ KF (generated)  │
│ ┌─────────────┐ │     │ ┌─────────────┐ │       │ ┌─────────────┐ │
│ │ Segment A   │ │     │ │ Segment A   │ │       │ │ Segment A   │ │
│ └─────────────┘ │     │ └─────────────┘ │       │ └─────────────┘ │
│ ┌─────────────┐ │     └─────────────────┘       └─────────────────┘
│ │ Segment B   │ │             │                         │
│ └─────────────┘ │             │ continuous              │ fade
└─────────────────┘             ▼                         ▼
        │ cut          ─────────────────          ─────────────────
        ▼              Final merged video with transitions
```

**Pros:**
- Semantic clarity (scenes = narrative units, segments = technical units)
- Scene-level keyframes (generated for cuts, extracted for continuous)
- Automatic video merging with transitions (cut, fade, dissolve)
- Hierarchical status tracking

**Cons:** More complex schema

**When to use each transition:**
| Transition | Use When | Keyframe |
|------------|----------|----------|
| `cut` | Camera angle/location changes | Generated (new) |
| `continuous` | Same shot continues (landscape only) | Extracted (from previous scene) |
| `fade` | Time skip, dramatic moment | Generated (new) |
| `dissolve` | Smooth transition between related scenes | Generated (new) |

**CRITICAL: Character Scenes and Continuous Transitions**

When a scene contains a character (even partially visible, like hands or clothing), **do NOT use `"extracted"` keyframes**. Extracted keyframes lose character identity anchoring and cause visual drift (e.g., clothing color changes, style inconsistency).

| Scene Type | Transition | Keyframe Type | Why |
|------------|------------|---------------|-----|
| Landscape (no characters) | `continuous` | `extracted` | OK - no character identity to preserve |
| Character visible | `continuous` | `generated` | REQUIRED - re-anchor character identity |
| Character visible | `cut` | `generated` | Standard - new camera angle |

**Rule:** If ANY part of a character is visible (hands, clothing, body), use `"type": "generated"` with character references.

## Pipeline Mode Selection (REQUIRED - Ask First)

**Before starting any work, ask the user which pipeline mode to use:**

Use AskUserQuestion with these options:
- **"Scene/Segment v3.0 (Recommended)"** - Best for longer videos with multiple scenes. Proper scene/segment hierarchy with automatic merging and transitions.
- **"Video-First v2.0"** - Simple sequential scenes. Best for short videos where all scenes are continuous.
- **"Keyframe-First v1.0"** - Legacy mode when you need precise control over specific end frame composition.

**Default recommendation:** Scene/Segment v3.0 for most use cases.

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

### Keyframe-First Mode

| Phase | LLM Actions | Required Outputs | Checkpoint |
|-------|-------------|------------------|------------|
| 0. Mode Selection | Ask user which pipeline mode | User's choice | **Ask before starting** |
| 1. Production Philosophy | Create visual identity & style | `philosophy.md`, `style.json` | User approval |
| 2. Scene Breakdown | Plan scenes & keyframes | `scene-breakdown.md` | User approval |
| 3. Pipeline Generation | Generate ALL prompts | `pipeline.json` | User approval |
| 4. Asset Execution | Run `execute_pipeline.py --stage assets` | `assets/` folder | LLM reviews with VLM, user approval |
| 5. Keyframe Execution | Run `execute_pipeline.py --stage keyframes` | `keyframes/*.png` | LLM reviews with VLM, user approval |
| 6. Video Execution | Run `execute_pipeline.py --stage videos` | `scene-*/video.mp4` | User approval |
| 7. Review & Iterate | Handle regeneration requests | Refinements | User signs off |

### Video-First Mode (v2.0)

| Phase | LLM Actions | Required Outputs | Checkpoint |
|-------|-------------|------------------|------------|
| 0. Mode Selection | Ask user which pipeline mode | User's choice | **Ask before starting** |
| 1. Production Philosophy | Create visual identity & style | `philosophy.md`, `style.json` | User approval |
| 2. Scene Breakdown | Plan scenes with motion prompts | `scene-breakdown.md` | User approval |
| 3. Pipeline Generation | Generate prompts with video-first schema | `pipeline.json` | User approval |
| 4. Asset Execution | Run `execute_pipeline.py --stage assets` | `assets/` folder | LLM reviews with VLM, user approval |
| 5. First Keyframe | Run `execute_pipeline.py --stage first_keyframe` | `keyframes/KF-A.png` | LLM reviews with VLM, user approval |
| 6. Scene Execution | Run `execute_pipeline.py --stage scenes` | `scene-*/video.mp4` + extracted keyframes | User approval |
| 7. Review & Iterate | Handle regeneration requests | Refinements | User signs off |

### Scene/Segment Mode (v3.0 - Recommended)

| Phase | LLM Actions | Required Outputs | Checkpoint |
|-------|-------------|------------------|------------|
| 0. Mode Selection | Ask user which pipeline mode | User's choice | **Ask before starting** |
| 1. Production Philosophy | Create visual identity & style | `philosophy.md`, `style.json` | User approval |
| 2. Scene Breakdown | Plan scenes with segments and transitions | `scene-breakdown.md` | User approval |
| 3. Pipeline Generation | Generate prompts with v3.0 schema | `pipeline.json` | User approval |
| 4. Asset Execution | Run `execute_pipeline.py --stage assets` | `assets/` folder | LLM reviews with VLM, user approval |
| 5. Scene Keyframes | Run `execute_pipeline.py --stage scene_keyframes` | `keyframes/scene-*.png` | LLM reviews with VLM, user approval |
| 6. Scene Execution | Run `execute_pipeline.py --stage scenes` | `scene-*/merged.mp4` + `final/video.mp4` | User approval |
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

| ID | Description | Character | Background | Used In |
|----|-------------|-----------|------------|---------|
| KF-A | [Description of this moment] | [character] | [background] | Scene 1 start |
| KF-B | [Description of this moment] | [character] | [background] | Scene 1 end, Scene 2 start |
| KF-C | [Description of this moment] | [character] | [background] | Scene 2 end |

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

# Style reference (example image in target style)
python {baseDir}/scripts/asset_generator.py style \
  --name [style_name] \
  --description "[style description]" \
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

## Phase 3: Pipeline Generation (REQUIRED)

**DO NOT PROCEED TO EXECUTION UNTIL `pipeline.json` EXISTS AND USER APPROVES**

This phase consolidates all prompts into a single structured file that will be executed deterministically.

### Step 3.1: Create pipeline.json

Based on philosophy.md, style.json, scene-breakdown.md, and assets.json, create a complete pipeline.json.

**Choose the schema based on your pipeline mode:**

#### Keyframe-First Schema (Default)

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
    }
  },

  "keyframes": [
    {
      "id": "KF-A",
      "type": "character",
      "prompt": "Scene description with character positions and actions...",
      "background": "<background_id>",
      "characters": ["<character_id_1>", "<character_id_2>"],
      "settings": {
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

#### Video-First Schema (Recommended for continuity)

```json
{
  "version": "2.0",
  "project_name": "project-name",

  "metadata": {
    "created_at": "ISO timestamp",
    "philosophy_file": "philosophy.md",
    "style_file": "style.json",
    "scene_breakdown_file": "scene-breakdown.md"
  },

  "assets": {
    "characters": { ... },
    "backgrounds": { ... }
  },

  "first_keyframe": {
    "id": "KF-A",
    "type": "landscape",
    "prompt": "First scene starting point - detailed visual description...",
    "background": "<background_id>",
    "characters": [],
    "settings": {
      "preset": "medium"
    },
    "output": "keyframes/KF-A.png",
    "status": "pending"
  },

  "scenes": [
    {
      "id": "scene-01",
      "motion_prompt": "Motion description - what happens in this scene...",
      "start_keyframe": "KF-A",
      "output_video": "scene-01/video.mp4",
      "output_keyframe": "keyframes/KF-B.png",
      "status": "pending"
    },
    {
      "id": "scene-02",
      "motion_prompt": "Motion description for scene 2...",
      "start_keyframe": "KF-B",
      "output_video": "scene-02/video.mp4",
      "output_keyframe": "keyframes/KF-C.png",
      "status": "pending"
    }
  ]
}
```

**Video-First Schema Key Differences:**
- `first_keyframe`: Single object (not array) - only the first keyframe is generated traditionally
- `scenes`: Array replacing `videos` - each scene uses I2V mode (start frame only)
- `motion_prompt`: Describes what happens during the scene (no end frame)
- `output_keyframe`: Where to save the extracted last frame (becomes next scene's start)
- `start_keyframe`: References either `first_keyframe.id` or previous scene's extracted keyframe

#### Scene/Segment Schema v3.0 (Recommended)

```json
{
  "version": "3.0",
  "project_name": "project-name",

  "metadata": {
    "created_at": "ISO timestamp",
    "philosophy_file": "philosophy.md",
    "style_file": "style.json",
    "scene_breakdown_file": "scene-breakdown.md"
  },

  "assets": {
    "characters": {
      "cafe_woman": {
        "prompt": "Character description...",
        "output": "assets/characters/cafe_woman.png",
        "status": "pending"
      }
    },
    "backgrounds": {
      "cafe_interior": {
        "prompt": "Background description...",
        "output": "assets/backgrounds/cafe_interior.png",
        "status": "pending"
      }
    }
  },

  "scenes": [
    {
      "id": "scene-01",
      "description": "Woman notices phone notification",
      "camera": "medium close-up",

      "transition_from_previous": null,

      "first_keyframe": {
        "type": "generated",
        "prompt": "Detailed keyframe description...",
        "background": "cafe_interior",
        "characters": ["cafe_woman"],
        "output": "keyframes/scene-01-start.png",
        "status": "pending"
      },

      "segments": [
        {
          "id": "seg-01-a",
          "motion_prompt": "Woman sighs, reaches for phone...",
          "output_video": "scene-01/seg-a.mp4",
          "output_keyframe": "keyframes/scene-01-seg-a-end.png",
          "status": "pending"
        },
        {
          "id": "seg-01-b",
          "motion_prompt": "Woman picks up phone, reads message...",
          "output_video": "scene-01/seg-b.mp4",
          "output_keyframe": "keyframes/scene-01-seg-b-end.png",
          "status": "pending"
        }
      ],

      "output_video": "scene-01/merged.mp4",
      "status": "pending"
    },
    {
      "id": "scene-02",
      "description": "Phone screen close-up",
      "camera": "extreme close-up",

      "transition_from_previous": {
        "type": "cut"
      },

      "first_keyframe": {
        "type": "generated",
        "prompt": "Extreme close-up of smartphone screen...",
        "output": "keyframes/scene-02-start.png",
        "status": "pending"
      },

      "segments": [
        {
          "id": "seg-02-a",
          "motion_prompt": "Message notification appears on screen...",
          "output_video": "scene-02/seg-a.mp4",
          "output_keyframe": "keyframes/scene-02-seg-a-end.png",
          "status": "pending"
        }
      ],

      "output_video": "scene-02/merged.mp4",
      "status": "pending"
    },
    {
      "id": "scene-03",
      "description": "Woman's reaction (continuous from scene-02)",
      "camera": "medium close-up",

      "transition_from_previous": {
        "type": "continuous"
      },

      "first_keyframe": {
        "type": "extracted"
      },

      "segments": [
        {
          "id": "seg-03-a",
          "motion_prompt": "Woman's expression changes to shock...",
          "output_video": "scene-03/seg-a.mp4",
          "output_keyframe": "keyframes/scene-03-seg-a-end.png",
          "status": "pending"
        }
      ],

      "output_video": "scene-03/merged.mp4",
      "status": "pending"
    }
  ],

  "final_video": {
    "output": "final/video.mp4",
    "status": "pending"
  }
}
```

**v3.0 Schema Key Concepts:**

| Field | Description |
|-------|-------------|
| `scenes[].first_keyframe.type` | `"generated"` = create new keyframe with character refs, `"extracted"` = use previous scene's end (landscape only!) |
| `scenes[].first_keyframe.characters` | Array of character IDs to reference - **REQUIRED if character is visible** |
| `scenes[].transition_from_previous` | `null` for first scene, or `{"type": "cut/continuous/fade/dissolve"}` |
| `scenes[].segments[]` | Array of 5-second video chunks within the scene |
| `segments[].output_keyframe` | Extracted last frame (required for all but last segment) |
| `scenes[].output_video` | Merged video of all segments in this scene |
| `final_video` | All scene videos merged with transitions |

**Keyframe Type Selection (CRITICAL for consistency):**

| Scene Content | `first_keyframe.type` | `characters` array | Notes |
|---------------|----------------------|-------------------|-------|
| Character fully visible | `"generated"` | Required | Include all visible characters |
| Character partially visible (hands, clothing) | `"generated"` | Required | Include character for clothing/style consistency |
| Landscape only (no characters) | `"generated"` or `"extracted"` | Optional | Can use extracted for continuous transitions |

**Transition Types:**
- `cut`: Hard cut (instant switch between scenes)
- `continuous`: Seamless continuation - use `"extracted"` ONLY for landscape scenes, use `"generated"` with character refs for character scenes
- `fade`: Fade through black (duration configurable, default 0.5s)
- `dissolve`: Cross-dissolve (duration configurable, default 0.5s)

### Step 3.2: Pipeline Prompt Writing Guidelines

**For Character Prompts:**
- Include full physical description (hair, eyes, clothing, distinguishing features)
- Mention "anime style character sheet, A-pose, full body, white background"
- Include multiple views: "front view, side view, back view"

**For Background Prompts:**
- Describe setting, lighting, atmosphere
- Include "no people, establishing shot"
- Match style from philosophy.md

**For Keyframe Prompts:**
- Use positional language: "On the left:", "On the right:", "In the center:"
- Reference character appearance from assets
- Include background context and lighting
- Match style from philosophy.md

**For Video Prompts (I2V Motion Prompts):**

I2V (Image-to-Video) models suffer from "suppressed motion dynamics" - they tend to preserve the input image too faithfully, resulting in static or minimal motion videos. This happens because the model "locks onto" fine details in the reference image during early denoising steps.

**CRITICAL RULES for Motion Prompts:**

1. **Separate SUBJECT motion from CAMERA motion** - describe both explicitly
2. **Describe physical body movements** - "legs pumping", "arms swinging", "torso twisting"
3. **Include environmental interaction** - "boots splashing through mud", "debris flying past"
4. **Avoid POV/first-person** - I2V models struggle with perspective-based motion
5. **Use motion verbs, not state verbs** - "running" not "in motion", "swinging" not "holding"

**BAD Prompt Examples (will produce static video):**
- ❌ "POV camera moving forward through battlefield" (ambiguous camera vs subject)
- ❌ "soldier in action" (no specific motion described)
- ❌ "dynamic scene with explosions" (describes scene, not motion)
- ❌ "first-person gunfire perspective" (POV is problematic for I2V)

**GOOD Prompt Examples (will produce dynamic video):**

| Scenario | Motion Prompt |
|----------|---------------|
| **Running forward** | "soldier physically sprinting forward, legs pumping rapidly, arms swinging rifle, boots kicking up dirt, body leaning into run, camera tracking from behind" |
| **Combat action** | "warrior swings sword in wide horizontal arc, body rotating with momentum, cape flowing behind movement, enemy staggers backward from impact" |
| **Walking scene** | "woman walks along beach, each footstep pressing into wet sand, hair flowing in wind, dress rippling with each stride, waves washing past ankles" |
| **Vehicle motion** | "car accelerates down highway, scenery blurring past windows, suspension bouncing over bumps, wheels spinning faster" |
| **Dance/Performance** | "dancer spins with arms extended, skirt flaring outward, one leg lifting into pirouette, spotlight following rotation" |

**Motion Prompt Structure:**
```
[SUBJECT] [ACTION VERB] [BODY PART DETAILS], [ENVIRONMENTAL INTERACTION], [SECONDARY MOTION], camera [CAMERA MOVEMENT]
```

**Example applying the structure:**
```
soldier sprints through muddy trench,
legs driving forward with each powerful stride,
rifle bouncing against chest,
mud splashing from boots,
smoke and debris whipping past face,
camera tracking steadily from behind at shoulder height
```

**Camera Movement Terms:**
- "camera tracking from behind" - follows subject from rear
- "camera dollying alongside" - moves parallel to subject
- "camera pushing in slowly" - gradual zoom effect
- "camera holding steady" - static camera, subject moves through frame
- "camera panning left/right" - rotational movement
- "camera tilting up/down" - vertical rotation

**References:**
- [ALG: Enhancing Motion Dynamics of I2V Models](https://arxiv.org/abs/2506.08456)
- [Wan2.2 Prompt Guide](https://www.instasd.com/post/wan2-2-whats-new-and-how-to-write-killer-prompts)

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
- Generate all characters, backgrounds defined in pipeline.json
- Automatically use `--free-memory` for each generation
- Update status in pipeline.json as items complete

### Step 4.2: Review Assets with VLM

After execution completes, use the Read tool to view each generated asset:

```
1. View each character asset - verify appearance matches description
2. View each background asset - verify setting and style
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
3. Check background consistency
4. Check style matches philosophy
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
| **Background** | Chain from previous scene's background for continuity |
| **Style** | ALWAYS apply with style asset reference |

### Character Consistency Rules (CRITICAL)

**Problem:** Without character references, I2V models cause "identity drift" - clothing colors change, styles shift, and characters become unrecognizable across scenes.

**Solution:** Include character references for ANY scene where the character is visible, even partially.

**When to include character references:**

| What's Visible | Include Character Reference? | Example |
|----------------|------------------------------|---------|
| Full body | YES | Wide shot of character walking |
| Upper body only | YES | Medium shot conversation |
| Hands only | YES | Close-up of hands holding object |
| Clothing only (no face) | YES | Back view of character running |
| Character's belongings | Optional | Close-up of character's bag |
| No character elements | NO | Landscape, building exterior |

**Common Mistakes to Avoid:**

1. **Close-up shots without character reference:**
   ```json
   // WRONG - hands visible but no character reference
   "first_keyframe": {
     "type": "generated",
     "prompt": "Close-up of hands holding cake...",
     "characters": []  // Missing!
   }

   // CORRECT - include character for clothing consistency
   "first_keyframe": {
     "type": "generated",
     "prompt": "Close-up of hands in grey hoodie holding cake...",
     "characters": ["protagonist"]  // Anchors clothing style
   }
   ```

2. **Continuous transitions with characters:**
   ```json
   // WRONG - extracted keyframe loses character identity
   "first_keyframe": {
     "type": "extracted"  // Character will drift!
   }

   // CORRECT - generated keyframe re-anchors identity
   "first_keyframe": {
     "type": "generated",
     "prompt": "Character running away...",
     "characters": ["protagonist"],
     "background": "train_station"
   }
   ```

**The Character Drift Problem:**

When keyframes are "extracted" from video end frames or generated without character references:
- Scene 1 → Scene 2 → Scene 3 → Scene 4
- Each scene accumulates small deviations
- By Scene 4, character may be unrecognizable (different clothing color, style)

**The Solution - Re-anchor at every character scene:**
- Always use `"type": "generated"` for scenes with characters
- Always include the character in the `"characters"` array
- Use the original asset from `assets/characters/` (never chain from previous keyframes)

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
- **Action** (WHAT happening) - from `--prompt`

**Single character keyframe:**
```bash
python {baseDir}/scripts/keyframe_generator.py \
  --free-memory \
  --prompt "[Action description], [expression], [environment context]" \
  --character {output_dir}/assets/characters/[character_name].png \
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
  --output {output_dir}/keyframes/KF-B.png
```

**Reference Slot Allocation:**
| Slot | Without --background | With --background |
|------|---------------------|-------------------|
| image1 | Character 1 | Background |
| image2 | Character 2 | Character 1 |
| image3 | Character 3 | Character 2 |

**Note:** With `--background`, maximum 2 characters are supported (3 reference slots total).

### Character Count Decision Matrix

The system has 3 reference image slots. Use this matrix to determine the approach:

| # Characters | Background | Approach |
|--------------|------------|----------|
| 0 | Any | Use `landscape` type with `asset_generator.py background` |
| 1 | No | `--character A` (empty slots auto-filled with fallback) |
| 1 | Yes | `--background B --character A` (empty slot auto-filled) |
| 2 | No | `--character A --character B` (slot 3 auto-filled) |
| 2 | Yes | `--background B --character A --character B` (all slots used) |
| 3 | No | `--character A --character B --character C` (all slots used) |
| 3+ | Yes | **Workaround required** - see below |
| 4+ | Any | **Workaround required** - see below |

**Handling 3+ Characters with Background OR 4+ Characters Total:**

When exceeding 3 reference slots, use this workaround:

1. **Select 2-3 most important characters** for reference slots (strongest identity consistency)
2. **Describe ALL characters in prompt** with positional language:
   ```
   "On the far left: [char1 detailed appearance]. In the center: [char2 detailed appearance].
   On the right: [char3 detailed appearance]. Behind them: [char4 detailed appearance]."
   ```
3. **Trade-off**: Referenced characters have strong identity; others rely on prompt description

**Example for 4 characters with background:**
```bash
# Generate with 2 most important characters as references
python {baseDir}/scripts/keyframe_generator.py \
  --free-memory \
  --prompt "On the left: warrior in red armor with sword. Second from left: mage in blue robes with staff. On the right: archer in green cloak with bow. Far right: healer in white dress with golden hair." \
  --background {output_dir}/assets/backgrounds/battlefield.png \
  --character {output_dir}/assets/characters/warrior.png \
  --character {output_dir}/assets/characters/mage.png \
  --output {output_dir}/keyframes/KF-group.png
```

In this example, warrior and mage have strong identity from references; archer and healer are generated from prompt descriptions.

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

At the START of the workflow, create this todo list based on your pipeline mode:

### Keyframe-First Mode

```
1. Ask user: Video-First or Keyframe-First? (user chose Keyframe-First)
2. Check ComfyUI setup and start server
3. Create philosophy.md
4. Create style.json
5. Get user approval on production philosophy
6. Create scene-breakdown.md with unique keyframes table
7. Get user approval on scene breakdown
8. Create pipeline.json with ALL prompts (assets, keyframes, videos)
9. Get user approval on pipeline.json
10. Execute asset stage: python execute_pipeline.py pipeline.json --stage assets
11. Review assets with VLM, get user approval
12. Execute keyframe stage: python execute_pipeline.py pipeline.json --stage keyframes
13. Review keyframes with VLM, get user approval
14. Execute video stage: python execute_pipeline.py pipeline.json --stage videos
15. Get user approval on videos
16. Provide final summary to user
```

### Video-First Mode (v2.0)

```
1. Ask user: Video-First or Keyframe-First? (user chose Video-First)
2. Check ComfyUI setup and start server
3. Create philosophy.md
4. Create style.json
5. Get user approval on production philosophy
6. Create scene-breakdown.md with motion prompts (no end keyframes)
7. Get user approval on scene breakdown
8. Create pipeline.json with video-first schema (first_keyframe + scenes)
9. Get user approval on pipeline.json
10. Execute asset stage: python execute_pipeline.py pipeline.json --stage assets
11. Review assets with VLM, get user approval
12. Execute first keyframe: python execute_pipeline.py pipeline.json --stage first_keyframe
13. Review first keyframe with VLM, get user approval
14. Execute scenes: python execute_pipeline.py pipeline.json --stage scenes
15. Get user approval on videos (keyframes auto-extracted between scenes)
16. Provide final summary to user
```

### Scene/Segment Mode (v3.0 - Recommended)

```
1. Ask user: Scene/Segment v3.0, Video-First v2.0, or Keyframe-First v1.0? (user chose v3.0)
2. Check ComfyUI setup and start server
3. Create philosophy.md
4. Create style.json
5. Get user approval on production philosophy
6. Create scene-breakdown.md with scenes, segments, and transitions
7. Get user approval on scene breakdown
8. Create pipeline.json with v3.0 schema (scenes with segments + final_video)
9. Get user approval on pipeline.json
10. Execute asset stage: python execute_pipeline.py pipeline.json --stage assets
11. Review assets with VLM, get user approval
12. Execute scene keyframes: python execute_pipeline.py pipeline.json --stage scene_keyframes
13. Review scene keyframes with VLM, get user approval
14. Execute scenes: python execute_pipeline.py pipeline.json --stage scenes
15. Get user approval on scene videos and final merged video
16. Provide final summary to user
```

**Key points:**
- ALL prompts are written to pipeline.json BEFORE any generation starts
- User approves the complete plan before execution
- execute_pipeline.py handles VRAM management automatically
- LLM reviews outputs with VLM after each stage
- v3.0 mode generates scene keyframes for "cut" transitions, extracts for "continuous"
- Segments within scenes are automatically merged
- Final video is automatically assembled with transitions

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

1. **ALWAYS use `--free-memory` for EVERY keyframe generation** - Memory fragmentation between generations can cause VRAM issues, resulting in slower generation times

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
python asset_generator.py background --name forest --description "..." --output assets/backgrounds/forest.png

# Generate keyframes - ALWAYS use --free-memory to prevent VRAM fragmentation
python keyframe_generator.py --free-memory --character assets/hero.png --prompt "hero standing ready" --output keyframes/KF-A.png
python keyframe_generator.py --free-memory --character assets/hero.png --prompt "hero in combat" --output keyframes/KF-B.png
python keyframe_generator.py --free-memory --character assets/hero.png --prompt "hero victorious" --output keyframes/KF-C.png

# Switch to video - FREE MEMORY FIRST
python wan_video_comfyui.py --free-memory --prompt "..." --start-frame keyframes/KF-A.png --end-frame keyframes/KF-B.png --output video1.mp4

# Generate more videos (WAN stays warm)
python wan_video_comfyui.py --prompt "..." --start-frame keyframes/KF-B.png --end-frame keyframes/KF-C.png --output video2.mp4
```

**Why `--free-memory` is mandatory for keyframes:**
- Multi-reference keyframe generation uses: Text Encoder (~8GB) + Diffusion Model (~6GB)
- Without clearing memory between generations, models may not load optimally
- With `--free-memory`, each generation starts fresh with optimal memory allocation (~2 minutes)

---

## Quick Reference

| Script | Purpose | Key Arguments |
|--------|---------|---------------|
| `execute_pipeline.py` | Execute complete pipeline | `--stage`, `--all`, `--status`, `--validate`, `--regenerate` |
| `asset_generator.py` | Generate reusable assets | `character`, `background`, `style` subcommands |
| `keyframe_generator.py` | Generate keyframes with character references | `--prompt`, `--character`, `--background`, `--output` |
| `angle_transformer.py` | Transform keyframe camera angles | `--input`, `--output`, `--rotate`, `--tilt`, `--zoom` |
| `wan_video_comfyui.py` | Generate videos (WAN 2.1) | `--prompt`, `--start-frame`, `--end-frame`, `--output`, `--free-memory` |
| `video_merger.py` | Merge videos with transitions | `--concat`, `--output`, `--transition`, `--duration` |
| `setup_comfyui.py` | Setup and manage ComfyUI | `--check`, `--start`, `--models` |

### Pipeline Execution

| Stage | v1.0 Keyframe-First | v2.0 Video-First | v3.0 Scene/Segment |
|-------|---------------------|------------------|-------------------|
| Assets | `--stage assets` | `--stage assets` | `--stage assets` |
| Keyframes | `--stage keyframes` | `--stage first_keyframe` | `--stage scene_keyframes` |
| Videos | `--stage videos` | `--stage scenes` | `--stage scenes` |
| All stages | `--all` | `--all` | `--all` |

**v3.0 Key Features:**
- Scene keyframes generated for "cut" transitions, extracted for "continuous"
- Segments within scenes merged automatically
- Final video assembled with transitions (cut/fade/dissolve)

**Remember:** Use `--free-memory` when switching between image and video generation!

### Asset Generation

| Asset Type | Command | Output |
|------------|---------|--------|
| **Character** | `asset_generator.py character --name X --description "..." -o path` | Neutral A-pose, white background |
| **Background** | `asset_generator.py background --name X --description "..." -o path` | Environment, no people |
| **Style** | `asset_generator.py style --name X --description "..." -o path` | Style reference |

### Keyframe Generation

**IMPORTANT:** Always use `--free-memory` for every keyframe generation to prevent VRAM fragmentation.

| Mode | Command | Description |
|------|---------|-------------|
| **Single Character** | `keyframe_generator.py --free-memory --character X --prompt "..."` | Character from reference |
| **Multi-Character** | `keyframe_generator.py --free-memory --character A --character B --prompt "..."` | Up to 3 characters |
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

### Video Model Selection (IMPORTANT)

**Choose the appropriate model/mode based on scene requirements:**

| Flag | Model | Time | Quality | Motion | When to Use |
|------|-------|------|---------|--------|-------------|
| (none) | WAN 2.1 Q4K + LoRA | ~6 min | Good | Standard | Default for most scenes |
| `--moe-fast` | WAN 2.2 MoE + ALG | ~7 min | Better | Enhanced | **RECOMMENDED** - Best balance |
| `--moe` | WAN 2.2 MoE (20 steps) | ~30 min | Best | Standard | Maximum quality, time not critical |

**Decision Guide for LLM:**

```
IF scene requires maximum quality AND time is not critical:
    USE --moe (20 steps, best quality)

ELSE (most scenes - RECOMMENDED):
    USE --moe-fast
    - Includes ALG for enhanced motion dynamics
    - Better character consistency
    - Reduces morphing artifacts

ELSE IF fastest generation needed and motion not critical:
    USE default (no flag) - fastest option
```

**About ALG (included in --moe-fast):**
- PRO: ~36% improved motion dynamics (less static video)
- PRO: Better character consistency during complex motion
- PRO: Reduces morphing/shape-shifting artifacts
- NOTE: Slightly reduced input fidelity (intentional - allows more motion freedom)

**Motion Limitations (applies to ALL modes):**
- I2V models preserve the subject's pose from the input image
- A static pose in the input = static pose in the video
- For running/dynamic poses: the starting keyframe must show the subject mid-action
- Camera motion works better than subject body motion in I2V

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

**Video Generation (WAN 2.1 - Default):**
| Model | Size | Purpose |
|-------|------|---------|
| WAN 2.1 I2V Q4_K_M GGUF | ~11GB | Video generation |
| LightX2V LoRA | ~0.7GB | Fast 8-step generation |
| UMT5-XXL FP8 | ~5GB | Text encoder |
| WAN VAE | ~0.2GB | Video decoding |

**Video Generation (WAN 2.2 MoE - for --moe/--moe-fast):**
| Model | Size | Purpose |
|-------|------|---------|
| WAN 2.2 I2V HighNoise Q6_K GGUF | ~12GB | MoE high-noise expert |
| WAN 2.2 I2V LowNoise Q6_K GGUF | ~12GB | MoE low-noise expert |

To download WAN 2.2 models: `python scripts/setup_comfyui.py --q6k`

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
