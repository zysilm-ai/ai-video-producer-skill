---
name: ai-video-producer
description: >
  AI video production using WAN 2.1 and Qwen Image Edit via ComfyUI.
  Creates any video type: promotional, narrative, educational, animations, etc.
  Follows philosophy-first approach with scene-by-scene execution.
  Runs locally on RTX 3080+ (10GB+ VRAM).
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion, TodoWrite
---

# AI Video Producer

## Setup

```bash
python {baseDir}/scripts/setup_comfyui.py         # Full setup (first time)
python {baseDir}/scripts/setup_comfyui.py --check # Verify
python {baseDir}/scripts/setup_comfyui.py --start # Start server
```

**Requirements:** 10GB VRAM, 16GB RAM, 40GB storage

## Mandatory Rules

1. **Use TodoWrite** at start to track workflow
2. **Ask Approval Mode** first (Manual or Automatic)
3. **Never skip phases** - complete in order
4. **Create all required files** before generation
5. **Use execute_pipeline.py** for all generation

## Workflow Overview

| Phase | Output | Approval |
|-------|--------|----------|
| 1. Philosophy | `philosophy.md`, `style.json` | Checkpoint |
| 2. Scene Breakdown | `scene-breakdown.md` | Checkpoint |
| 3. Pipeline | `pipeline.json` | Checkpoint |
| 4. Assets | `assets/` | VLM review |
| 5. Keyframes | `keyframes/` | VLM review |
| 6. Videos | `scene-*/`, `final/` | Final review |

**Approval Modes:**
- **Manual**: User approves each phase
- **Automatic**: LLM proceeds, user reviews final only

---

## Phase 1: Production Philosophy

Create `philosophy.md`:
```markdown
# Production Philosophy: [Project Name]

## Visual Identity
- **Art Style**: [cinematic/animated/stylized]
- **Color Palette**: [colors, mood, temperature]
- **Lighting**: [natural/dramatic/soft]

## Motion Language
- **Movement**: [smooth/dynamic/subtle]
- **Pacing**: [fast/slow/rhythmic]
- **Camera**: [static/tracking/handheld]

## Constraints
- **Avoid**: [unwanted elements]
- **Maintain**: [consistency requirements]
```

Create `style.json` with same info in JSON format.

---

## Phase 2: Scene Breakdown

**See `examples/` folder for complete examples.**

Create `scene-breakdown.md`:
```markdown
# Scene Breakdown: [Project Name]

## Overview
- **Duration**: [X seconds]
- **Scenes**: [N]
- **Genre**: [action/horror/drama/comedy/anime/fantasy/commercial]

## Scene Overview
| Scene | Description | Shot | Transition | Duration |
|-------|-------------|------|------------|----------|
| 1 | [description] | [ELS/LS/MS/CU/ECU] | - | 5s |
| 2 | [description] | [shot] | cut | 5s |

## Scenes

### Scene 1: [Title]
**Type**: character | landscape
**Duration**: [3-8]s
**Shot**: [ELS/LS/MLS/MS/MCU/CU/ECU] + [static/tracking/pan]
**Purpose**: [setup/action/reaction/transition]

**Keyframe**: Generated | Extracted
- Characters: [IDs]
- Background: [ID]

**Segments**:
| ID | Motion | Duration | Beat |
|----|--------|----------|------|
| seg-1a | [motion description] | 5s | action |

**Transition**: cut | continuous | fade | dissolve
```

### Shot Types
| Shot | Frame | Use |
|------|-------|-----|
| ELS | Environment dominant | Establishing |
| LS | Full body | Character in space |
| MS | Waist up | Action, dialogue |
| CU | Face | Emotion |
| ECU | Single feature | Intensity |

### Segment Duration
- **3-4s**: Quick action, impacts
- **5s**: Standard (default)
- **6-8s**: Establishing, emotional moments

### Transitions
- **cut**: Camera change (generated keyframe)
- **continuous**: Same shot continues (extracted keyframe for landscape ONLY)
- **fade/dissolve**: Time skip, dramatic (generated keyframe)

**CRITICAL**: Character scenes MUST use generated keyframes with character references. Extracted keyframes cause identity drift.

---

## Phase 3: Pipeline Generation

Create `pipeline.json` with ALL prompts defined before any generation:

```json
{
  "version": "3.0",
  "project_name": "project-name",
  "assets": {
    "characters": {
      "hero": {
        "prompt": "Character description, A-pose, full body, white background",
        "output": "assets/characters/hero.png",
        "status": "pending"
      }
    },
    "backgrounds": {
      "location": {
        "prompt": "Environment description, no people",
        "output": "assets/backgrounds/location.png",
        "status": "pending"
      }
    }
  },
  "scenes": [
    {
      "id": "scene-01",
      "description": "Scene description",
      "shot_type": "MS",
      "transition_from_previous": null,
      "first_keyframe": {
        "type": "generated",
        "prompt": "Keyframe description with character and background",
        "characters": ["hero"],
        "background": "location",
        "output": "keyframes/scene-01-start.png",
        "status": "pending"
      },
      "segments": [
        {
          "id": "seg-01a",
          "motion_prompt": "Motion description with physical details",
          "duration": 5,
          "output_video": "scene-01/seg-a.mp4",
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

---

## Phase 4-6: Execution

Run stages with `execute_pipeline.py`:

```bash
# Assets (characters, backgrounds)
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --stage assets

# Keyframes
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --stage keyframes

# Videos (generates and merges)
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --stage videos

# Or run all
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --all
```

**Regeneration:**
```bash
python {baseDir}/scripts/execute_pipeline.py {output_dir}/pipeline.json --regenerate <id>
```

---

## Motion Prompt Guidelines

Structure: `[Subject] [Action] [Environment interaction], camera [movement]`

**Good**: "Soldier sprints through trench, legs driving forward, mud splashing from boots, camera tracking from behind"

**Bad**: "Soldier runs" (too vague, no physical detail)

**Key principles:**
- Describe physical body mechanics
- Include environmental interaction
- Specify camera movement separately
- Use active verbs: sprints, lunges, crashes, drifts

See `references/prompt-engineering.md` for genre-specific guidance.

---

## Genre Templates

| Genre | Pacing | Key Techniques |
|-------|--------|----------------|
| Action | 3-5s variable | Wide→close→wide, tracking, smash cuts |
| Horror | 6-8s slow | Dutch angles, negative space, low-key light |
| Drama | 5s standard | Two-shots, slow push-ins, reaction holds |
| Comedy | 3-5s quick | Wide for physical, static camera |
| Anime | Variable | Speed lines, impact frames, dramatic poses |
| Fantasy | 6-8s epic | Sweeping cameras, low heroic angles |
| Commercial | 3-5s fast | Hero shots, 360 orbits, clean lighting |

See `references/genre-templates.md` for full details.

---

## Output Structure

```
{output_dir}/
├── philosophy.md
├── style.json
├── scene-breakdown.md
├── pipeline.json
├── assets/
│   ├── characters/
│   └── backgrounds/
├── keyframes/
├── scene-01/
│   └── merged.mp4
└── final/
    └── video.mp4
```

---

## Quick Reference

| Script | Purpose |
|--------|---------|
| `execute_pipeline.py` | Run pipeline stages |
| `setup_comfyui.py` | Setup/start ComfyUI |

| Stage | Command |
|-------|---------|
| Assets | `--stage assets` |
| Keyframes | `--stage keyframes` |
| Videos | `--stage videos` |
| All | `--all` |
| Regenerate | `--regenerate <id>` |

**Video Specs:** 5s per segment, 81 frames, 16fps, up to 832x480

---

## References

- `references/genre-templates.md` - Full cinematography guides
- `references/prompt-engineering.md` - Prompt writing (includes genre-specific)
- `references/models.md` - Model specifications
- `examples/` - Complete scene breakdown examples
