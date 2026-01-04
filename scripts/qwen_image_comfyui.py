#!/usr/bin/env python3
"""
Generate keyframe images using Qwen Image Edit 2511 via ComfyUI.
Supports T2I, Edit (with reference), and Pose (with ControlNet) modes.
Uses GGUF quantization for efficient inference on consumer GPUs.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from comfyui_client import (
    ComfyUIClient,
    ComfyUIError,
    WorkflowValidationError,
    load_workflow,
)
from utils import (
    load_style_config,
    ensure_output_dir,
    print_status,
    format_duration,
    build_enhanced_prompt,
)


# Default workflow paths
WORKFLOW_DIR = Path(__file__).parent / "workflows"
T2I_WORKFLOW = WORKFLOW_DIR / "qwen_t2i.json"
EDIT_WORKFLOW = WORKFLOW_DIR / "qwen_edit.json"
POSE_WORKFLOW = WORKFLOW_DIR / "qwen_pose.json"

# GGUF model variants (file must be in ComfyUI diffusion_models folder)
GGUF_VARIANTS = {
    "q2_k": "qwen-image-edit-2511-Q2_K.gguf",      # ~7GB - fastest, lower quality
    "q3_k_m": "qwen-image-edit-2511-Q3_K_M.gguf",  # ~10GB
    "q4_k_m": "qwen-image-edit-2511-Q4_K_M.gguf",  # ~13GB - recommended
    "q5_k_m": "qwen-image-edit-2511-Q5_K_M.gguf",  # ~15GB
    "q6_k": "qwen-image-edit-2511-Q6_K.gguf",      # ~17GB - best quality/speed
    "q8_0": "qwen-image-edit-2511-Q8_0.gguf",      # ~22GB - highest quality
}

# Lightning LoRA for fast 4-step generation
LIGHTNING_LORA = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"

# Resolution presets
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384},
    "medium": {"width": 832, "height": 480},
    "high": {"width": 1280, "height": 720},
}

# Default negative prompt
DEFAULT_NEGATIVE = "bad quality, worst quality, blurry, distorted, deformed, ugly, low resolution, poorly drawn"


def update_workflow_model(workflow: dict, model_name: str, lora_name: str) -> dict:
    """Update model and LoRA names in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})

        # Update GGUF model name
        if "unet_name" in inputs and "{{MODEL_NAME}}" in str(inputs.get("unet_name", "")):
            workflow[node_id]["inputs"]["unet_name"] = model_name
        elif inputs.get("unet_name") == "{{MODEL_NAME}}":
            workflow[node_id]["inputs"]["unet_name"] = model_name

        # Update LoRA name
        if "lora_name" in inputs and "{{LORA_NAME}}" in str(inputs.get("lora_name", "")):
            workflow[node_id]["inputs"]["lora_name"] = lora_name
        elif inputs.get("lora_name") == "{{LORA_NAME}}":
            workflow[node_id]["inputs"]["lora_name"] = lora_name

    return workflow


def update_workflow_prompts(
    workflow: dict,
    prompt: str,
    negative_prompt: str = None
) -> dict:
    """Update text prompts in workflow."""
    if negative_prompt is None:
        negative_prompt = DEFAULT_NEGATIVE

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})

        # Update positive prompt
        if inputs.get("prompt") == "{{PROMPT}}":
            workflow[node_id]["inputs"]["prompt"] = prompt

        # Update negative prompt
        if inputs.get("text") == "{{NEGATIVE_PROMPT}}":
            workflow[node_id]["inputs"]["text"] = negative_prompt

    return workflow


def update_workflow_images(
    workflow: dict,
    reference: str = None,
    pose: str = None
) -> dict:
    """Update image inputs in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})
        title = node.get("_meta", {}).get("title", "").lower()

        if node.get("class_type") == "LoadImage":
            current_image = str(inputs.get("image", ""))

            # Reference image
            if "{{REFERENCE}}" in current_image or "reference" in title:
                if reference:
                    workflow[node_id]["inputs"]["image"] = reference

            # Pose image
            if "{{POSE}}" in current_image or "pose" in title:
                if pose:
                    workflow[node_id]["inputs"]["image"] = pose

    return workflow


def update_workflow_resolution(
    workflow: dict,
    width: int = None,
    height: int = None,
) -> dict:
    """Update resolution parameters in workflow."""
    resolution_nodes = [
        "EmptyQwenImageLayeredLatentImage",
        "EmptySD3LatentImage",
        "ImageScale",
        "OpenposePreprocessor",
    ]

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type in resolution_nodes:
            if width is not None and "width" in inputs:
                workflow[node_id]["inputs"]["width"] = width
            if height is not None and "height" in inputs:
                workflow[node_id]["inputs"]["height"] = height
            # OpenposePreprocessor uses 'resolution' instead of width/height
            if class_type == "OpenposePreprocessor" and width is not None:
                workflow[node_id]["inputs"]["resolution"] = width

    return workflow


def update_workflow_sampler(
    workflow: dict,
    steps: int = None,
    cfg: float = None,
    seed: int = None,
    shift: float = None,
) -> dict:
    """Update sampler and flow matching parameters in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # Update KSampler
        if class_type == "KSampler":
            if steps is not None:
                workflow[node_id]["inputs"]["steps"] = steps
            if cfg is not None:
                workflow[node_id]["inputs"]["cfg"] = cfg
            if seed is not None and seed > 0:
                workflow[node_id]["inputs"]["seed"] = seed

        # Update ModelSamplingAuraFlow (shift parameter)
        if class_type == "ModelSamplingAuraFlow":
            if shift is not None:
                workflow[node_id]["inputs"]["shift"] = shift

    return workflow


def update_workflow_controlnet(
    workflow: dict,
    control_strength: float = None,
) -> dict:
    """Update ControlNet strength in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")

        if class_type == "ControlNetApplySD3":
            if control_strength is not None:
                workflow[node_id]["inputs"]["strength"] = control_strength

    return workflow


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
    steps: int = 4,
    cfg: float = 1.0,
    shift: float = 5.0,
    resolution_preset: Optional[str] = None,
    gguf_variant: str = "q4_k_m",
    use_lightning: bool = True,
    timeout: int = 300,
    workflow_path: Optional[str] = None,
) -> str:
    """
    Generate a keyframe image using Qwen Image Edit 2511 via ComfyUI.

    Args:
        prompt: Text prompt describing the image
        output_path: Path to save the generated image
        style_ref: Optional path to style configuration JSON
        reference_image: Optional reference image for editing/consistency
        pose_image: Optional pose reference image (enables ControlNet pose mode)
        control_strength: ControlNet strength for pose guidance (default: 0.9)
        width: Image width
        height: Image height
        seed: Random seed (0 for random)
        steps: Number of sampling steps (default 4 with Lightning LoRA)
        cfg: Guidance scale (default 1.0 with Lightning LoRA)
        shift: Flow matching shift parameter (default 5.0)
        resolution_preset: Resolution preset ("low", "medium", "high")
        gguf_variant: GGUF quantization variant
        use_lightning: Use Lightning LoRA for fast 4-step generation
        timeout: Maximum time to wait for generation
        workflow_path: Custom workflow file path

    Returns:
        Path to saved image
    """
    # Initialize client
    client = ComfyUIClient()

    if not client.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python scripts/setup_comfyui.py --start", "error")
        sys.exit(1)

    # Apply resolution preset if specified
    if resolution_preset and resolution_preset in RESOLUTION_PRESETS:
        preset = RESOLUTION_PRESETS[resolution_preset]
        width = preset["width"]
        height = preset["height"]
        print_status(f"Using '{resolution_preset}' preset: {width}x{height}")

    # Get model and LoRA names
    if gguf_variant not in GGUF_VARIANTS:
        print_status(f"Unknown GGUF variant: {gguf_variant}, using q4_k_m", "warning")
        gguf_variant = "q4_k_m"

    model_name = GGUF_VARIANTS[gguf_variant]
    lora_name = LIGHTNING_LORA if use_lightning else ""

    # Determine mode and select workflow
    if workflow_path:
        mode = "custom"
        workflow_file = Path(workflow_path)
        print_status("Mode: Custom workflow")
    elif pose_image:
        mode = "pose"
        workflow_file = POSE_WORKFLOW
        print_status("Mode: Pose-guided generation with ControlNet")
    elif reference_image:
        mode = "edit"
        workflow_file = EDIT_WORKFLOW
        print_status("Mode: Edit/Consistency with reference image")
    else:
        mode = "t2i"
        workflow_file = T2I_WORKFLOW
        print_status("Mode: Text-to-Image generation")

    # Validate input files exist
    if reference_image and not Path(reference_image).exists():
        print_status(f"Reference image not found: {reference_image}", "error")
        sys.exit(1)
    if pose_image and not Path(pose_image).exists():
        print_status(f"Pose image not found: {pose_image}", "error")
        sys.exit(1)

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

    # Load workflow
    if not workflow_file.exists():
        print_status(f"Workflow not found: {workflow_file}", "error")
        print_status("Please ensure Qwen workflows are set up correctly.", "error")
        sys.exit(1)

    try:
        workflow = load_workflow(str(workflow_file))
    except json.JSONDecodeError as e:
        print_status(f"Invalid workflow JSON: {e}", "error")
        sys.exit(1)

    # Upload images if needed
    ref_image_name = None
    pose_image_name = None

    if reference_image:
        print_status("Uploading reference image to ComfyUI...", "progress")
        try:
            result = client.upload_image(reference_image)
            ref_image_name = result["name"]
            print_status(f"Uploaded reference: {ref_image_name}")
        except Exception as e:
            print_status(f"Failed to upload reference image: {e}", "error")
            sys.exit(1)

    if pose_image:
        print_status("Uploading pose image to ComfyUI...", "progress")
        try:
            result = client.upload_image(pose_image)
            pose_image_name = result["name"]
            print_status(f"Uploaded pose: {pose_image_name}")
        except Exception as e:
            print_status(f"Failed to upload pose image: {e}", "error")
            sys.exit(1)

    # Update workflow with all parameters
    workflow = update_workflow_model(workflow, model_name, lora_name)
    workflow = update_workflow_prompts(workflow, enhanced_prompt)
    workflow = update_workflow_images(workflow, ref_image_name, pose_image_name)
    workflow = update_workflow_resolution(workflow, width, height)
    workflow = update_workflow_sampler(workflow, steps, cfg, seed, shift)
    workflow = update_workflow_controlnet(workflow, control_strength)

    # Execute workflow
    print_status("Submitting image generation request...", "progress")
    print_status(f"Model: {model_name}")
    if use_lightning:
        print_status(f"Using Lightning LoRA (4-step fast mode)")
    print_status(f"Settings: {width}x{height}, {steps} steps, CFG {cfg}, Shift {shift}")

    start_time = time.time()

    def on_progress(msg):
        elapsed = time.time() - start_time
        print_status(f"{msg} ({format_duration(elapsed)})", "progress")

    try:
        result = client.execute_workflow(
            workflow,
            timeout=timeout,
            on_progress=on_progress,
            validate=True,
        )

        # Get output images
        images = client.get_output_images(result)

        if not images:
            print_status("No image generated!", "error")
            sys.exit(1)

        # Download and save the first image
        output = ensure_output_dir(output_path)
        image_info = images[0]
        client.download_output(image_info, str(output))

        total_time = time.time() - start_time
        print_status(f"Image saved to: {output_path} ({format_duration(total_time)})", "success")

        return str(output)

    except WorkflowValidationError as e:
        print_status("Workflow validation failed:", "error")
        print(str(e))
        sys.exit(1)
    except ComfyUIError as e:
        print_status("ComfyUI error:", "error")
        print(str(e))
        sys.exit(1)
    except TimeoutError:
        print_status(f"Generation timed out after {timeout}s", "error")
        sys.exit(1)
    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate keyframe images using Qwen Image Edit 2511 via ComfyUI"
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
        help="Reference image path for editing/consistency"
    )
    parser.add_argument(
        "--pose", "-P",
        dest="pose_image",
        help="Pose reference image (enables ControlNet pose mode)"
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
        default=4,
        help="Number of sampling steps (default: 4 with Lightning LoRA)"
    )
    parser.add_argument(
        "--cfg",
        type=float,
        default=1.0,
        help="Guidance scale (default: 1.0 with Lightning LoRA)"
    )
    parser.add_argument(
        "--shift",
        type=float,
        default=5.0,
        help="Flow matching shift parameter (default: 5.0)"
    )
    parser.add_argument(
        "--gguf",
        dest="gguf_variant",
        choices=list(GGUF_VARIANTS.keys()),
        default="q4_k_m",
        help="GGUF quantization variant (default: q4_k_m, ~13GB)"
    )
    parser.add_argument(
        "--lightning",
        action="store_true",
        default=True,
        help="Use Lightning LoRA for fast 4-step generation (default: enabled)"
    )
    parser.add_argument(
        "--no-lightning",
        dest="lightning",
        action="store_false",
        help="Disable Lightning LoRA (use full 20-step generation)"
    )
    parser.add_argument(
        "--workflow",
        help="Custom workflow JSON file path"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum time to wait in seconds (default: 300 = 5 min)"
    )

    args = parser.parse_args()

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
        gguf_variant=args.gguf_variant,
        use_lightning=args.lightning,
        timeout=args.timeout,
        workflow_path=args.workflow,
    )


if __name__ == "__main__":
    main()
