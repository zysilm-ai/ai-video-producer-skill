#!/usr/bin/env python3
"""
Generate videos using WAN 2.2 GGUF via ComfyUI.
Supports single-frame (I2V) and dual-frame (FLF2V) generation modes.
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
    find_node_by_title,
    find_node_by_class,
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
I2V_WORKFLOW = WORKFLOW_DIR / "wan_i2v.json"
FLF2V_WORKFLOW = WORKFLOW_DIR / "wan_flf2v.json"

# Resolution presets for different VRAM levels
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384, "num_frames": 49},    # ~8GB VRAM
    "medium": {"width": 832, "height": 480, "num_frames": 49},  # ~10GB VRAM
    "high": {"width": 1280, "height": 720, "num_frames": 81},   # ~16GB+ VRAM
}


def update_workflow_prompts(workflow: dict, prompt: str, negative_prompt: str = None) -> dict:
    """Update text prompts in workflow."""
    default_negative = "blurry, low quality, distorted, deformed, static, poorly drawn, disfigured, ugly, worst quality"

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        title = node.get("_meta", {}).get("title", "").lower()

        if class_type == "CLIPTextEncode":
            current_text = inputs.get("text", "")

            # Check if this is the positive prompt
            if "{{PROMPT}}" in current_text or "positive" in title:
                workflow[node_id]["inputs"]["text"] = prompt
            # Check if this is the negative prompt
            elif "negative" in title:
                workflow[node_id]["inputs"]["text"] = negative_prompt or default_negative

    return workflow


def update_workflow_images(
    workflow: dict,
    start_frame: str = None,
    end_frame: str = None
) -> dict:
    """Update image inputs in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        title = node.get("_meta", {}).get("title", "").lower()

        if class_type == "LoadImage":
            current_image = str(inputs.get("image", ""))

            # Determine which frame this node expects
            is_start = any(x in title for x in ["first", "start"]) or "{{START_FRAME}}" in current_image
            is_end = any(x in title for x in ["last", "end"]) or "{{END_FRAME}}" in current_image

            if is_start and start_frame:
                workflow[node_id]["inputs"]["image"] = start_frame
            elif is_end and end_frame:
                workflow[node_id]["inputs"]["image"] = end_frame
            elif not is_end and start_frame:
                # Default to start frame if not explicitly end
                workflow[node_id]["inputs"]["image"] = start_frame

    return workflow


def update_workflow_params(
    workflow: dict,
    num_frames: int = None,
    steps: int = None,
    cfg: float = None,
    seed: int = None,
    width: int = None,
    height: int = None,
) -> dict:
    """Update generation parameters in workflow."""
    # Node classes that accept these parameters
    sampler_classes = [
        "WanImageToVideo",
        "WanFirstLastFrameToVideo",
        "WanVideoSampler",
        "KSampler",
        "KSamplerAdvanced",
    ]

    encode_classes = [
        "WanVideoImageToVideoEncode",
    ]

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # Update sampler nodes
        if class_type in sampler_classes:
            if num_frames is not None and "num_frames" in inputs:
                workflow[node_id]["inputs"]["num_frames"] = num_frames
            if steps is not None and "steps" in inputs:
                workflow[node_id]["inputs"]["steps"] = steps
            if cfg is not None and "cfg" in inputs:
                workflow[node_id]["inputs"]["cfg"] = cfg
            if seed is not None and seed > 0 and "seed" in inputs:
                workflow[node_id]["inputs"]["seed"] = seed

        # Update encode nodes (for resolution)
        if class_type in encode_classes:
            if width is not None and "width" in inputs:
                workflow[node_id]["inputs"]["width"] = width
            if height is not None and "height" in inputs:
                workflow[node_id]["inputs"]["height"] = height
            if num_frames is not None and "num_frames" in inputs:
                workflow[node_id]["inputs"]["num_frames"] = num_frames

        # Update native WAN nodes that have width/height
        if class_type in ["WanImageToVideo", "WanFirstLastFrameToVideo"]:
            if width is not None and "width" in inputs:
                workflow[node_id]["inputs"]["width"] = width
            if height is not None and "height" in inputs:
                workflow[node_id]["inputs"]["height"] = height

    return workflow


def generate_video(
    prompt: str,
    output_path: str,
    start_frame: str | None = None,
    end_frame: str | None = None,
    style_ref: str | None = None,
    num_frames: int = 81,
    steps: int = 20,
    cfg: float = 5.0,
    seed: int = 0,
    width: int = None,
    height: int = None,
    resolution_preset: str = None,
    timeout: int = 900,
    workflow_path: str = None,
) -> str:
    """
    Generate a video using WAN 2.2 GGUF via ComfyUI.

    Args:
        prompt: Text prompt describing the video content/motion
        output_path: Path to save the generated video
        start_frame: Optional path to starting frame image
        end_frame: Optional path to ending frame image
        style_ref: Optional path to style configuration JSON
        num_frames: Number of frames to generate (default 81 = ~5 seconds at 16fps)
        steps: Number of sampling steps
        cfg: Classifier-free guidance scale
        seed: Random seed (0 for random)
        width: Video width (overrides preset)
        height: Video height (overrides preset)
        resolution_preset: Resolution preset ("low", "medium", "high")
        timeout: Maximum time to wait for generation
        workflow_path: Custom workflow file path

    Returns:
        Path to saved video
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
        if width is None:
            width = preset["width"]
        if height is None:
            height = preset["height"]
        if num_frames == 81:  # Default value, override with preset
            num_frames = preset["num_frames"]
        print_status(f"Using '{resolution_preset}' preset: {width}x{height}, {num_frames} frames")

    # Determine mode based on inputs
    if workflow_path:
        mode = "custom"
        workflow_file = Path(workflow_path)
        print_status(f"Mode: Custom workflow")
    elif start_frame and end_frame:
        mode = "flf2v"
        workflow_file = FLF2V_WORKFLOW
        print_status("Mode: First-Last-Frame (FLF2V)")
    elif start_frame:
        mode = "i2v"
        workflow_file = I2V_WORKFLOW
        print_status("Mode: Image-to-Video (I2V)")
    elif end_frame:
        # If only end frame provided, treat as start frame for I2V
        mode = "i2v"
        start_frame = end_frame
        end_frame = None
        workflow_file = I2V_WORKFLOW
        print_status("Mode: Image-to-Video (I2V) - using end frame as start")
    else:
        print_status("Error: At least one frame (start_frame) is required", "error")
        print_status("Text-to-video without frames is not yet supported in this workflow", "error")
        sys.exit(1)

    # Validate frame files exist
    if start_frame and not Path(start_frame).exists():
        print_status(f"Start frame not found: {start_frame}", "error")
        sys.exit(1)
    if end_frame and not Path(end_frame).exists():
        print_status(f"End frame not found: {end_frame}", "error")
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
        print_status("Please ensure WAN workflows are set up correctly.", "error")
        sys.exit(1)

    try:
        workflow = load_workflow(str(workflow_file))
    except json.JSONDecodeError as e:
        print_status(f"Invalid workflow JSON: {e}", "error")
        sys.exit(1)

    # Upload images
    print_status("Uploading frames to ComfyUI...", "progress")

    start_frame_name = None
    end_frame_name = None

    if start_frame:
        try:
            result = client.upload_image(start_frame)
            start_frame_name = result["name"]
            print_status(f"Uploaded start frame: {start_frame_name}")
        except Exception as e:
            print_status(f"Failed to upload start frame: {e}", "error")
            sys.exit(1)

    if end_frame:
        try:
            result = client.upload_image(end_frame)
            end_frame_name = result["name"]
            print_status(f"Uploaded end frame: {end_frame_name}")
        except Exception as e:
            print_status(f"Failed to upload end frame: {e}", "error")
            sys.exit(1)

    # Update workflow
    workflow = update_workflow_prompts(workflow, enhanced_prompt)
    workflow = update_workflow_images(workflow, start_frame_name, end_frame_name)
    workflow = update_workflow_params(
        workflow,
        num_frames=num_frames,
        steps=steps,
        cfg=cfg,
        seed=seed,
        width=width,
        height=height,
    )

    # Execute workflow
    print_status("Submitting video generation request...", "progress")
    print_status(f"Settings: {num_frames} frames, {steps} steps, CFG {cfg}")
    if width and height:
        print_status(f"Resolution: {width}x{height}")

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

        # Get output videos
        videos = client.get_output_videos(result)

        if not videos:
            # Try getting as images (some workflows output as image sequence)
            images = client.get_output_images(result)
            if images:
                print_status("Output is image sequence, video file may be in ComfyUI output folder", "warning")
            else:
                print_status("No video generated!", "error")
                sys.exit(1)

        if videos:
            # Download and save the video
            output = ensure_output_dir(output_path)

            video_info = videos[0]
            client.download_output(video_info, str(output))

            total_time = time.time() - start_time
            print_status(f"Video saved to: {output_path} ({format_duration(total_time)})", "success")
            return str(output)
        else:
            # Check if video was saved directly by ComfyUI
            print_status("Video may have been saved directly to ComfyUI output folder", "warning")
            print_status(f"Check: ComfyUI/output/", "warning")
            return output_path

    except WorkflowValidationError as e:
        print_status(f"Workflow validation failed:", "error")
        print(str(e))
        sys.exit(1)
    except ComfyUIError as e:
        print_status(f"ComfyUI error:", "error")
        print(str(e))
        sys.exit(1)
    except TimeoutError:
        print_status(f"Generation timed out after {timeout}s", "error")
        print_status("Try reducing resolution or number of frames", "error")
        sys.exit(1)
    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate videos using WAN 2.2 GGUF via ComfyUI"
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
        "--num-frames", "-n",
        type=int,
        default=81,
        help="Number of frames to generate (default: 81 = ~5s at 16fps)"
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
        default=5.0,
        help="CFG scale (default: 5.0, use 5.5 for FLF2V)"
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
        help="Video width (default: from preset or workflow)"
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Video height (default: from preset or workflow)"
    )
    parser.add_argument(
        "--preset",
        choices=["low", "medium", "high"],
        default="medium",
        help="Resolution preset (default: medium = 832x480)"
    )
    parser.add_argument(
        "--workflow",
        help="Custom workflow JSON file path"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Maximum time to wait in seconds (default: 900 = 15 min)"
    )

    args = parser.parse_args()

    # Auto-adjust CFG for FLF2V mode
    cfg = args.cfg
    if args.start_frame and args.end_frame and args.cfg == 5.0:
        cfg = 5.5  # Recommended for FLF2V
        print_status("Auto-adjusted CFG to 5.5 for FLF2V mode")

    generate_video(
        prompt=args.prompt,
        output_path=args.output,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        style_ref=args.style_ref,
        num_frames=args.num_frames,
        steps=args.steps,
        cfg=cfg,
        seed=args.seed,
        width=args.width,
        height=args.height,
        resolution_preset=args.preset,
        timeout=args.timeout,
        workflow_path=args.workflow,
    )


if __name__ == "__main__":
    main()
