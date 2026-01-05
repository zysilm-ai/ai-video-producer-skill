#!/usr/bin/env python3
"""
Angle Transformer for Keyframes.

Transforms existing keyframes to different camera angles using Multi-Angle LoRA.
This enables dynamic camera movements between scenes without regenerating
character identities.

Usage:
    # Transform keyframe to low angle shot
    python angle_transformer.py \\
        --input keyframes/KF-A.png \\
        --output keyframes/KF-A-lowangle.png \\
        --tilt -30 \\
        --prompt "dramatic low angle action shot"

    # Rotate camera 45 degrees left
    python angle_transformer.py \\
        --input keyframes/KF-B.png \\
        --output keyframes/KF-B-rotated.png \\
        --rotate -45

    # Wide angle with camera rotation
    python angle_transformer.py \\
        --input keyframes/KF-C.png \\
        --output keyframes/KF-C-wide.png \\
        --rotate 30 \\
        --zoom wide
"""

import argparse
import sys
from pathlib import Path

from core import (
    QwenImageGenerator,
    MULTIANGLE_WORKFLOW,
    MULTIANGLE_LORA,
    GGUF_VARIANTS,
    LIGHTNING_LORA,
    print_status,
)
from comfyui_client import ComfyUIClient, load_workflow
from utils import ensure_output_dir


def build_angle_prompt(
    rotate_degrees: float = 0,
    tilt_degrees: float = 0,
    zoom: str = "normal",
    custom_prompt: str = None,
) -> str:
    """
    Build an angle transformation prompt.

    Args:
        rotate_degrees: Horizontal rotation (-180 to 180, negative = left)
        tilt_degrees: Vertical tilt (-90 to 90, negative = look up)
        zoom: Lens type (wide, normal, close)
        custom_prompt: Override with custom description

    Returns:
        Prompt string for angle transformation
    """
    if custom_prompt:
        return custom_prompt

    parts = []

    if rotate_degrees != 0:
        direction = "left" if rotate_degrees < 0 else "right"
        parts.append(f"rotate camera {abs(rotate_degrees)} degrees {direction}")

    if tilt_degrees != 0:
        if tilt_degrees < 0:
            parts.append(f"low angle shot looking up {abs(tilt_degrees)} degrees")
        else:
            parts.append(f"high angle shot looking down {tilt_degrees} degrees")

    if zoom == "wide":
        parts.append("wide-angle lens, expansive view")
    elif zoom == "close":
        parts.append("close-up shot, tight framing")

    if not parts:
        return "maintain current camera angle and perspective"

    return ", ".join(parts)


def transform_angle(
    input_image: str,
    output_path: str,
    rotate_degrees: float = 0,
    tilt_degrees: float = 0,
    zoom: str = "normal",
    prompt: str = None,
    angle_lora_strength: float = 0.8,
    resolution_preset: str = "medium",
    seed: int = 0,
    free_memory: bool = False,
) -> str:
    """
    Transform a keyframe to a new camera angle using Multi-Angle LoRA.

    This is a two-step approach (Approach B):
    1. Takes an already-generated keyframe as input
    2. Applies Multi-Angle LoRA to transform the camera perspective

    Args:
        input_image: Path to source keyframe image
        output_path: Path to save transformed image
        rotate_degrees: Horizontal rotation (-180 to 180, negative = left)
        tilt_degrees: Vertical tilt (-90 to 90, negative = look up)
        zoom: Lens type (wide, normal, close)
        prompt: Optional custom angle description (overrides auto-generated)
        angle_lora_strength: Multi-Angle LoRA strength (0.0-1.0)
        resolution_preset: Resolution preset (low, medium, high)
        seed: Random seed (0 for random)
        free_memory: Free GPU memory before generation

    Returns:
        Path to saved transformed image
    """
    # Validate inputs
    if not Path(input_image).exists():
        print_status(f"Input image not found: {input_image}", "error")
        sys.exit(1)

    if zoom not in ["wide", "normal", "close"]:
        print_status(f"Invalid zoom value: {zoom}. Use: wide, normal, close", "error")
        sys.exit(1)

    # Check for Multi-Angle LoRA
    # Note: The LoRA will be downloaded by setup_comfyui.py if not present

    # Build angle prompt
    angle_prompt = build_angle_prompt(rotate_degrees, tilt_degrees, zoom, prompt)
    print_status(f"Angle transformation: {angle_prompt}")

    # Initialize generator
    generator = QwenImageGenerator(resolution_preset=resolution_preset)

    if not generator.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python scripts/setup_comfyui.py --start", "error")
        sys.exit(1)

    if free_memory:
        generator.free_memory()

    # For angle transformation, we need to use the multiangle workflow
    # with both Lightning LoRA and Multi-Angle LoRA
    from core import update_workflow_model, update_workflow_prompts, update_workflow_images
    from core import update_workflow_resolution, update_workflow_sampler

    workflow_path = MULTIANGLE_WORKFLOW
    if not workflow_path.exists():
        print_status(f"Multi-angle workflow not found: {workflow_path}", "error")
        sys.exit(1)

    print_status("Mode: Camera angle transformation")
    print_status(f"Input keyframe: {input_image}")
    print_status(f"Transform: rotate={rotate_degrees}, tilt={tilt_degrees}, zoom={zoom}")

    # Load workflow
    workflow = load_workflow(str(workflow_path))

    # Upload input keyframe
    client = ComfyUIClient()
    print_status("Uploading input keyframe...", "progress")
    result = client.upload_image(input_image)
    uploaded_name = result["name"]
    print_status(f"Uploaded: {uploaded_name}")

    # Get resolution from preset
    from core import RESOLUTION_PRESETS
    if resolution_preset in RESOLUTION_PRESETS:
        preset = RESOLUTION_PRESETS[resolution_preset]
        width = preset["width"]
        height = preset["height"]
    else:
        width = 832
        height = 480

    # Update workflow
    workflow = update_workflow_model(
        workflow,
        generator.model_name,
        generator.lora_name,
        angle_lora_name=MULTIANGLE_LORA
    )
    workflow = update_workflow_prompts(workflow, angle_prompt)
    workflow = update_workflow_images(workflow, reference=uploaded_name)
    workflow = update_workflow_resolution(workflow, width, height)
    workflow = update_workflow_sampler(workflow, seed=seed)

    # Update angle LoRA strength
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("_meta", {}).get("title") == "Multi-Angle LoRA":
            workflow[node_id]["inputs"]["strength_model"] = angle_lora_strength
            workflow[node_id]["inputs"]["strength_clip"] = angle_lora_strength

    # Execute workflow
    print_status("Submitting angle transformation request...", "progress")

    import time
    from utils import format_duration
    start_time = time.time()

    def on_progress(msg):
        elapsed = time.time() - start_time
        print_status(f"{msg} ({format_duration(elapsed)})", "progress")

    try:
        result = client.execute_workflow(
            workflow,
            timeout=300,
            on_progress=on_progress,
            validate=True,
        )

        images = client.get_output_images(result)
        if not images:
            print_status("No image generated!", "error")
            sys.exit(1)

        output = ensure_output_dir(output_path)
        client.download_output(images[0], str(output))

        total_time = time.time() - start_time
        print_status(f"Transformed image saved to: {output_path} ({format_duration(total_time)})", "success")

        return str(output)

    except Exception as e:
        print_status(f"Angle transformation failed: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Transform keyframes to different camera angles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Low angle dramatic shot
  python angle_transformer.py \\
    --input keyframes/KF-A.png \\
    --output keyframes/KF-A-lowangle.png \\
    --tilt -30

  # Rotate camera left
  python angle_transformer.py \\
    --input keyframes/KF-B.png \\
    --output keyframes/KF-B-rotated.png \\
    --rotate -45

  # Wide angle with custom prompt
  python angle_transformer.py \\
    --input keyframes/KF-C.png \\
    --output keyframes/KF-C-wide.png \\
    --zoom wide \\
    --prompt "cinematic wide establishing shot"

  # High angle top-down view
  python angle_transformer.py \\
    --input keyframes/KF-D.png \\
    --output keyframes/KF-D-topdown.png \\
    --tilt 60 \\
    --prompt "top-down bird's eye view of scene"
"""
    )

    # Required arguments
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input keyframe image"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path to save transformed image"
    )

    # Angle controls
    angle_group = parser.add_argument_group("Angle Controls")
    angle_group.add_argument(
        "--rotate", "-r",
        type=float,
        default=0,
        help="Horizontal rotation in degrees (-180 to 180, negative = left)"
    )
    angle_group.add_argument(
        "--tilt", "-t",
        type=float,
        default=0,
        help="Vertical tilt in degrees (-90 to 90, negative = look up)"
    )
    angle_group.add_argument(
        "--zoom", "-z",
        choices=["wide", "normal", "close"],
        default="normal",
        help="Lens/zoom type (default: normal)"
    )
    angle_group.add_argument(
        "--prompt", "-p",
        help="Custom angle description (overrides auto-generated prompt)"
    )

    # Generation settings
    gen_group = parser.add_argument_group("Generation Settings")
    gen_group.add_argument(
        "--lora-strength",
        type=float,
        default=0.8,
        help="Multi-Angle LoRA strength (default: 0.8)"
    )
    gen_group.add_argument(
        "--preset",
        choices=["low", "medium", "high"],
        default="medium",
        help="Resolution preset (default: medium = 832x480)"
    )
    gen_group.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed (0 for random)"
    )
    gen_group.add_argument(
        "--free-memory",
        action="store_true",
        help="Free GPU memory before generation"
    )

    args = parser.parse_args()

    # Validate angle ranges
    if not -180 <= args.rotate <= 180:
        print_status("Rotation must be between -180 and 180 degrees", "error")
        sys.exit(1)
    if not -90 <= args.tilt <= 90:
        print_status("Tilt must be between -90 and 90 degrees", "error")
        sys.exit(1)

    transform_angle(
        input_image=args.input,
        output_path=args.output,
        rotate_degrees=args.rotate,
        tilt_degrees=args.tilt,
        zoom=args.zoom,
        prompt=args.prompt,
        angle_lora_strength=args.lora_strength,
        resolution_preset=args.preset,
        seed=args.seed,
        free_memory=args.free_memory,
    )


if __name__ == "__main__":
    main()
