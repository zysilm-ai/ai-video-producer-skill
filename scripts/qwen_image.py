#!/usr/bin/env python3
"""
Generate keyframe images using Qwen Image Edit 2511 via ComfyUI.
Used for creating keyframes in the AI video production workflow.
Qwen Image Edit 2511 provides the best open-source image editing with
enhanced character/scene consistency across frames.
"""

import argparse
import json
import sys
import time
from pathlib import Path

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

# Resolution presets for different VRAM levels
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384},      # ~8GB VRAM
    "medium": {"width": 832, "height": 480},   # ~10GB VRAM
    "high": {"width": 1280, "height": 720},    # ~16GB+ VRAM
}


def update_workflow_prompts(workflow: dict, prompt: str, negative_prompt: str = None) -> dict:
    """Update text prompts in workflow."""
    default_negative = "blurry, low quality, distorted, deformed, poorly drawn, disfigured, ugly, worst quality"

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        
        # Check for Qwen Generator inputs directly
        if "prompt" in inputs and "{{PROMPT}}" in str(inputs["prompt"]):
            workflow[node_id]["inputs"]["prompt"] = prompt
            
        if "negative_prompt" in inputs:
            workflow[node_id]["inputs"]["negative_prompt"] = negative_prompt or default_negative

        # Also support standard CLIPTextEncode if used in custom workflows
        if class_type == "CLIPTextEncode":
            current_text = inputs.get("text", "")
            if "{{PROMPT}}" in current_text:
                workflow[node_id]["inputs"]["text"] = prompt

    return workflow


def update_workflow_images(workflow: dict, reference_image: str = None) -> dict:
    """Update image inputs in workflow for Editing mode.

    Handles both LoadImage nodes and TextEncodeQwenImageEditPlus image inputs.
    """
    if not reference_image:
        return workflow

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        title = node.get("_meta", {}).get("title", "").lower()

        # Update LoadImage nodes
        if class_type == "LoadImage":
            current_image = str(inputs.get("image", ""))
            # Update reference/input image
            if "{{REFERENCE}}" in current_image or "reference" in title:
                workflow[node_id]["inputs"]["image"] = reference_image

    return workflow


def update_workflow_params(
    workflow: dict,
    width: int = None,
    height: int = None,
    steps: int = None,
    cfg: float = None,
    seed: int = None,
) -> dict:
    """Update generation parameters in workflow."""
    
    # Qwen Generator and other sampling nodes
    generation_classes = [
        "RH_Qwen_Generator",
        "KSampler",
        "KSamplerAdvanced",
        "WanVideoSampler" 
    ]

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type in generation_classes:
            if width is not None and "width" in inputs:
                workflow[node_id]["inputs"]["width"] = width
            if height is not None and "height" in inputs:
                workflow[node_id]["inputs"]["height"] = height
            if steps is not None and "steps" in inputs:
                workflow[node_id]["inputs"]["steps"] = steps
            if cfg is not None and "cfg" in inputs:
                workflow[node_id]["inputs"]["cfg"] = cfg
            if seed is not None and seed > 0 and "seed" in inputs:
                workflow[node_id]["inputs"]["seed"] = seed

    return workflow


def generate_image(
    prompt: str,
    output_path: str,
    style_ref: str | None = None,
    reference_image: str | None = None,
    width: int = 832,
    height: int = 480,
    seed: int = 0,
    steps: int = 20,
    cfg: float = 4.0,
    resolution_preset: str = None,
    workflow_path: str | None = None,
    timeout: int = 300,
) -> str:
    """
    Generate a keyframe image using Qwen Image Edit 2511 via ComfyUI.

    Args:
        prompt: Text prompt describing the image
        output_path: Path to save the generated image
        style_ref: Optional path to style configuration JSON
        reference_image: Optional reference image for editing/consistency
        width: Image width
        height: Image height
        seed: Random seed (0 for random)
        steps: Number of sampling steps
        cfg: Classifier-free guidance scale
        resolution_preset: Resolution preset ("low", "medium", "high")
        workflow_path: Optional custom workflow path
        timeout: Maximum time to wait for generation

    Returns:
        Path to saved image
    """
    # Initialize client
    client = ComfyUIClient()

    if not client.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python main.py --listen 0.0.0.0 --port 8188", "error")
        sys.exit(1)

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

    # Determine workflow based on inputs
    if workflow_path:
        wf_path = Path(workflow_path)
        print_status("Using custom workflow")
    elif reference_image:
        if EDIT_WORKFLOW.exists():
            wf_path = EDIT_WORKFLOW
            print_status("Using Qwen Image Edit 2511 workflow (consistency/editing)")
        else:
            print_status("Edit workflow not found!", "error")
            sys.exit(1)
    elif T2I_WORKFLOW.exists():
        wf_path = T2I_WORKFLOW
        print_status("Using Qwen Image Edit 2511 T2I workflow")
    else:
        print_status("Qwen workflows not found!", "error")
        print_status("Please ensure Qwen workflows are set up correctly.", "error")
        sys.exit(1)

    print_status(f"Generating image with prompt: {enhanced_prompt[:100]}...")
    print_status(f"Resolution: {width}x{height}, Steps: {steps}, CFG: {cfg}")

    # Load workflow
    if not wf_path.exists():
        print_status(f"Workflow not found: {wf_path}", "error")
        sys.exit(1)

    try:
        workflow = load_workflow(str(wf_path))
    except json.JSONDecodeError as e:
        print_status(f"Invalid workflow JSON: {e}", "error")
        sys.exit(1)

    # Upload reference image if provided
    uploaded_ref_name = None
    if reference_image:
        if not Path(reference_image).exists():
            print_status(f"Reference image not found: {reference_image}", "error")
            sys.exit(1)

        print_status(f"Uploading reference image: {reference_image}", "progress")
        try:
            upload_result = client.upload_image(reference_image)
            uploaded_ref_name = upload_result.get('name', str(upload_result))
            print_status(f"Reference uploaded as: {uploaded_ref_name}")
        except Exception as e:
            print_status(f"Failed to upload reference image: {e}", "error")
            sys.exit(1)

    # Update workflow
    workflow = update_workflow_prompts(workflow, enhanced_prompt)
    if uploaded_ref_name:
        workflow = update_workflow_images(workflow, uploaded_ref_name)
    workflow = update_workflow_params(
        workflow,
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        seed=seed,
    )

    # Execute workflow
    print_status("Submitting to ComfyUI...", "progress")
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
            print_status("No images generated!", "error")
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
        help="Reference image path for Editing/Consistency"
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
        help="CFG scale (default: 4.0)"
    )
    parser.add_argument(
        "--workflow",
        help="Custom workflow JSON path"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Maximum time to wait in seconds (default: 300)"
    )

    args = parser.parse_args()

    generate_image(
        prompt=args.prompt,
        output_path=args.output,
        style_ref=args.style_ref,
        reference_image=args.reference_image,
        width=args.width,
        height=args.height,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        resolution_preset=args.preset,
        workflow_path=args.workflow,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
