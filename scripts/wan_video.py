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

from comfyui_client import ComfyUIClient, load_workflow
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
    timeout: int = 600,
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
        timeout: Maximum time to wait for generation

    Returns:
        Path to saved video
    """
    # Initialize client
    client = ComfyUIClient()

    if not client.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python main.py --listen 0.0.0.0 --port 8188", "error")
        sys.exit(1)

    # Determine mode based on inputs
    if start_frame and end_frame:
        mode = "flf2v"
        print_status("Mode: First-Last-Frame (FLF2V)")
        workflow_path = FLF2V_WORKFLOW
    elif start_frame:
        mode = "i2v"
        print_status("Mode: Image-to-Video (I2V)")
        workflow_path = I2V_WORKFLOW
    elif end_frame:
        # If only end frame provided, treat as start frame for I2V
        mode = "i2v"
        start_frame = end_frame
        end_frame = None
        print_status("Mode: Image-to-Video (I2V) - using end frame as start")
        workflow_path = I2V_WORKFLOW
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
    try:
        workflow = load_workflow(str(workflow_path))
    except FileNotFoundError:
        print_status(f"Workflow not found: {workflow_path}", "error")
        print_status("Please ensure WAN workflows are set up correctly.", "error")
        sys.exit(1)

    # Upload images and update workflow
    print_status("Uploading frames to ComfyUI...", "progress")

    start_frame_name = None
    end_frame_name = None

    if start_frame:
        result = client.upload_image(start_frame)
        start_frame_name = result["name"]
        print_status(f"Uploaded start frame: {start_frame_name}")

    if end_frame:
        result = client.upload_image(end_frame)
        end_frame_name = result["name"]
        print_status(f"Uploaded end frame: {end_frame_name}")

    # Update workflow parameters
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # Update prompt
        if class_type == "CLIPTextEncode":
            if inputs.get("text") == "{{PROMPT}}" or "positive" in node.get("_meta", {}).get("title", "").lower():
                workflow[node_id]["inputs"]["text"] = enhanced_prompt

        # Update start frame
        if class_type == "LoadImage":
            title = node.get("_meta", {}).get("title", "").lower()
            if "first" in title or "start" in title:
                if start_frame_name:
                    workflow[node_id]["inputs"]["image"] = start_frame_name
            elif "last" in title or "end" in title:
                if end_frame_name:
                    workflow[node_id]["inputs"]["image"] = end_frame_name
            elif start_frame_name and "{{START_FRAME}}" in str(inputs.get("image", "")):
                workflow[node_id]["inputs"]["image"] = start_frame_name
            elif end_frame_name and "{{END_FRAME}}" in str(inputs.get("image", "")):
                workflow[node_id]["inputs"]["image"] = end_frame_name

        # Update generation parameters
        if class_type in ["WanImageToVideo", "WanFirstLastFrameToVideo"]:
            workflow[node_id]["inputs"]["num_frames"] = num_frames
            workflow[node_id]["inputs"]["steps"] = steps
            workflow[node_id]["inputs"]["cfg"] = cfg
            if seed > 0:
                workflow[node_id]["inputs"]["seed"] = seed

        # Update KSampler if present
        if class_type == "KSampler":
            workflow[node_id]["inputs"]["steps"] = steps
            workflow[node_id]["inputs"]["cfg"] = cfg
            if seed > 0:
                workflow[node_id]["inputs"]["seed"] = seed

    # Execute workflow
    print_status("Submitting video generation request...", "progress")
    start_time = time.time()

    def on_progress(msg):
        elapsed = time.time() - start_time
        print_status(f"{msg} ({format_duration(elapsed)})", "progress")

    try:
        result = client.execute_workflow(
            workflow,
            timeout=timeout,
            on_progress=on_progress,
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

    except TimeoutError:
        print_status(f"Generation timed out after {timeout}s", "error")
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
        "--timeout",
        type=int,
        default=600,
        help="Maximum time to wait in seconds (default: 600)"
    )

    args = parser.parse_args()

    # Auto-adjust CFG for FLF2V mode
    cfg = args.cfg
    if args.start_frame and args.end_frame and args.cfg == 5.0:
        cfg = 5.5  # Recommended for FLF2V

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
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
