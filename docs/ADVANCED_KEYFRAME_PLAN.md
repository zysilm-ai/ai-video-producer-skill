# Advanced Keyframe Generation: Implementation Plan

## Overview

This document outlines the plan to integrate advanced consistency features into the AI Video Producer skill, enabling layer-based keyframe generation with:

1. **AnyPose LoRA** - Character pose transfer
2. **InStyle LoRA** - Style consistency
3. **Multi-Layer Composite** - Separate character/background generation
4. **Asset Library** - Reusable assets across scenes

---

## Design Decisions Summary

### Area 1: Asset Library

| Decision | Choice |
|----------|--------|
| Asset Types | Full set: characters, poses, backgrounds, styles, objects |
| Storage | Separate `assets.json` file |
| Generation Phase | New Phase 2.5 (after Scene Breakdown) |
| Planning | Analyze scenes to identify needed assets |

### Area 2: Scene Breakdown Format

| Decision | Choice |
|----------|--------|
| Asset references | By name only (e.g., `character: samurai`) |
| Pose specification | Reference from assets.json (e.g., `pose: meditation`) |
| Generation mode | Auto-detect from inputs |
| Scene type | Explicit field (`type: character` or `type: landscape`) |

### Area 3: Generation Flow

| Decision | Choice |
|----------|--------|
| Composite mode | Always for character scenes |
| Character identity | Always use original identity asset (no chaining) |
| Background handling | Chain from previous scene's background |
| InStyle LoRA | Always apply with style asset reference |
| Compositing method | Qwen multi-image (native blending) |

### Area 4: Directory Structure

| Decision | Choice |
|----------|--------|
| Intermediate layers | Keep in `layers/` subfolder |
| Assets organization | By type (`assets/characters/`, `assets/backgrounds/`, etc.) |

---

## New Workflow Phases

```
Phase 1:   Production Philosophy  → philosophy.md, style.json
Phase 2:   Scene Breakdown        → scene-breakdown.md
Phase 2.5: Asset Generation (NEW) → assets.json, assets/ folder
Phase 3:   Keyframe Generation    → scene-XX/keyframe-*.png
Phase 4:   Video Synthesis        → scene-XX/video.mp4
Phase 5:   Review & Iterate
```

---

## File Formats

### assets.json

```json
{
  "characters": {
    "samurai": {
      "description": "Feudal Japanese warrior, red armor, stern expression",
      "identity_ref": "assets/characters/samurai.png"
    },
    "ninja": {
      "description": "Shadow warrior, black outfit, agile build",
      "identity_ref": "assets/characters/ninja.png"
    }
  },
  "backgrounds": {
    "temple_courtyard": {
      "description": "Ancient temple with cherry blossoms, stone paths",
      "ref_image": "assets/backgrounds/temple_courtyard.png"
    },
    "mountain_sunset": {
      "description": "Mountain range at golden hour, dramatic clouds",
      "ref_image": "assets/backgrounds/mountain_sunset.png"
    }
  },
  "poses": {
    "standing": {
      "description": "Upright neutral stance",
      "ref_image": "assets/poses/standing.png"
    },
    "meditation": {
      "description": "Seated cross-legged, hands on knees",
      "ref_image": "assets/poses/meditation.png"
    },
    "fighting": {
      "description": "Combat stance, weapon raised",
      "ref_image": "assets/poses/fighting.png"
    }
  },
  "styles": {
    "ghibli": {
      "description": "Studio Ghibli anime aesthetic",
      "ref_image": "assets/styles/ghibli.png"
    },
    "realistic": {
      "description": "Photorealistic cinematic look",
      "ref_image": "assets/styles/realistic.png"
    }
  },
  "objects": {
    "katana": {
      "description": "Traditional Japanese sword",
      "ref_image": "assets/objects/katana.png"
    }
  }
}
```

### scene-breakdown.md (Updated Format)

```markdown
# Scene Breakdown: [Project Name]

## Overview
- **Total Duration**: 15 seconds
- **Number of Scenes**: 3
- **Video Type**: narrative

---

## Scene 1: Temple Meditation

**Type**: character
**Duration**: 5 seconds
**Characters**: samurai
**Background**: temple_courtyard
**Style**: ghibli

**Start Frame**:
- pose: standing
- expression: calm, contemplative

**End Frame**:
- pose: meditation
- expression: peaceful, eyes closed

**Motion**: Samurai slowly sits down into meditation pose

**Camera**: static, wide shot

---

## Scene 2: Sunset Transition

**Type**: landscape
**Duration**: 5 seconds
**Background**: mountain_sunset
**Style**: ghibli

**Start Frame**: Sun above mountains, warm light
**End Frame**: Sun touching horizon, golden hour

**Motion**: Slow pan right, sun descending

**Camera**: tracking right

---

## Scene 3: Eyes Open

**Type**: character
**Duration**: 5 seconds
**Characters**: samurai
**Background**: temple_courtyard
**Style**: ghibli

**Start Frame**:
- pose: meditation
- expression: eyes closed

**End Frame**:
- pose: meditation
- expression: eyes open, alert

**Motion**: Subtle - only eyes open, slight head movement

**Camera**: close-up on face
```

---

## Directory Structure

```
{output_dir}/
├── philosophy.md              # Production philosophy
├── style.json                 # Style configuration
├── assets.json                # Asset definitions (NEW)
├── scene-breakdown.md         # Scene breakdown
│
├── assets/                    # Reusable assets (NEW)
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
│   ├── layers/                # Intermediate outputs (NEW)
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
└── scene-03/
    ├── layers/
    │   ├── background.png
    │   └── character.png
    ├── keyframe-start.png
    ├── keyframe-end.png
    └── video.mp4
```

---

## Generation Flow

### Character Scene (type: character)

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Generate Background Layer                               │
│                                                                 │
│ Input:                                                          │
│   - Background asset from assets.json                           │
│   - OR previous scene's background (for chaining)               │
│   - Style reference + InStyle LoRA                              │
│                                                                 │
│ Output: scene-XX/layers/background.png                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Generate Character Layer                                │
│                                                                 │
│ Input:                                                          │
│   - Character identity asset (always original, no chain)        │
│   - Pose reference from assets.json                             │
│   - Style reference + InStyle LoRA                              │
│   - AnyPose LoRA for pose transfer                              │
│                                                                 │
│ Output: scene-XX/layers/character.png                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Composite Layers                                        │
│                                                                 │
│ Input:                                                          │
│   - scene-XX/layers/background.png                              │
│   - scene-XX/layers/character.png                               │
│                                                                 │
│ Method: Qwen multi-image blending                               │
│ Prompt: "Place character naturally in background scene"         │
│                                                                 │
│ Output: scene-XX/keyframe-start.png                             │
└─────────────────────────────────────────────────────────────────┘
```

### Landscape Scene (type: landscape)

```
┌─────────────────────────────────────────────────────────────────┐
│ Single Step: Generate Background                                │
│                                                                 │
│ Input:                                                          │
│   - Background asset OR previous scene's background             │
│   - Style reference + InStyle LoRA                              │
│   - Scene description for modifications                         │
│                                                                 │
│ Output: scene-XX/keyframe-start.png                             │
│         (also saved to layers/background.png for reference)     │
└─────────────────────────────────────────────────────────────────┘
```

### Reference Chain Rules

| Asset Type | Chain Behavior |
|------------|----------------|
| **Character Identity** | Never chain - always use original asset |
| **Character Pose** | Reference from assets.json per keyframe |
| **Background** | Chain from previous scene for continuity |
| **Style** | Always apply InStyle with style asset |

---

## LoRA Configuration

### Required LoRAs

| LoRA | Source | Strength | Purpose |
|------|--------|----------|---------|
| Lightning 4-step | Comfy-Org | 1.0 | Fast generation (6 steps) |
| AnyPose | lilylilith/AnyPose | 0.7 | Pose transfer |
| AnyPose_helper | lilylilith/AnyPose | 0.7 | Pose helper |
| InStyle | peteromallet/Qwen-Image-Edit-InStyle | 0.5 | Style consistency |

### LoRA Stacking Order

```
1. Lightning 4-step (base acceleration)
2. AnyPose + AnyPose_helper (if pose transfer needed)
3. InStyle (always, for style consistency)
```

### Adjusted Strengths for Stacking

When combining AnyPose + InStyle:
- AnyPose: 0.5-0.6 (reduced from 0.7)
- AnyPose_helper: 0.5-0.6
- InStyle: 0.4-0.5 (reduced from 0.5)

---

## Script Updates Required

### qwen_image.py Changes

```python
# New arguments
--mode [auto|t2i|edit|anypose|composite|landscape]
--character <asset_name>      # Character from assets.json
--background <asset_name>     # Background from assets.json
--pose <asset_name>           # Pose from assets.json
--style <asset_name>          # Style from assets.json
--assets-file <path>          # Path to assets.json

# Mode auto-detection logic
def detect_mode(scene_type, has_character, has_pose_change):
    if scene_type == "landscape":
        return "landscape"
    elif scene_type == "character":
        return "composite"  # Always composite for character scenes
    else:
        return "edit"  # Fallback
```

### New Script: generate_keyframe.py

High-level orchestrator that:
1. Reads scene from scene-breakdown.md
2. Loads assets from assets.json
3. Runs the 3-step composite flow
4. Handles both character and landscape scenes

```bash
python scripts/generate_keyframe.py \
  --scene 1 \
  --keyframe start \
  --assets-file outputs/project/assets.json \
  --scene-breakdown outputs/project/scene-breakdown.md \
  --output-dir outputs/project/scene-01/
```

---

## Workflow Updates Required

### New Workflows

| Workflow | Purpose |
|----------|---------|
| `qwen_anypose.json` | Character with pose transfer |
| `qwen_instyle.json` | Style-consistent generation |
| `qwen_background.json` | Background-only generation |
| `qwen_composite.json` | Multi-image compositing |

### Workflow Selection Matrix

| Scene Type | Has Pose Change | Workflow Sequence |
|------------|-----------------|-------------------|
| character | yes | background → anypose+instyle → composite |
| character | no | background → instyle → composite |
| landscape | - | background+instyle only |
| object | - | instyle only |

---

## SKILL.md Updates Required

### Phase Changes

1. **Add Phase 2.5: Asset Generation**
   - Analyze scene-breakdown.md for required assets
   - Generate or collect character/background/pose/style references
   - Create assets.json with all definitions
   - User approval checkpoint

2. **Update Phase 3: Keyframe Generation**
   - New generation flow for character scenes (3-step composite)
   - Simplified flow for landscape scenes
   - Layer-based output structure

3. **Update directory structure documentation**

4. **Update scene-breakdown.md format**
   - Add `type:` field
   - Add asset references by name
   - Add pose references

---

## Implementation Checklist

### Setup & Downloads
- [ ] Add LoRA downloads to setup_comfyui.py
- [ ] Install ComfyUI-QwenImageLoraLoader custom node
- [ ] Test LoRA loading and stacking

### Workflows
- [ ] Create qwen_anypose.json
- [ ] Create qwen_instyle.json
- [ ] Create qwen_background.json
- [ ] Create qwen_composite.json
- [ ] Test each workflow individually
- [ ] Test LoRA stacking combinations

### Scripts
- [ ] Update qwen_image.py with new arguments
- [ ] Add asset loading from assets.json
- [ ] Implement mode auto-detection
- [ ] Create generate_keyframe.py orchestrator
- [ ] Add layer management (save to layers/ folder)

### SKILL.md
- [ ] Add Phase 2.5 documentation
- [ ] Update Phase 3 with new flow
- [ ] Update scene-breakdown.md format
- [ ] Update directory structure
- [ ] Update assets.json format documentation

### Testing
- [ ] Test full workflow with sample project
- [ ] Test character scene generation
- [ ] Test landscape scene generation
- [ ] Test multi-scene consistency
- [ ] Benchmark performance

---

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Asset types to support | Full set: characters, poses, backgrounds, styles, objects |
| Where to store asset definitions | Separate assets.json |
| When to generate assets | Phase 2.5 after scene breakdown |
| How to reference assets | By name only (lookup in assets.json) |
| How to specify poses | Reference from assets.json |
| Generation mode selection | Auto-detect from inputs |
| Scene type handling | Explicit field in scene-breakdown.md |
| Composite mode usage | Always for character scenes |
| Character identity chaining | Never - always use original asset |
| Background chaining | Yes - chain for continuity |
| InStyle LoRA application | Always with style reference |
| Compositing method | Qwen multi-image blending |
| Intermediate layers | Keep in layers/ subfolder |
| Asset folder organization | By type (characters/, backgrounds/, etc.) |
