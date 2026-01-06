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

**Requires:** WAN 2.1 + Qwen Image Edit via ComfyUI (GGUF quantization, ~40GB models)

### Setup Commands
```bash
python {baseDir}/scripts/setup_comfyui.py         # Full setup (first time)
python {baseDir}/scripts/setup_comfyui.py --check # Verify setup
python {baseDir}/scripts/setup_comfyui.py --start # Start server before generating
```

### System Requirements
| Component | Minimum |
|-----------|---------|
| GPU VRAM | 10GB |
| RAM | 16GB |
| Storage | 40GB free |

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

## Pipeline Mode: Scene/Segment v3.0
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

**MANDATORY FORMAT - v3.0 Scene/Segment structure:**

```markdown
# Scene Breakdown: [Project Name]

## Overview
- **Total Duration**: [X seconds]
- **Number of Scenes**: [N]
- **Video Type**: [promotional/narrative/educational/etc.]
- **Pipeline Mode**: Scene/Segment v3.0

---

## Scene Overview

| Scene | Description | Camera | Transition | Duration |
|-------|-------------|--------|------------|----------|
| 1 | [Brief description] | [Camera type] | - | 5s |
| 2 | [Brief description] | [Camera type] | cut/continuous | 5s |

---

## Scenes

### Scene N: [Title]

**Type**: character | landscape
**Duration**: 5 seconds
**Camera**: [static/tracking/pan/zoom]
**Purpose**: [What this scene communicates]

**First Keyframe**: Generated (character scenes) OR Extracted (continuous landscape only)
- Characters: [list IDs - REQUIRED if visible]
- Background: [background ID]

**Segments**:
| ID | Motion | Duration |
|----|--------|----------|
| seg-Na | [Motion description] | 5s |

**Transition to Next**: cut | continuous | fade

[Repeat for all scenes]
```

**Scene Type Explanation:**
- `character`: Scenes with characters - MUST include character references in keyframe
- `landscape`: Scenes without characters - can use extracted keyframes for continuous transitions

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

### Step 2.5.3: Asset Generation

Assets are generated via `execute_pipeline.py --stage assets`. This phase defines assets in `assets.json` for later execution.

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

#### Pipeline Schema v3.0

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
      "protagonist": {
        "prompt": "Character sheet description...",
        "output": "assets/characters/protagonist.png",
        "status": "pending"
      }
    },
    "backgrounds": {
      "location": {
        "prompt": "Background description...",
        "output": "assets/backgrounds/location.png",
        "status": "pending"
      }
    }
  },
  "scenes": [
    {
      "id": "scene-01",
      "description": "Scene description",
      "camera": "medium shot",
      "transition_from_previous": null,
      "first_keyframe": {
        "type": "generated",
        "prompt": "Keyframe description...",
        "background": "location",
        "characters": ["protagonist"],
        "output": "keyframes/scene-01-start.png",
        "status": "pending"
      },
      "segments": [
        {
          "id": "seg-01-a",
          "motion_prompt": "Motion description...",
          "output_video": "scene-01/seg-a.mp4",
          "output_keyframe": "keyframes/scene-01-seg-a-end.png",
          "status": "pending"
        }
      ],
      "output_video": "scene-01/merged.mp4",
      "status": "pending"
    }
  ],
  "final_video": {
    "output": "final/video.mp4",
    "status": "pending"
  }
}
```

**Additional scene examples:**
- **Cut transition:** `"transition_from_previous": {"type": "cut"}`
- **Continuous (landscape only):** `"transition_from_previous": {"type": "continuous"}, "first_keyframe": {"type": "extracted"}`

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

I2V models tend to produce static video. Use these rules:

1. **Separate subject motion from camera motion** - describe both explicitly
2. **Describe physical body movements** - "legs pumping", "arms swinging", not just "running"
3. **Include environmental interaction** - "boots splashing through mud", "hair flowing in wind"
4. **Avoid POV/first-person** - I2V struggles with perspective-based motion
5. **Use motion verbs** - "sprinting" not "in motion"

**Motion Prompt Structure:**
```
[SUBJECT] [ACTION VERB] [BODY PART DETAILS], [ENVIRONMENTAL INTERACTION], camera [CAMERA MOVEMENT]
```

**Example:** "soldier sprints through trench, legs driving forward, rifle bouncing against chest, mud splashing from boots, camera tracking from behind at shoulder height"

**Camera Terms:** "tracking from behind", "dollying alongside", "pushing in slowly", "holding steady", "panning left/right", "tilting up/down"

See `references/prompt-engineering.md` for detailed guidance.

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

### v3.0 Keyframe Strategy

In Scene/Segment v3.0 mode:
- Each scene has ONE first keyframe (generated or extracted)
- Video generation uses I2V: first keyframe + motion prompt → video
- End frames are automatically extracted from generated videos

```
Scene 1 (cut)         Scene 2 (cut)         Scene 3 (continuous)
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ KF generated│       │ KF generated│       │ KF extracted│
│     ↓       │       │     ↓       │       │     ↓       │
│ I2V video   │ ──→   │ I2V video   │ ──→   │ I2V video   │
│     ↓       │       │     ↓       │       │     ↓       │
│ End extract │       │ End extract │       │ End extract │
└─────────────┘       └─────────────┘       └─────────────┘
```

### Scene Type and Keyframe Rules

| Scene Type | Keyframe Type | Character Refs | Notes |
|------------|---------------|----------------|-------|
| `character` (any character visible) | Generated | REQUIRED | Always re-anchor identity |
| `landscape` (no characters) | Generated or Extracted | Optional | Can use extracted for continuous |

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

**Common Mistakes:**
- Close-up of hands without character reference → clothing inconsistency
- Using `"type": "extracted"` for character scenes → identity drift

**The Character Drift Problem:** Without character references, each scene accumulates deviations. By Scene 4, character may have different clothing color/style.

**Solution:** Always use `"type": "generated"` with `"characters": ["id"]` for any scene with visible character parts.

### Reference Slot Allocation

The keyframe generator uses 3 reference image slots:

| Slot | Without --background | With --background |
|------|---------------------|-------------------|
| image1 | Character 1 | Background |
| image2 | Character 2 | Character 1 |
| image3 | Character 3 | Character 2 |

**Note:** With `--background`, maximum 2 characters are supported (3 slots total).

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

**Handling 3+ Characters with Background OR 4+ Characters:**

When exceeding 3 reference slots:
1. Select 2-3 most important characters for reference slots
2. Describe ALL characters in prompt with positional language
3. Trade-off: Referenced characters have strong identity; others rely on prompt

### Keyframe Quality Checklist

Before proceeding to video, verify EACH keyframe:
- Subject appears correctly (no distortion)
- Style matches Production Philosophy
- Composition allows for intended motion
- Characters are consistent with assets
- Background/environment is consistent
- Lighting direction is consistent

**Key Rule:** NEVER chain keyframes as references - always use original assets from `assets/characters/`

---

## Output Directory Structure (REQUIRED)

```
{output_dir}/
├── philosophy.md              # Production philosophy
├── style.json                 # Style configuration
├── scene-breakdown.md         # Scene breakdown with segments
├── pipeline.json              # v3.0 pipeline definition
│
├── assets/                    # Reusable character/background assets
│   ├── characters/
│   │   ├── protagonist.png
│   │   └── sidekick.png
│   └── backgrounds/
│       ├── city_street.png
│       └── rooftop.png
│
├── keyframes/                 # Scene start keyframes + extracted end frames
│   ├── scene-01-start.png    # Generated from assets
│   ├── scene-01-seg-a-end.png # Extracted from video
│   ├── scene-02-start.png    # Generated (cut) or extracted (continuous)
│   └── scene-02-seg-a-end.png
│
├── scene-01/
│   ├── seg-a.mp4             # Segment video
│   └── merged.mp4            # Scene merged video
│
├── scene-02/
│   ├── seg-a.mp4
│   └── merged.mp4
│
└── final/
    └── video.mp4             # All scenes merged
```

**Note:** Each scene has one start keyframe. End frames are extracted from generated videos, not pre-generated.

---

## TodoWrite Template

At the START of the workflow, create this todo list:

```
1. Check ComfyUI setup and start server
2. Create philosophy.md
3. Create style.json
4. Get user approval on production philosophy
5. Create scene-breakdown.md with scenes, segments, and transitions
6. Get user approval on scene breakdown
7. Create pipeline.json with v3.0 schema (scenes with segments + final_video)
8. Get user approval on pipeline.json
9. Execute asset stage: python execute_pipeline.py pipeline.json --stage assets
10. Review assets with VLM, get user approval
11. Execute scene keyframes: python execute_pipeline.py pipeline.json --stage scene_keyframes
12. Review scene keyframes with VLM, get user approval
13. Execute scenes: python execute_pipeline.py pipeline.json --stage scenes
14. Get user approval on scene videos and final merged video
15. Provide final summary to user
```

**Key points:**
- ALL prompts are written to pipeline.json BEFORE any generation starts
- User approves the complete plan before execution
- execute_pipeline.py handles VRAM management automatically
- LLM reviews outputs with VLM after each stage
- Scene keyframes generated for "cut" transitions, extracted for "continuous" (landscape only)
- Segments within scenes are automatically merged
- Final video is automatically assembled with transitions

### Setup Verification (Step 1)

```bash
python {baseDir}/scripts/setup_comfyui.py --check   # Verify setup
python {baseDir}/scripts/setup_comfyui.py --start   # Start ComfyUI server
```

### VRAM Management

**Note:** `execute_pipeline.py` handles VRAM management automatically with `--free-memory` flags.
The Qwen image model and WAN video model cannot both fit in 10GB VRAM simultaneously - the executor handles this.

---

## Quick Reference

| Script | Purpose | Key Arguments |
|--------|---------|---------------|
| `execute_pipeline.py` | Execute complete pipeline | `--stage`, `--all`, `--status`, `--validate`, `--regenerate` |
| `asset_generator.py` | Generate reusable assets | `character`, `background`, `style` subcommands |
| `keyframe_generator.py` | Generate keyframes with character references | `--prompt`, `--character`, `--background`, `--output` |
| `angle_transformer.py` | Transform keyframe camera angles | `--input`, `--output`, `--rotate`, `--tilt`, `--zoom` |
| `wan_video_comfyui.py` | Generate videos (WAN 2.1 I2V) | `--prompt`, `--start-frame`, `--output`, `--free-memory` |
| `video_merger.py` | Merge videos with transitions | `--concat`, `--output`, `--transition`, `--duration` |
| `setup_comfyui.py` | Setup and manage ComfyUI | `--check`, `--start`, `--models` |

### Pipeline Execution

| Stage | Command | Description |
|-------|---------|-------------|
| Assets | `--stage assets` | Generate character sheets and backgrounds |
| Scene Keyframes | `--stage scene_keyframes` | Generate keyframes for each scene |
| Scenes | `--stage scenes` | Generate videos, merge segments, create final video |
| All stages | `--all` | Run complete pipeline |

**Key Features:**
- Scene keyframes generated for "cut" transitions, extracted for "continuous" (landscape only)
- Segments within scenes merged automatically
- Final video assembled with transitions (cut/fade/dissolve)

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

Transform keyframes using `angle_transformer.py`:
- `--rotate`: -180 to 180 (horizontal rotation, negative = left)
- `--tilt`: -90 to 90 (vertical tilt, negative = look up)
- `--zoom`: wide/normal/close
- Requires Multi-Angle LoRA

### Video Generation (I2V Mode)

This skill uses **Image-to-Video (I2V)** mode exclusively:
- Input: Start keyframe + Motion prompt
- Output: Video + Extracted end frame

### Video Model Selection

| Flag | Time | Quality | When to Use |
|------|------|---------|-------------|
| (none) | ~6 min | Good | Fast generation |
| `--moe-fast` | ~7 min | Better | **RECOMMENDED** - Best balance with ALG motion enhancement |
| `--moe` | ~30 min | Best | Maximum quality when time not critical |

**Motion Limitations:** I2V preserves the subject's pose from input image. For dynamic poses, keyframe must show subject mid-action. Camera motion works better than body motion.

### Technical Specs

| Parameter | Value |
|-----------|-------|
| Video Duration | ~5 seconds (81 frames) |
| Frame Rate | 16 fps |
| Resolution | Up to 832x480 (medium preset) |
| VRAM Required | 10GB (GGUF Q4_K_M quantization) |
| Image Steps | 4 (with Lightning LoRA) |
| Video Steps | 8 (with LightX2V LoRA) |

---

## References

- `references/models.md` - Model specifications and sizes
- `references/prompt-engineering.md` - Detailed prompt writing guidance
- `references/troubleshooting.md` - Common issues and solutions
- `README.md` - Installation instructions
