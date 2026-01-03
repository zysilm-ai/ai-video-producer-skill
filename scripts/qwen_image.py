#!/usr/bin/env python3
"""
Generate keyframe images using Qwen Image Edit 2511 via HuggingFace diffusers.
Used for creating keyframes in the AI video production workflow.
Supports T2I, Edit (with reference), and Pose (with ControlNet) modes.
Supports GGUF quantization for low VRAM (10GB) systems.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import torch
from PIL import Image

from diffusers_utils import (
    get_device,
    get_torch_dtype,
    enable_memory_optimization,
    create_progress_callback,
    get_pipeline_from_cache,
    set_pipeline_cache,
    clear_vram,
    get_resolution_preset,
    print_memory_stats,
)
from utils import (
    load_style_config,
    ensure_output_dir,
    print_status,
    format_duration,
    build_enhanced_prompt,
)


# Model IDs
QWEN_EDIT_MODEL = "Qwen/Qwen-Image-Edit-2511"
QWEN_CONTROLNET_MODEL = "InstantX/Qwen-Image-ControlNet-Union"
QWEN_LIGHTNING_LORA = "lightx2v/Qwen-Image-Edit-2511-Lightning"
QWEN_LIGHTNING_LORA_FILENAME = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"

# GGUF quantized models (for low VRAM)
QWEN_GGUF_REPO = "unsloth/Qwen-Image-Edit-2511-GGUF"
QWEN_GGUF_VARIANTS = {
    "q2_k": "qwen-image-edit-2511-Q2_K.gguf",      # 7.2GB, ~4-5GB VRAM
    "q3_k_m": "qwen-image-edit-2511-Q3_K_M.gguf",  # 9.7GB, ~5-6GB VRAM
    "q4_k_m": "qwen-image-edit-2511-Q4_K_M.gguf",  # 13.1GB, ~7-8GB VRAM
    "q8_0": "qwen-image-edit-2511-Q8_0.gguf",      # 21.8GB, ~12GB VRAM
}

# Resolution presets for different VRAM levels
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384},
    "medium": {"width": 832, "height": 480},
    "high": {"width": 1280, "height": 720},
}


def load_qwen_pipeline(
    use_controlnet: bool = False,
    use_lightning: bool = False,
    gguf_variant: str = "q4_k_m",
):
    """
    Load Qwen Image Edit pipeline with caching.

    Args:
        use_controlnet: Whether to load ControlNet for pose-guided generation
        use_lightning: Whether to load Lightning LoRA for fast 4-step generation
        gguf_variant: GGUF quantization variant ("q2_k", "q3_k_m", "q4_k_m", "q8_0", or None for BF16)

    Returns:
        Loaded pipeline (cached for reuse)
    """
    import math
    from huggingface_hub import hf_hub_download

    # Determine cache key based on configuration
    if use_controlnet:
        cache_key = "qwen_controlnet"
    elif gguf_variant:
        cache_key = f"qwen_gguf_{gguf_variant}"
    elif use_lightning:
        cache_key = "qwen_lightning"
    else:
        cache_key = "qwen_edit"

    # Check cache first
    cached_pipe = get_pipeline_from_cache(cache_key)
    if cached_pipe is not None:
        return cached_pipe

    device = get_device()
    dtype = get_torch_dtype(device)

    if use_controlnet:
        from diffusers import FluxControlNetPipeline, FluxControlNetModel

        print_status("Loading Qwen ControlNet pipeline...", "progress")

        # Load ControlNet model
        controlnet = FluxControlNetModel.from_pretrained(
            QWEN_CONTROLNET_MODEL,
            torch_dtype=dtype,
        )

        # Load pipeline with ControlNet
        pipe = FluxControlNetPipeline.from_pretrained(
            QWEN_EDIT_MODEL,
            controlnet=controlnet,
            torch_dtype=dtype,
        )

        pipe = enable_memory_optimization(pipe)
        print_status("Qwen ControlNet pipeline loaded", "success")

    elif gguf_variant and gguf_variant in QWEN_GGUF_VARIANTS:
        # Load GGUF quantized model for low VRAM
        from diffusers import QwenImageEditPlusPipeline, QwenImageTransformer2DModel, GGUFQuantizationConfig

        gguf_filename = QWEN_GGUF_VARIANTS[gguf_variant]
        print_status(f"Loading Qwen GGUF ({gguf_variant.upper()})...", "progress")

        # Download GGUF file from unsloth
        gguf_path = hf_hub_download(
            repo_id=QWEN_GGUF_REPO,
            filename=gguf_filename,
        )
        print_status(f"GGUF model: {gguf_filename}", "info")

        # Load transformer from GGUF using original Qwen config
        # See: https://github.com/huggingface/diffusers/issues/12891
        transformer = QwenImageTransformer2DModel.from_single_file(
            gguf_path,
            quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
            torch_dtype=torch.bfloat16,
            config=QWEN_EDIT_MODEL,
            subfolder="transformer",
        )

        # Load pipeline with quantized transformer
        pipe = QwenImageEditPlusPipeline.from_pretrained(
            QWEN_EDIT_MODEL,
            transformer=transformer,
            torch_dtype=torch.bfloat16,
        )

        # Keep model fully on GPU for speed (Q2_K ~7GB fits in 10GB VRAM)
        pipe.to("cuda")
        print_status(f"Qwen GGUF pipeline loaded on GPU ({gguf_variant.upper()})", "success")

    else:
        from diffusers import QwenImageEditPlusPipeline, FlowMatchEulerDiscreteScheduler

        print_status("Loading Qwen Image Edit pipeline (BF16)...", "progress")

        # Custom scheduler config for Lightning LoRA
        if use_lightning:
            scheduler_config = {
                "base_image_seq_len": 256,
                "base_shift": math.log(3),
                "invert_sigmas": False,
                "max_image_seq_len": 8192,
                "max_shift": math.log(3),
                "num_train_timesteps": 1000,
                "shift": 1.0,
                "shift_terminal": None,
                "stochastic_sampling": False,
                "time_shift_type": "exponential",
                "use_beta_sigmas": False,
                "use_dynamic_shifting": True,
                "use_exponential_sigmas": False,
                "use_karras_sigmas": False,
            }
            scheduler = FlowMatchEulerDiscreteScheduler.from_config(scheduler_config)

            pipe = QwenImageEditPlusPipeline.from_pretrained(
                QWEN_EDIT_MODEL,
                scheduler=scheduler,
                torch_dtype=dtype,
            )
        else:
            pipe = QwenImageEditPlusPipeline.from_pretrained(
                QWEN_EDIT_MODEL,
                torch_dtype=dtype,
            )

        # Load Lightning LoRA for fast 4-step generation
        if use_lightning:
            print_status("Loading Lightning distillation LoRA...", "progress")
            try:
                pipe.load_lora_weights(
                    QWEN_LIGHTNING_LORA,
                    weight_name=QWEN_LIGHTNING_LORA_FILENAME,
                )
                print_status("Lightning LoRA loaded (4-step mode)", "success")
            except Exception as e:
                print_status(f"Warning: Could not load Lightning LoRA: {e}", "warning")
                print_status("Using base model (slower, more steps needed)", "warning")

        pipe = enable_memory_optimization(pipe)
        print_status("Qwen Image Edit pipeline loaded", "success")

    # Cache for reuse
    set_pipeline_cache(cache_key, pipe)
    print_memory_stats()

    return pipe


def generate_image(
    prompt: str,
    output_path: str,
    style_ref: Optional[str] = None,
    reference_image: Optional[str] = None,
    pose_image: Optional[str] = None,
    control_strength: float = 0.9,
    width: int = 832,
    height: int = 480,
    seed: int = 0,
    steps: int = 20,
    cfg: float = 4.0,
    shift: float = 5.0,
    resolution_preset: Optional[str] = None,
    gguf_variant: Optional[str] = "q2_k",
    timeout: int = 300,
) -> str:
    """
    Generate a keyframe image using Qwen Image Edit 2511 via diffusers.

    Args:
        prompt: Text prompt describing the image
        output_path: Path to save the generated image
        style_ref: Optional path to style configuration JSON
        reference_image: Optional reference image for editing/consistency (up to 3 images)
        pose_image: Optional pose reference image (uses ControlNet for pose guidance)
        control_strength: ControlNet strength for pose guidance (default: 0.9)
        width: Image width
        height: Image height
        seed: Random seed (0 for random)
        steps: Number of sampling steps (default 20)
        cfg: Guidance scale (default 4.0)
        shift: Flow matching shift parameter (default 5.0, range 3.0-8.0)
        resolution_preset: Resolution preset ("low", "medium", "high")
        gguf_variant: GGUF quantization variant ("q2_k", "q3_k_m", "q4_k_m", "q8_0", or None for BF16)
        timeout: Maximum time to wait for generation (unused in diffusers, kept for compatibility)

    Returns:
        Path to saved image
    """
    # Apply resolution preset if specified
    if resolution_preset and resolution_preset in RESOLUTION_PRESETS:
        preset = RESOLUTION_PRESETS[resolution_preset]
        width = preset["width"]
        height = preset["height"]
        print_status(f"Using '{resolution_preset}' preset: {width}x{height}")

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

    # Determine mode based on inputs
    use_controlnet = pose_image is not None
    if use_controlnet:
        print_status("Mode: Pose-guided generation with ControlNet")
    elif reference_image:
        print_status("Mode: Edit/Consistency with reference image")
    else:
        print_status("Mode: Text-to-Image generation")

    # Load pipeline
    pipe = load_qwen_pipeline(
        use_controlnet=use_controlnet,
        gguf_variant=gguf_variant if not use_controlnet else None,
    )

    # Set up generator for reproducibility
    device = get_device()
    generator = None
    if seed > 0:
        generator = torch.Generator(device=device).manual_seed(seed)
        print_status(f"Using seed: {seed}")
    else:
        print_status("Using random seed")

    # Load reference image(s) if provided
    ref_images = None
    if reference_image:
        ref_path = Path(reference_image)
        if ref_path.exists():
            ref_img = Image.open(ref_path).convert("RGB")
            ref_images = [ref_img]
            print_status(f"Loaded reference image: {reference_image}")
        else:
            print_status(f"Reference image not found: {reference_image}", "error")
            sys.exit(1)

    # Load pose image for ControlNet
    control_image = None
    if pose_image:
        pose_path = Path(pose_image)
        if pose_path.exists():
            control_image = Image.open(pose_path).convert("RGB")
            print_status(f"Loaded pose image: {pose_image}")
            print_status(f"ControlNet strength: {control_strength}")
        else:
            print_status(f"Pose image not found: {pose_image}", "error")
            sys.exit(1)

    # Generate
    print_status(f"Generating: {enhanced_prompt[:100]}...")
    print_status(f"Resolution: {width}x{height}, Steps: {steps}, CFG: {cfg}")

    start_time = time.time()
    progress_callback = create_progress_callback(steps)

    try:
        if use_controlnet and control_image:
            # Pose-guided generation with ControlNet
            output = pipe(
                prompt=enhanced_prompt,
                image=ref_images,
                control_image=control_image,
                controlnet_conditioning_scale=control_strength,
                height=height,
                width=width,
                num_inference_steps=steps,
                true_cfg_scale=cfg,
                generator=generator,
                callback_on_step_end=progress_callback,
                callback_on_step_end_tensor_inputs=["latents"],
            ).images[0]
        elif ref_images:
            # Edit mode with reference image
            output = pipe(
                prompt=enhanced_prompt,
                image=ref_images,
                height=height,
                width=width,
                num_inference_steps=steps,
                true_cfg_scale=cfg,
                generator=generator,
                callback_on_step_end=progress_callback,
                callback_on_step_end_tensor_inputs=["latents"],
            ).images[0]
        else:
            # T2I mode - create a blank/noise image as reference
            # QwenImageEditPlusPipeline requires an image input
            import numpy as np
            blank_image = Image.fromarray(
                np.random.randint(128, 130, (height, width, 3), dtype=np.uint8)
            )
            output = pipe(
                prompt=enhanced_prompt,
                image=[blank_image],
                height=height,
                width=width,
                num_inference_steps=steps,
                true_cfg_scale=cfg,
                generator=generator,
                callback_on_step_end=progress_callback,
                callback_on_step_end_tensor_inputs=["latents"],
            ).images[0]

        # Save output
        out_path = ensure_output_dir(output_path)
        output.save(out_path)

        total_time = time.time() - start_time
        print_status(f"Image saved to: {output_path} ({format_duration(total_time)})", "success")

        return str(out_path)

    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Generate keyframe images using Qwen Image Edit 2511 via diffusers"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text prompt describing the image to generate"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output path for generated image"
    )
    parser.add_argument(
        "--style-ref", "-s",
        help="Path to style configuration JSON file"
    )
    parser.add_argument(
        "--reference", "-r",
        dest="reference_image",
        help="Reference image path for Editing/Consistency"
    )
    parser.add_argument(
        "--pose", "-P",
        dest="pose_image",
        help="Pose reference image (extracts skeleton for pose-guided generation)"
    )
    parser.add_argument(
        "--control-strength",
        type=float,
        default=0.9,
        help="ControlNet strength for pose guidance (default: 0.9)"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=832,
        help="Image width (default: 832)"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=480,
        help="Image height (default: 480)"
    )
    parser.add_argument(
        "--preset",
        choices=["low", "medium", "high"],
        default="medium",
        help="Resolution preset (default: medium = 832x480)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed (0 for random)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=20,
        help="Number of sampling steps (default: 20)"
    )
    parser.add_argument(
        "--cfg",
        type=float,
        default=4.0,
        help="Guidance scale (default: 4.0)"
    )
    parser.add_argument(
        "--gguf",
        dest="gguf_variant",
        choices=["q2_k", "q3_k_m", "q4_k_m", "q8_0", "none"],
        default="q2_k",
        help="GGUF quantization variant (default: q2_k ~7GB, fits 10GB VRAM; use 'none' for BF16)"
    )
    parser.add_argument(
        "--shift",
        type=float,
        default=5.0,
        help="Flow matching shift parameter (default: 5.0, kept for compatibility)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds (kept for CLI compatibility)"
    )

    args = parser.parse_args()

    # Handle gguf_variant - convert "none" to None
    gguf_variant = args.gguf_variant if args.gguf_variant != "none" else None

    generate_image(
        prompt=args.prompt,
        output_path=args.output,
        style_ref=args.style_ref,
        reference_image=args.reference_image,
        pose_image=args.pose_image,
        control_strength=args.control_strength,
        width=args.width,
        height=args.height,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        shift=args.shift,
        resolution_preset=args.preset,
        gguf_variant=gguf_variant,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
