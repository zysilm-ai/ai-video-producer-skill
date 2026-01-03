# Boxing Video Generation Session

**Date:** 2026-01-02
**Status:** Paused at keyframe generation
**Output Directory:** `D:\comfyui\output\boxing-video\`

---

## Session Summary

Attempted to invoke the AI Video Producer skill to generate a boxing video. Completed phases 1-2.5, encountered issues at phase 3 (keyframe generation).

---

## Completed Steps

### 1. ComfyUI Setup
- ComfyUI started successfully
- All models verified: WAN 2.2, Qwen Image Edit 2511, ControlNet Union

### 2. Phase 1: Production Philosophy (COMPLETED)
Created files:
- `philosophy.md` - Visual identity, motion language, subject consistency
- `style.json` - Programmatic style configuration

**Style:** Cinematic realistic sports documentary, dramatic spotlight lighting, red/blue boxing colors

### 3. Phase 2: Scene Breakdown (COMPLETED)
Created `scene-breakdown.md`:
- **Total Duration:** 10 seconds (2 scenes x 5 seconds)
- **Scene 1:** "The Opening Strike" - Red boxer throws right hook
- **Scene 2:** "The Counter" - Blue boxer defends and counters with jab
- **Keyframes:** KF-A, KF-B (shared), KF-C

### 4. Phase 2.5: Asset Generation (COMPLETED)
Created `assets.json` and generated 7 asset images:

| Asset | Path |
|-------|------|
| Boxing ring background | `assets/backgrounds/boxing_ring.png` |
| Red boxer character | `assets/characters/red_boxer.png` |
| Blue boxer character | `assets/characters/blue_boxer.png` |
| Fighting stance pose | `assets/poses/fighting_stance.png` |
| Punch throw pose | `assets/poses/punch_throw.png` |
| Counter punch pose | `assets/poses/counter_punch.png` |
| Sports cinematic style | `assets/styles/sports_cinematic.png` |

---

## Where We Stopped: Phase 3 Keyframe Generation

### Issue Encountered
Attempted to generate KF-A with a single reference image:

```bash
python qwen_image.py \
  --prompt "Athletic male boxer in red gloves..." \
  --output "...\keyframes\KF-A.png" \
  --reference "...\assets\backgrounds\boxing_ring.png" \
  --preset medium
```

**Result:** Timed out after 600 seconds (VAE decode step hung)

### Root Cause Discovery
Researched Qwen Image Edit 2511 capabilities and found:

1. **Model supports up to 3 reference images** for multi-image compositing
2. **Current `qwen_image.py` only implements:**
   - 1 reference image (`--reference`)
   - 1 pose image (`--pose`)
3. **SKILL.md describes a 3-step composite workflow that isn't implemented in the script**

The "layered generation" approach (background → character → composite) requires script modifications to support multiple reference images.

---

## Next Steps When Resuming

### Option A: Simple Approach (T2I only)
Generate keyframes without references - faster but no consistency guarantee:
```bash
python qwen_image.py --prompt "..." --output "..." --preset medium
```

### Option B: Single Reference
Use one reference per generation - partial consistency:
```bash
python qwen_image.py --prompt "..." --reference <one_asset> --output "..."
```

### Option C: Update Script (Recommended)
Modify `qwen_image.py` to support multiple `--reference` arguments for proper multi-image compositing as the Qwen model supports.

---

## Files Created This Session

```
D:\comfyui\output\boxing-video\
├── philosophy.md              ✓
├── style.json                 ✓
├── scene-breakdown.md         ✓
├── assets.json                ✓
├── assets/
│   ├── backgrounds/
│   │   └── boxing_ring.png    ✓
│   ├── characters/
│   │   ├── red_boxer.png      ✓
│   │   └── blue_boxer.png     ✓
│   ├── poses/
│   │   ├── fighting_stance.png ✓
│   │   ├── punch_throw.png    ✓
│   │   └── counter_punch.png  ✓
│   └── styles/
│       └── sports_cinematic.png ✓
├── keyframes/                 (empty - not generated yet)
├── scene-01/                  (empty)
└── scene-02/                  (empty)
```

---

## Research References

- [Qwen Image Edit 2511 ComfyUI Tutorial](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511)
- [Qwen Image Edit 2511 Blog](https://blog.comfy.org/p/qwen-image-edit-2511-and-qwen-image)
- [Multi-Reference Outfit Changes Tutorial](https://www.nextdiffusion.ai/tutorials/consistent-outfit-changes-with-multi-qwen-image-edit-2511-in-comfyui)

---

## To Resume

1. Start ComfyUI: `cd D:\comfyui && python main.py --listen 0.0.0.0 --port 8188`
2. Decide on approach (A, B, or C above)
3. Generate keyframes KF-A, KF-B, KF-C
4. Generate videos for Scene 1 and Scene 2
5. Review final output
