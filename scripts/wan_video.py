#!/usr/bin/env python3
"""
Generate videos using WAN 2.2 via HuggingFace diffusers.
Supports single-frame (I2V) and dual-frame (FLF2V) generation modes.
Uses LightX2V distillation LoRA for fast 8-step generation.

This script follows the ComfyUI approach of loading standalone model files:
- GGUF transformer (quantized, ~9GB for Q4_K_M)
- FP8 text encoder (~4.9GB)
- Standalone VAE (~0.2GB)
- LightX2V LoRA (~0.7GB)

Total: ~15GB vs 28GB+ for full HuggingFace model
"""

import argparse
import gc
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

import torch
from PIL import Image

from diffusers_utils import (
    get_device,
    get_torch_dtype,
    create_progress_callback,
    get_pipeline_from_cache,
    set_pipeline_cache,
    clear_vram,
    print_memory_stats,
    MODELS_DIR,
)
from utils import (
    load_style_config,
    ensure_output_dir,
    print_status,
    format_duration,
    build_enhanced_prompt,
)


# Standalone model files (ComfyUI approach)
# These are separate files, not a full HuggingFace repository
STANDALONE_MODELS = {
    "gguf_transformer": {
        "url": "https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/wan2.2_i2v_low_noise_14B_Q4_K_M.gguf",
        "filename": "wan2.2_i2v_low_noise_14B_Q4_K_M.gguf",
        "size_gb": 9.0,
        "subdir": "diffusion_models",
    },
    "text_encoder": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "filename": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "size_gb": 4.9,
        "subdir": "text_encoders",
    },
    "vae": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
        "filename": "wan_2.1_vae.safetensors",
        "size_gb": 0.2,
        "subdir": "vae",
    },
    "lora": {
        "url": "https://huggingface.co/lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v/resolve/main/loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
        "filename": "Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
        "size_gb": 0.7,
        "subdir": "loras",
    },
}

# Alternative GGUF variants
GGUF_VARIANTS = {
    "q2_k": ("wan2.2_i2v_low_noise_14B_Q2_K.gguf", 5.3, "fastest, lowest quality"),
    "q3_k_m": ("wan2.2_i2v_low_noise_14B_Q3_K_M.gguf", 7.2, ""),
    "q4_k_m": ("wan2.2_i2v_low_noise_14B_Q4_K_M.gguf", 9.0, "recommended for 10GB VRAM"),
    "q5_k_m": ("wan2.2_i2v_low_noise_14B_Q5_K_M.gguf", 10.8, ""),
    "q6_k": ("wan2.2_i2v_low_noise_14B_Q6_K.gguf", 12.0, "best quality"),
    "q8_0": ("wan2.2_i2v_low_noise_14B_Q8_0.gguf", 15.4, "highest quality"),
}
DEFAULT_GGUF_VARIANT = "q4_k_m"

# Resolution presets for different VRAM levels
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384, "length": 49},
    "medium": {"width": 832, "height": 480, "length": 81},
    "high": {"width": 1280, "height": 720, "length": 81},
}


def download_file(url: str, target: Path, desc: str = None) -> bool:
    """Download a file with progress indication."""
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        print_status(f"Already exists: {target.name}", "success")
        return True

    desc = desc or target.name
    print_status(f"Downloading {desc}...", "progress")

    try:
        urllib.request.urlretrieve(url, str(target))
        print_status(f"Downloaded: {target.name}", "success")
        return True
    except Exception as e:
        print_status(f"Failed to download {desc}: {e}", "error")
        return False


def get_model_path(model_key: str, gguf_variant: str = None) -> Path:
    """Get path to a standalone model file, downloading if needed."""
    if model_key == "gguf_transformer" and gguf_variant:
        # Use specified GGUF variant
        filename, size_gb, _ = GGUF_VARIANTS.get(gguf_variant, GGUF_VARIANTS[DEFAULT_GGUF_VARIANT])
        url = f"https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/{filename}"
        subdir = "diffusion_models"
    else:
        model_info = STANDALONE_MODELS[model_key]
        filename = model_info["filename"]
        url = model_info["url"]
        subdir = model_info["subdir"]

    target_dir = MODELS_DIR / "standalone" / subdir
    target_path = target_dir / filename

    if not target_path.exists():
        download_file(url, target_path, filename)

    return target_path


def load_wan_pipeline(use_lora: bool = True, gguf_variant: str = None):
    """
    Load WAN I2V pipeline using standalone files (ComfyUI approach).

    This loads individual component files instead of a full HuggingFace repository,
    significantly reducing RAM requirements.

    Args:
        use_lora: Whether to load LightX2V distillation LoRA (8-step generation)
        gguf_variant: GGUF quantization variant (default: q4_k_m)

    Returns:
        Loaded pipeline (cached for reuse)
    """
    if gguf_variant is None:
        gguf_variant = DEFAULT_GGUF_VARIANT

    cache_key = f"wan_i2v_standalone_{gguf_variant}" + ("_lora" if use_lora else "")

    # Check cache first
    cached_pipe = get_pipeline_from_cache(cache_key)
    if cached_pipe is not None:
        return cached_pipe

    from diffusers import WanImageToVideoPipeline, WanTransformer3DModel, AutoencoderKLWan
    from diffusers import GGUFQuantizationConfig, FlowMatchEulerDiscreteScheduler
    from transformers import UMT5EncoderModel, AutoTokenizer
    from safetensors.torch import load_file

    device = get_device()
    print_status(f"Loading WAN 2.2 I2V (standalone files, {gguf_variant.upper()})...", "progress")

    # Free memory before loading
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # Get paths to standalone files
    gguf_path = get_model_path("gguf_transformer", gguf_variant)
    text_encoder_path = get_model_path("text_encoder")
    vae_path = get_model_path("vae")

    # 1. Load GGUF transformer
    # Load to CPU first, then move to appropriate device
    print_status("Loading GGUF transformer...", "progress")

    # Create quantization config with modules_to_not_convert to avoid None error
    gguf_config = GGUFQuantizationConfig(compute_dtype=torch.bfloat16)

    # Try loading with explicit CPU target first
    try:
        transformer = WanTransformer3DModel.from_single_file(
            str(gguf_path),
            quantization_config=gguf_config,
            config="Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
            subfolder="transformer",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=False,  # Disable meta tensors
        )
    except Exception as e:
        print_status(f"Standard GGUF loading failed: {e}", "warning")
        print_status("Trying alternative loading method...", "progress")
        # Fallback: load with simpler config
        transformer = WanTransformer3DModel.from_single_file(
            str(gguf_path),
            quantization_config=gguf_config,
        )

    # 2. Load VAE from standalone file
    print_status("Loading VAE...", "progress")
    vae = AutoencoderKLWan.from_single_file(
        str(vae_path),
        torch_dtype=torch.float32,
    )

    # 3. Load FP8 text encoder from Comfy-Org standalone file
    # This file is specifically formatted for WAN and contains FP8 quantized weights
    print_status("Loading text encoder (FP8)...", "progress")

    # Load the FP8 weights directly
    fp8_state_dict = load_file(str(text_encoder_path))

    # Convert FP8 weights to BF16 for compatibility with diffusers
    converted_state_dict = {}
    for key, tensor in fp8_state_dict.items():
        if tensor.dtype in (torch.float8_e4m3fn, torch.float8_e5m2):
            # Scale FP8 back to BF16
            converted_state_dict[key] = tensor.to(torch.bfloat16)
        else:
            converted_state_dict[key] = tensor
    del fp8_state_dict
    gc.collect()

    # Create UMT5 config manually to avoid downloading from HuggingFace
    from transformers import UMT5Config

    # UMT5-XXL config (based on google/umt5-xxl)
    umt5_config = UMT5Config(
        vocab_size=250112,
        d_model=4096,
        d_kv=64,
        d_ff=10240,
        num_layers=24,
        num_decoder_layers=24,
        num_heads=64,
        relative_attention_num_buckets=32,
        relative_attention_max_distance=128,
        dropout_rate=0.1,
        layer_norm_epsilon=1e-6,
        feed_forward_proj="gated-gelu",
        is_encoder_decoder=True,
        use_cache=True,
        pad_token_id=0,
        eos_token_id=1,
        decoder_start_token_id=0,
    )

    # Initialize model with config (no download)
    text_encoder = UMT5EncoderModel(umt5_config)
    text_encoder.load_state_dict(converted_state_dict, strict=False)
    text_encoder = text_encoder.to(torch.bfloat16)
    del converted_state_dict
    gc.collect()
    print_status("Text encoder loaded (FP8->BF16 conversion)", "success")

    # 4. Load tokenizer from HuggingFace (small download, just tokenizer files)
    tokenizer = AutoTokenizer.from_pretrained("google/umt5-xxl")

    # 5. Create scheduler
    scheduler = FlowMatchEulerDiscreteScheduler(
        num_train_timesteps=1000,
        shift=8.0,  # Flow shift from ComfyUI workflow
    )

    # 6. Assemble pipeline
    print_status("Assembling pipeline...", "progress")
    pipe = WanImageToVideoPipeline(
        vae=vae,
        text_encoder=text_encoder,
        tokenizer=tokenizer,
        transformer=transformer,
        scheduler=scheduler,
    )

    # 7. Load LoRA if requested
    if use_lora:
        print_status("Loading LightX2V LoRA...", "progress")
        lora_path = get_model_path("lora")
        try:
            pipe.load_lora_weights(
                str(lora_path.parent),
                weight_name=lora_path.name,
                adapter_name="lightx2v",
            )
            pipe.set_adapters(["lightx2v"], adapter_weights=[1.25])
            print_status("LightX2V LoRA loaded (8-step mode)", "success")
        except Exception as e:
            print_status(f"LoRA loading failed: {e}", "warning")

    # 8. Enable CPU offloading
    pipe.enable_sequential_cpu_offload()
    print_status("Pipeline loaded with sequential CPU offload", "success")

    # Cache for reuse
    set_pipeline_cache(cache_key, pipe)
    print_memory_stats()

    return pipe


def generate_video(
    prompt: str,
    output_path: str,
    start_frame: Optional[str] = None,
    end_frame: Optional[str] = None,
    style_ref: Optional[str] = None,
    length: int = 81,
    steps: int = 8,
    cfg: float = 1.0,
    seed: int = 0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    resolution_preset: Optional[str] = None,
    lora_strength: float = 1.25,
    gguf_variant: Optional[str] = None,
    timeout: int = 600,
) -> str:
    """
    Generate a video using WAN 2.2 with standalone model files.

    Args:
        prompt: Text prompt describing the video content/motion
        output_path: Path to save the generated video
        start_frame: Path to starting frame image (required)
        end_frame: Optional path to ending frame image (enables FLF2V mode)
        style_ref: Optional path to style configuration JSON
        length: Number of frames to generate (default 81 = ~5 seconds at 16fps)
        steps: Number of sampling steps (default 8 with LightX2V LoRA)
        cfg: Classifier-free guidance scale (default 1.0 with LightX2V LoRA)
        seed: Random seed (0 for random)
        width: Video width (overrides preset)
        height: Video height (overrides preset)
        resolution_preset: Resolution preset ("low", "medium", "high")
        lora_strength: LightX2V LoRA strength (default 1.25)
        gguf_variant: GGUF quantization variant (default: q4_k_m)
        timeout: Maximum time (kept for CLI compatibility)

    Returns:
        Path to saved video
    """
    # Validate inputs
    if not start_frame:
        if end_frame:
            start_frame = end_frame
            end_frame = None
            print_status("Using end frame as start frame for I2V", "info")
        else:
            print_status("Error: At least one frame (start_frame) is required", "error")
            sys.exit(1)

    # Apply resolution preset if specified
    if resolution_preset and resolution_preset in RESOLUTION_PRESETS:
        preset = RESOLUTION_PRESETS[resolution_preset]
        if width is None:
            width = preset["width"]
        if height is None:
            height = preset["height"]
        if length == 81:  # Default value
            length = preset["length"]
        print_status(f"Using '{resolution_preset}' preset: {width}x{height}, {length} frames")

    # Set defaults
    if width is None:
        width = 832
    if height is None:
        height = 480

    # Determine mode
    mode = "FLF2V" if end_frame else "I2V"
    print_status(f"Mode: {mode} - {'First-Last-Frame' if mode == 'FLF2V' else 'Image-to-Video'}")

    # Validate frame files
    if not Path(start_frame).exists():
        print_status(f"Start frame not found: {start_frame}", "error")
        sys.exit(1)
    if end_frame and not Path(end_frame).exists():
        print_status(f"End frame not found: {end_frame}", "error")
        sys.exit(1)

    # Load frames
    start_image = Image.open(start_frame).convert("RGB")
    print_status(f"Loaded start frame: {start_frame}")

    end_image = None
    if end_frame:
        end_image = Image.open(end_frame).convert("RGB")
        print_status(f"Loaded end frame: {end_frame}")

    # Load style configuration if provided
    style_config = None
    if style_ref:
        try:
            style_config = load_style_config(style_ref)
            print_status(f"Loaded style config from: {style_ref}")
        except FileNotFoundError:
            print_status(f"Style config not found: {style_ref}", "warning")

    # Build enhanced prompt
    enhanced_prompt = build_enhanced_prompt(prompt, style_config)
    print_status(f"Prompt: {enhanced_prompt[:100]}...")

    # Load pipeline
    pipe = load_wan_pipeline(use_lora=True, gguf_variant=gguf_variant)

    # Check if LoRA is active and set strength
    try:
        active_adapters = pipe.get_active_adapters()
        if active_adapters:
            pipe.set_adapters(["lightx2v"], adapter_weights=[lora_strength])
            print_status(f"LoRA strength set to: {lora_strength}")
    except Exception:
        pass

    # Set up generator for reproducibility
    device = get_device()
    generator = None
    if seed > 0:
        generator = torch.Generator(device=device).manual_seed(seed)
        print_status(f"Using seed: {seed}")
    else:
        print_status("Using random seed")

    # Generate
    print_status(f"Generating video: {width}x{height}, {length} frames, {steps} steps")
    print_status(f"CFG: {cfg}, LoRA strength: {lora_strength}")

    start_time = time.time()
    progress_callback = create_progress_callback(steps)

    try:
        from diffusers.utils import export_to_video

        output = pipe(
            prompt=enhanced_prompt,
            image=start_image,
            last_image=end_image,
            height=height,
            width=width,
            num_frames=length,
            num_inference_steps=steps,
            guidance_scale=cfg,
            generator=generator,
            callback_on_step_end=progress_callback,
            callback_on_step_end_tensor_inputs=["latents"],
        ).frames[0]

        # Save video
        out_path = ensure_output_dir(output_path)

        # Ensure output path has .mp4 extension
        if not str(out_path).lower().endswith('.mp4'):
            out_path = Path(str(out_path) + '.mp4')

        export_to_video(output, str(out_path), fps=16)

        total_time = time.time() - start_time
        duration_sec = length / 16
        print_status(
            f"Video saved to: {out_path} (~{duration_sec:.1f}s at 16fps, generated in {format_duration(total_time)})",
            "success"
        )

        return str(out_path)

    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Generate videos using WAN 2.2 (standalone files approach)"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text prompt describing the video content and motion"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output path for generated video"
    )
    parser.add_argument(
        "--start-frame", "-s",
        help="Path to starting frame image"
    )
    parser.add_argument(
        "--end-frame", "-e",
        help="Path to ending frame image (enables FLF2V mode)"
    )
    parser.add_argument(
        "--style-ref",
        help="Path to style configuration JSON file"
    )
    parser.add_argument(
        "--length", "-n",
        type=int,
        default=81,
        help="Number of frames to generate (default: 81 = ~5s at 16fps)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=8,
        help="Number of sampling steps (default: 8 with LightX2V LoRA)"
    )
    parser.add_argument(
        "--cfg",
        type=float,
        default=1.0,
        help="CFG scale (default: 1.0 with LightX2V LoRA)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed (0 for random)"
    )
    parser.add_argument(
        "--width",
        type=int,
        help="Video width (default: from preset or 832)"
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Video height (default: from preset or 480)"
    )
    parser.add_argument(
        "--preset",
        choices=["low", "medium", "high"],
        default="medium",
        help="Resolution preset (default: medium = 832x480)"
    )
    parser.add_argument(
        "--lora-strength",
        type=float,
        default=1.25,
        help="LightX2V LoRA strength (default: 1.25)"
    )
    parser.add_argument(
        "--gguf",
        dest="gguf_variant",
        choices=list(GGUF_VARIANTS.keys()),
        default=DEFAULT_GGUF_VARIANT,
        help=f"GGUF quantization variant (default: {DEFAULT_GGUF_VARIANT})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds (kept for CLI compatibility)"
    )

    args = parser.parse_args()

    generate_video(
        prompt=args.prompt,
        output_path=args.output,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        style_ref=args.style_ref,
        length=args.length,
        steps=args.steps,
        cfg=args.cfg,
        seed=args.seed,
        width=args.width,
        height=args.height,
        resolution_preset=args.preset,
        lora_strength=args.lora_strength,
        gguf_variant=args.gguf_variant,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
