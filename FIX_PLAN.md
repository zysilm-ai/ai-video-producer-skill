# Fix Plan: Qwen Image Generation Issues

## Summary of Issues

| Issue | Root Cause | Solution |
|-------|------------|----------|
| 1. Oversaturation | CFG 4.0 + reference chaining on flow-matching model | Use `shift` parameter instead of CFG, set CFG to 1.0 |
| 2. No pose change | Missing `--pose` flag, no ControlNet activation | Use `--pose` flag with pose assets |
| 3. Layer composite not used | Direct scene generation, chaining previous keyframes | Implement 3-step layer workflow, smart reference strategy |

---

## Problem 1: Oversaturation Fix

### Current State

All three Qwen workflows use `cfg: 4.0` in KSampler:
- `qwen_t2i.json` - No ModelSamplingAuraFlow, CFG 4.0
- `qwen_edit.json` - No ModelSamplingAuraFlow, CFG 4.0
- `qwen_pose.json` - Has ModelSamplingAuraFlow (shift 1.73), but still CFG 4.0

### Why CFG Causes Saturation

Qwen Image Edit is a **flow-matching model**. When using CFG on flow-matching models:
> "The magnitude of the predicted noise could be higher than what it's supposed to be, causing color saturation."

The correct approach is to use the `shift` parameter via `ModelSamplingAuraFlow` node.

### Fix Details

#### 1.1 Update all workflows to add ModelSamplingAuraFlow

Add this node to `qwen_t2i.json` and `qwen_edit.json`:

```json
"NEW_NODE_ID": {
  "class_type": "ModelSamplingAuraFlow",
  "inputs": {
    "model": ["1", 0],
    "shift": 5.0
  },
  "_meta": {
    "title": "Model Sampling AuraFlow"
  }
}
```

#### 1.2 Update KSampler CFG values

Change in ALL workflows:
- `cfg`: 4.0 → **1.0**
- Connect model input from ModelSamplingAuraFlow output instead of direct UNETLoader

#### 1.3 Shift parameter recommendations

| Use Case | Shift Value | Notes |
|----------|-------------|-------|
| T2I (new generation) | 5.0-7.0 | Higher = more composition freedom |
| Edit (with reference) | 3.0-5.0 | Lower = more detail preservation |
| Pose-guided | 4.0-6.0 | Balance between pose control and quality |

#### 1.4 Update qwen_image.py

Add `--shift` parameter:
```python
parser.add_argument(
    "--shift",
    type=float,
    default=5.0,
    help="ModelSamplingAuraFlow shift (default: 5.0, range 3.0-8.0)"
)
```

Update `update_workflow_params()` to set shift value in ModelSamplingAuraFlow node.

---

## Problem 2: Pose Control Fix

### Current State

- Pose assets generated but never used
- `--pose` flag exists but wasn't invoked
- `qwen_pose.json` workflow exists and is functional

### Fix Details

#### 2.1 Generate ALL required pose assets

Currently only 2 poses exist. Need to generate:

| Pose | Description | Scene Usage |
|------|-------------|-------------|
| `fighting_stance.png` | ✅ Exists | Scene 1 start |
| `punch_throw.png` | ✅ Exists | Scene 1 end |
| `punch_connect.png` | ❌ Missing | Scene 2 start |
| `recovery.png` | ❌ Missing | Scene 2 end |

#### 2.2 Update SKILL.md workflow instructions

Emphasize that `--pose` flag is **REQUIRED** for character scenes:

```bash
# Character scene keyframe (CORRECT)
python qwen_image.py \
  --prompt "..." \
  --reference assets/characters/red_boxer.png \
  --pose assets/poses/fighting_stance.png \
  --control-strength 0.8 \
  --output scene-01/keyframe-start.png
```

#### 2.3 ControlNet strength guidelines

| Scenario | Strength | Reason |
|----------|----------|--------|
| Strict pose match | 0.9-1.0 | Exact pose replication |
| Flexible pose | 0.6-0.8 | Allow natural variation |
| Loose guidance | 0.3-0.5 | Hint at pose, prioritize prompt |

---

## Problem 3: Layer-Based Composite Workflow

### Current State

Current approach (WRONG):
```
Scene 1 start → Scene 1 end → Scene 2 start → Scene 2 end
       ↓              ↓              ↓
    (reference)   (reference)   (reference)
```

This chains references, compounding color drift with each generation.

### Correct Layer-Based Approach

```
For each keyframe:
┌─────────────────────────────────────────────────────────┐
│ Step 1: Generate/Reuse Background Layer                 │
│   - T2I for new background OR                           │
│   - Reference previous scene's background for continuity│
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ Step 2: Generate Character Layer                        │
│   - ALWAYS reference original asset (assets/characters/)│
│   - Use pose asset for ControlNet guidance              │
│   - Generate on transparent/neutral background          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ Step 3: Composite Layers                                │
│   - Combine background + character                      │
│   - Use multi-image TextEncodeQwenImageEditPlus         │
│   - Apply style reference                               │
└─────────────────────────────────────────────────────────┘
```

### Reference Strategy (Critical)

| Asset Type | Reference Source | Chain? |
|------------|------------------|--------|
| Character Identity | `assets/characters/*.png` | **NEVER** - always use original |
| Character Pose | `assets/poses/*.png` | **NEVER** - always use original |
| Background (same location) | Previous scene's `layers/background.png` | **YES** - for continuity |
| Background (new location) | `assets/backgrounds/*.png` | **NO** - use original asset |
| Style | `assets/styles/*.png` or `style.json` | **NEVER** - always use original |

### Why This Works

1. **Character consistency**: Always referencing the original character asset prevents identity drift
2. **Color stability**: Not chaining generated keyframes prevents saturation accumulation
3. **Pose control**: ControlNet ensures pose changes actually happen
4. **Scene continuity**: Background chaining is safe (no character, less complexity)

---

## Implementation Plan

### Phase 1: Workflow JSON Updates

#### Task 1.1: Update qwen_t2i.json
- [ ] Add ModelSamplingAuraFlow node (shift: 5.0)
- [ ] Update KSampler to use AuraFlow model output
- [ ] Set CFG to 1.0

#### Task 1.2: Update qwen_edit.json
- [ ] Add ModelSamplingAuraFlow node (shift: 4.0)
- [ ] Update KSampler to use AuraFlow model output
- [ ] Set CFG to 1.0

#### Task 1.3: Update qwen_pose.json
- [ ] Update existing ModelSamplingAuraFlow shift: 1.73 → 5.0
- [ ] Update KSampler CFG: 4.0 → 1.0

### Phase 2: Script Updates

#### Task 2.1: Update qwen_image.py
- [ ] Add `--shift` parameter (default 5.0)
- [ ] Add logic to update ModelSamplingAuraFlow shift value
- [ ] Update `update_workflow_params()` function

#### Task 2.2: Create new workflow: qwen_composite.json
- [ ] Multi-image TextEncodeQwenImageEditPlus (image1=background, image2=character)
- [ ] ModelSamplingAuraFlow with shift
- [ ] CFG 1.0
- [ ] Purpose: Final layer compositing

### Phase 3: SKILL.md Workflow Update

#### Task 3.1: Update Phase 3 (Keyframe Generation)
- [ ] Document 3-step layer workflow clearly
- [ ] Add reference strategy rules
- [ ] Update command examples with `--pose` and `--shift`

#### Task 3.2: Add reference strategy section
- [ ] Document what to reference for each asset type
- [ ] Explain why chaining keyframes causes issues
- [ ] Provide decision flowchart

### Phase 4: Regenerate Boxing Video

#### Task 4.1: Generate missing pose assets
- [ ] `punch_connect.png`
- [ ] `recovery.png`

#### Task 4.2: Regenerate Scene 1 with correct workflow
- [ ] Background layer (T2I with shift)
- [ ] Character layer (pose + character reference)
- [ ] Composite

#### Task 4.3: Regenerate Scene 2 with correct workflow
- [ ] Background layer (reference Scene 1 background)
- [ ] Character layer (original character asset + new pose)
- [ ] Composite

---

## New Workflow Files Needed

### qwen_composite.json (NEW)

Purpose: Combine background + character into final keyframe

```json
{
  "TextEncodeQwenImageEditPlus": {
    "inputs": {
      "image1": "{{BACKGROUND}}",
      "image2": "{{CHARACTER}}",
      "prompt": "{{PROMPT}}"
    }
  },
  "ModelSamplingAuraFlow": {
    "inputs": {
      "shift": 4.0
    }
  },
  "KSampler": {
    "inputs": {
      "cfg": 1.0,
      "steps": 20
    }
  }
}
```

---

## Verification Checklist

After implementing fixes, verify:

- [ ] T2I generation produces non-saturated colors
- [ ] Edit workflow with reference maintains color fidelity
- [ ] Pose workflow actually changes character pose
- [ ] Chained backgrounds maintain consistency without color drift
- [ ] Scene 2 keyframe-end shows visible difference from keyframe-start
- [ ] Overall video has consistent character identity across all scenes

---

## Sources

- [ModelSamplingAuraFlow Documentation](https://www.runcomfy.com/comfyui-nodes/ComfyUI/ModelSamplingAuraFlow)
- [MyAIForce - Fixing Image Drift](https://myaiforce.com/qwen-image-edit-2511-relighting/)
- [Qwen Image Edit FAQ](https://qwen-image-edit.app/blog/qwen-image-edit-faqs)
- [Multi-Image Qwen Workflow](https://www.nextdiffusion.ai/tutorials/consistent-outfit-changes-with-multi-qwen-image-edit-2511-in-comfyui)
- [ComfyUI-QwenEditUtils](https://github.com/lrzjason/Comfyui-QwenEditUtils)
- [ComfyUI-PainterLongVideo](https://github.com/princepainter/ComfyUI-PainterLongVideo)
