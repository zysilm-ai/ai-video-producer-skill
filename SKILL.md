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
allowed-tools: Bash, Read, Write, Edit, Glob, AskUserQuestion
---

# AI Video Producer

Create professional AI-generated videos through a structured, iterative workflow.

## Workflow Overview

1. **Production Philosophy** - Define visual style, motion language, and narrative approach
2. **Scene Breakdown** - Decompose video into scenes with keyframe requirements
3. **Keyframe Generation** - Create start/end frames with visual consistency
4. **Video Synthesis** - Generate video segments using Veo API
5. **Review & Iterate** - Refine based on user feedback

## Phase 1: Production Philosophy

Before generating any assets, establish a **Production Philosophy** document. This ensures visual coherence across all scenes.

### Philosophy Template

Create a markdown file capturing these elements:

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

Save this as `outputs/philosophy.md` or include in style configuration JSON.

### Style Configuration (JSON)

For programmatic use, create a style config:

```json
{
  "project_name": "My Video Project",
  "visual_style": {
    "art_style": "cinematic realistic with subtle stylization",
    "color_palette": "warm earth tones with teal accents",
    "lighting": "golden hour, soft shadows",
    "composition": "wide establishing shots, intimate close-ups"
  },
  "motion_language": {
    "movement_quality": "smooth and fluid",
    "pacing": "contemplative with dynamic peaks",
    "camera_style": "slow tracking shots, occasional static frames"
  },
  "subject_consistency": {
    "main_subject": "description here",
    "environment": "description here"
  },
  "constraints": {
    "avoid": ["text overlays", "rapid cuts", "dutch angles"],
    "maintain": ["consistent lighting direction", "color grade"]
  }
}
```

Save to `outputs/style.json` for use with generation scripts.

## Phase 2: Scene Breakdown

Break the video into discrete scenes, identifying keyframe requirements.

### Scene Planning Template

```markdown
## Scene [N]: [Title]

**Duration**: [X seconds]
**Purpose**: [What this scene communicates]

**Keyframes Required**:
- Start frame: [description]
- End frame: [description] (if using dual-frame mode)

**Motion Description**:
[What happens during this scene]

**Audio Notes**:
[Music, sound effects, dialogue cues]

**Transition**:
[How this connects to next scene]
```

### Generation Strategy Selection

| Scenario | Strategy | Keyframes Needed |
|----------|----------|------------------|
| Continuous motion (running, flying) | Single-frame (start) | 1 |
| Ambient/atmospheric | Single-frame (end) | 1 |
| Precise action/transformation | Dual-frame | 2 |
| Long take (>8 seconds) | Multi-segment | 3+ |

For **long takes**, chain keyframes: A → B → C → D, generating A→B, B→C, C→D separately.

## Phase 3: Keyframe Generation

Generate keyframe images using Gemini API.

### Using the Generation Script

```bash
# Set API key first
export GOOGLE_API_KEY="your-key-here"

# Generate a keyframe
python {baseDir}/scripts/gemini_image.py \
  --prompt "A warrior standing in defensive stance, golden hour lighting, cinematic" \
  --style-ref outputs/style.json \
  --output outputs/scene-01/keyframe-start.png

# With reference images for consistency
python {baseDir}/scripts/gemini_image.py \
  --prompt "Same warrior now mid-attack, motion blur on sword" \
  --reference outputs/character-ref.png \
  --style-ref outputs/style.json \
  --output outputs/scene-01/keyframe-end.png
```

### Keyframe Quality Checklist

Before proceeding to video generation, verify:

- [ ] Subject appears correctly (no distortion)
- [ ] Style matches Production Philosophy
- [ ] Composition allows for intended motion
- [ ] All necessary visual information is present
- [ ] Lighting direction is consistent

**Critical**: If the subject will rotate significantly, ensure front-facing reference exists. Veo cannot hallucinate unseen angles accurately.

## Phase 4: Video Generation

Generate videos using Veo API with prepared keyframes.

### Generation Commands

**Single-frame mode** (continuous motion):
```bash
python {baseDir}/scripts/veo_video.py \
  --prompt "The warrior charges forward, cape flowing behind" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --style-ref outputs/style.json \
  --duration 8 \
  --output outputs/scene-01/video.mp4
```

**Dual-frame mode** (precise control):
```bash
python {baseDir}/scripts/veo_video.py \
  --prompt "Warrior swings sword in powerful arc, enemies react" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --end-frame outputs/scene-01/keyframe-end.png \
  --style-ref outputs/style.json \
  --output outputs/scene-01/video.mp4
```

**Text-to-video** (no keyframes):
```bash
python {baseDir}/scripts/veo_video.py \
  --prompt "Sweeping aerial shot of mountain landscape at dawn" \
  --duration 8 \
  --resolution 1080p \
  --output outputs/scene-01/video.mp4
```

### Check Generation Status

```bash
python {baseDir}/scripts/status_checker.py list
python {baseDir}/scripts/status_checker.py check [operation-name]
```

## Phase 5: Review & Iterate

After each generation, review with the user and refine as needed.

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Subject distortion on rotation | Missing front-facing reference | Add intermediate keyframe |
| Style drift between scenes | Inconsistent prompts | Reinforce style in each prompt |
| Unnatural motion | Vague motion description | Add specific motion constraints |
| Wrong subject position | Ambiguous spatial language | Use explicit directional terms |

### Iteration Workflow

1. Review generated video with user
2. Identify specific issues
3. Adjust keyframes OR prompts (not both simultaneously)
4. Regenerate
5. Repeat until satisfactory

## Prompt Engineering Guidelines

### Effective Motion Prompts

**Do:**
- Describe the action trajectory: "moves from left to right"
- Specify speed: "slowly raises hand" vs "quickly dodges"
- Include environmental interaction: "dust kicks up as they land"
- Add directional constraints: "character faces camera throughout"

**Don't:**
- Use ambiguous terms: "character does something cool"
- Assume implied actions: be explicit about every motion
- Contradict keyframe content
- Request impossible physics without indication

### Prompt Structure

```
[Subject description]. [Action/motion]. [Environmental details]. [Style reinforcement]. [Constraints].
```

Example:
```
A young woman in a blue dress stands at the edge of a cliff.
She slowly raises her arms as wind catches her hair.
Ocean waves crash against rocks below, sea spray visible.
Cinematic wide shot, golden hour lighting, film grain.
Character remains facing the ocean throughout, no rotation.
```

## Output Organization

Recommended directory structure:

```
outputs/
├── philosophy.md           # Production philosophy document
├── style.json             # Style configuration
├── scene-breakdown.md     # Full scene breakdown
├── scene-01/
│   ├── keyframe-start.png
│   ├── keyframe-end.png   # If using dual-frame
│   └── video.mp4
├── scene-02/
│   └── ...
└── final/
    └── assembly-notes.md  # Notes for final editing
```

## Video Types Reference

This workflow adapts to any video type:

- **Promotional**: Focus on product shots, benefit visualization
- **Educational**: Clear demonstrations, step-by-step sequences
- **Narrative**: Character consistency, emotional beats, story arc
- **Social Media**: Hook in first 2 seconds, vertical format (9:16)
- **Music Video**: Beat-synchronized transitions, visual rhythm
- **Product Demo**: Feature highlights, use-case scenarios
- **Game Trailer**: Action sequences, atmosphere, gameplay hints

Adjust Production Philosophy and Scene Breakdown to match the specific video type.

## Quick Reference

| Script | Purpose | Key Arguments |
|--------|---------|---------------|
| `gemini_image.py` | Generate keyframes | `--prompt`, `--output`, `--style-ref`, `--reference` |
| `veo_video.py` | Generate videos | `--prompt`, `--start-frame`, `--end-frame`, `--output` |
| `status_checker.py` | Monitor jobs | `list`, `check [name]` |

See `references/prompt-engineering.md` for detailed prompt writing guidance.
See `references/troubleshooting.md` for common issues and solutions.
