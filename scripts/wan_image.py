#!/usr/bin/env python3
"""
Generate images using Flux via ComfyUI.
Used for creating keyframes in the AI video production workflow.
"""

import argparse
import json
import sys
from pathlib import Path

from comfyui_client import ComfyUIClient, load_workflow, update_workflow_value
from utils import (
    load_style_config,
    ensure_output_dir,
    print_status,
    build_enhanced_prompt,
)


# Default workflow path
WORKFLOW_DIR = Path(__file__).parent / "workflows"
DEFAULT_WORKFLOW = WORKFLOW_DIR / "flux_t2i.json"


def generate_image(
    prompt: str,
    output_path: str,
    style_ref: str | None = None,
    reference_images: list[str] | None = None,
    width: int = 1280,
    height: int = 720,
    seed: int = 0,
    steps: int = 4,
    workflow_path: str | None = None,
) -> str:
    """
    Generate an image using Flux via ComfyUI.

    Args:
        prompt: Text prompt describing the image
        output_path: Path to save the generated image
        style_ref: Optional path to style configuration JSON
        reference_images: Optional list of reference image paths (for prompt enhancement)
        width: Image width
        height: Image height
        seed: Random seed (0 for random)
        steps: Number of sampling steps
        workflow_path: Optional custom workflow path

    Returns:
        Path to saved image
    """
    # Initialize client
    client = ComfyUIClient()

    if not client.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python main.py --listen 0.0.0.0 --port 8188", "error")
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

    # Add reference image descriptions to prompt if provided
    if reference_images:
        ref_note = "Maintain visual consistency with previous frames. "
        enhanced_prompt = ref_note + enhanced_prompt
        print_status(f"Reference images noted: {len(reference_images)} images")

    print_status(f"Generating image with prompt: {enhanced_prompt[:100]}...")

    # Load workflow
    wf_path = workflow_path or str(DEFAULT_WORKFLOW)
    try:
        workflow = load_workflow(wf_path)
    except FileNotFoundError:
        print_status(f"Workflow not found: {wf_path}", "error")
        print_status("Please ensure Flux workflow is set up correctly.", "error")
        sys.exit(1)

    # Update workflow parameters
    # Find and update prompt node
    for node_id, node in workflow.items():
        if node.get("class_type") == "CLIPTextEncode":
            inputs = node.get("inputs", {})
            if inputs.get("text") == "{{PROMPT}}" or "positive" in node.get("_meta", {}).get("title", "").lower():
                workflow[node_id]["inputs"]["text"] = enhanced_prompt

        # Update image size
        if node.get("class_type") in ["EmptySD3LatentImage", "EmptyLatentImage"]:
            workflow[node_id]["inputs"]["width"] = width
            workflow[node_id]["inputs"]["height"] = height

        # Update seed
        if node.get("class_type") == "KSampler":
            if seed > 0:
                workflow[node_id]["inputs"]["seed"] = seed
            workflow[node_id]["inputs"]["steps"] = steps

    # Execute workflow
    print_status("Submitting to ComfyUI...", "progress")

    def on_progress(msg):
        print_status(msg, "progress")

    try:
        result = client.execute_workflow(
            workflow,
            timeout=300,
            on_progress=on_progress,
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

        print_status(f"Image saved to: {output_path}", "success")
        return str(output)

    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Flux via ComfyUI for video keyframes"
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
        action="append",
        dest="reference_images",
        help="Reference image path for prompt context (can be specified multiple times)"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=1280,
        help="Image width (default: 1280)"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=720,
        help="Image height (default: 720)"
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
        help="Number of sampling steps (default: 4 for schnell)"
    )
    parser.add_argument(
        "--workflow",
        help="Custom workflow JSON path"
    )

    args = parser.parse_args()

    generate_image(
        prompt=args.prompt,
        output_path=args.output,
        style_ref=args.style_ref,
        reference_images=args.reference_images,
        width=args.width,
        height=args.height,
        seed=args.seed,
        steps=args.steps,
        workflow_path=args.workflow,
    )


if __name__ == "__main__":
    main()
