---
name: ai-video-producer
description: >
  Complete AI video production workflow using Google Gemini and Veo APIs.
  Creates any video type: promotional, educational, narrative, social media,
  animations, game trailers, music videos, product demos, and more. Use when
  users want to create videos with AI, need help with video storyboarding,
  keyframe generation, or video prompt writing. Follows a philosophy-first
  approach: establish visual style and production philosophy, then execute
  scene by scene with user feedback at each stage.
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion, TodoWrite
---

# AI Video Producer

Create professional AI-generated videos through a structured, iterative workflow.

## MANDATORY WORKFLOW REQUIREMENTS

**YOU MUST FOLLOW THESE RULES:**

1. **ALWAYS use TodoWrite** at the start to create a task list for the entire workflow
2. **NEVER skip phases** - complete each phase in order before proceeding
3. **ALWAYS create required files** - philosophy.md, style.json, and scene-breakdown.md are REQUIRED
4. **ALWAYS break videos into multiple scenes** - minimum 2 scenes for any video over 8 seconds
5. **ALWAYS ask user for approval** before proceeding to the next phase
6. **NEVER generate video without scene breakdown** - plan first, execute second

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

**STOP and ask the user:**
> "I've created the production philosophy. Please review `philosophy.md` and `style.json`. Should I proceed to scene breakdown, or would you like any changes?"

---

## Phase 2: Scene Breakdown (REQUIRED)

**DO NOT PROCEED TO PHASE 3 UNTIL `scene-breakdown.md` EXISTS AND USER APPROVES**

### Step 2.1: Analyze Video Requirements

Before creating scenes, determine:
- Total video duration needed
- Number of scenes required (minimum 2 for videos > 8 seconds)
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

**Duration**: [X seconds]
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
| 1 | [single/dual/text-only] | [1-2] | [any special notes] |
| 2 | [single/dual/text-only] | [1-2] | [any special notes] |
```

### Scene Count Guidelines

| Total Video Length | Minimum Scenes | Recommended Scenes |
|--------------------|----------------|-------------------|
| 1-8 seconds | 1 | 1-2 |
| 9-16 seconds | 2 | 2-3 |
| 17-24 seconds | 3 | 3-4 |
| 25-40 seconds | 4 | 4-5 |
| 40+ seconds | 5+ | Break into logical story beats |

### Step 2.3: CHECKPOINT - Get User Approval

**STOP and ask the user:**
> "I've created the scene breakdown with [N] scenes. Please review `scene-breakdown.md`. Should I proceed to generate keyframes, or would you like to adjust the scenes?"

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
export GOOGLE_API_KEY="your-key-here"

# Scene 1: Start keyframe - establishes visual style
python {baseDir}/scripts/gemini_image.py \
  --prompt "[Detailed prompt from scene-breakdown.md]" \
  --style-ref {output_dir}/style.json \
  --output {output_dir}/scene-01/keyframe-start.png
```

**Scene 1 - End keyframe (MUST reference start):**
```bash
# Scene 1: End keyframe - MUST reference start for consistency
python {baseDir}/scripts/gemini_image.py \
  --prompt "[Detailed prompt - same characters in new pose/state]" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/scene-01/keyframe-start.png \
  --output {output_dir}/scene-01/keyframe-end.png
```

**Scene 2+ - Start keyframe (MUST reference previous scene):**
```bash
# Scene 2: Start keyframe - MUST reference Scene 1's end keyframe
python {baseDir}/scripts/gemini_image.py \
  --prompt "[Detailed prompt for scene 2 start]" \
  --style-ref {output_dir}/style.json \
  --reference {output_dir}/scene-01/keyframe-end.png \
  --output {output_dir}/scene-02/keyframe-start.png
```

**Multiple references for complex consistency:**
```bash
# You can pass multiple --reference flags for better consistency
python {baseDir}/scripts/gemini_image.py \
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
- [ ] **Characters are consistent with reference keyframes**
- [ ] **Background/environment is consistent with reference keyframes**
- [ ] Lighting direction is consistent

**If consistency check fails**: Regenerate the keyframe with the same reference images. Do NOT proceed with inconsistent keyframes.

### Step 3.4: CHECKPOINT - Show User Each Keyframe

**After generating keyframes for a scene, STOP and inform the user:**
> "Generated keyframes for Scene [N]. The files are at:
> - `scene-XX/keyframe-start.png`
> - `scene-XX/keyframe-end.png` (if applicable)
>
> Please review. Should I proceed to generate the video for this scene?"

---

## Phase 4: Video Synthesis

**Generate video for EACH scene according to the scene breakdown.**

### Step 4.1: Generate Video Per Scene

**Single-frame mode:**
```bash
python {baseDir}/scripts/veo_video.py \
  --prompt "[Motion description from scene-breakdown.md]" \
  --start-frame {output_dir}/scene-01/keyframe-start.png \
  --style-ref {output_dir}/style.json \
  --duration [duration from scene-breakdown] \
  --output {output_dir}/scene-01/video.mp4
```

**Dual-frame mode:**
```bash
python {baseDir}/scripts/veo_video.py \
  --prompt "[Motion description from scene-breakdown.md]" \
  --start-frame {output_dir}/scene-01/keyframe-start.png \
  --end-frame {output_dir}/scene-01/keyframe-end.png \
  --style-ref {output_dir}/style.json \
  --duration [duration from scene-breakdown] \
  --output {output_dir}/scene-01/video.mp4
```

### Step 4.2: CHECKPOINT - Show User Each Video

**After each video generation, inform the user:**
> "Generated video for Scene [N]: `scene-XX/video.mp4`
> Duration: [X seconds]
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
1. Create philosophy.md
2. Create style.json
3. Get user approval on production philosophy
4. Create scene-breakdown.md
5. Get user approval on scene breakdown
6. Generate Scene 1 keyframes
7. Get user approval on Scene 1 keyframes
8. Generate Scene 1 video
9. [Repeat 6-8 for each scene]
10. Provide final summary to user
```

---

## Quick Reference

| Script | Purpose | Key Arguments |
|--------|---------|---------------|
| `gemini_image.py` | Generate keyframes | `--prompt`, `--output`, `--style-ref`, `--reference` |
| `veo_video.py` | Generate videos | `--prompt`, `--start-frame`, `--end-frame`, `--output` |
| `status_checker.py` | Monitor jobs | `list`, `check [name]` |

See `references/prompt-engineering.md` for detailed prompt writing guidance.
See `references/troubleshooting.md` for common issues and solutions.
