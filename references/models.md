# Models Required (ComfyUI + GGUF)

This document lists all models required for the AI Video Production skill.

## Video Generation (WAN 2.1 - Default)

| Model | Size | Purpose |
|-------|------|---------|
| WAN 2.1 I2V Q4_K_M GGUF | ~11GB | Video generation |
| LightX2V LoRA | ~0.7GB | Fast 8-step generation |
| UMT5-XXL FP8 | ~5GB | Text encoder |
| WAN VAE | ~0.2GB | Video decoding |

## Video Generation (WAN 2.2 MoE - for --moe/--moe-fast)

| Model | Size | Purpose |
|-------|------|---------|
| WAN 2.2 I2V HighNoise Q6_K GGUF | ~12GB | MoE high-noise expert |
| WAN 2.2 I2V LowNoise Q6_K GGUF | ~12GB | MoE low-noise expert |

To download WAN 2.2 models: `python scripts/setup_comfyui.py --q6k`

## Keyframe Generation (Qwen Image Edit 2511)

| Model | Size | Purpose |
|-------|------|---------|
| Qwen Image Edit Q4_K_M GGUF | ~13GB | Image generation |
| Lightning LoRA | ~0.8GB | Fast 4-step generation |
| Qwen VL 7B FP8 | ~8GB | Text encoder |
| Qwen VAE | ~0.2GB | Image decoding (tiled) |

## Storage Location

Models are stored in `{baseDir}/comfyui/models/` directory.

See `README.md` for installation instructions.
