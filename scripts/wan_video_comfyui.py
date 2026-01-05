#!/usr/bin/env python3
"""
Generate videos using WAN 2.2 with LightX2V distillation via ComfyUI.
Supports single-frame (I2V) and dual-frame (FLF2V) generation modes.

Uses native ComfyUI nodes with LightX2V distillation LoRA for fast 8-step generation.

Includes automatic color correction to fix WAN's color drift issue where
saturation increases over time during video generation.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

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
I2V_WORKFLOW = WORKFLOW_DIR / "wan_i2v.json"
I2V_WORKFLOW_Q6K = WORKFLOW_DIR / "wan_i2v_q6k.json"  # Q6K without LoRA (deprecated)
I2V_WORKFLOW_MOE = WORKFLOW_DIR / "wan_i2v_moe.json"  # WAN 2.2 MoE (HighNoise + LowNoise)
FLF2V_WORKFLOW = WORKFLOW_DIR / "wan_flf2v.json"

# Resolution presets for different VRAM levels
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384, "length": 49},     # ~8GB VRAM
    "medium": {"width": 832, "height": 480, "length": 81},  # ~10GB VRAM
    "high": {"width": 1280, "height": 720, "length": 81},   # ~16GB+ VRAM
}


def match_histogram_lab(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """
    Match the color histogram of source image to reference image using LAB color space.

    This fixes WAN's color drift issue where saturation increases over time.

    Args:
        source: Source image (BGR format from OpenCV)
        reference: Reference image to match colors to (BGR format)

    Returns:
        Color-corrected image (BGR format)
    """
    # Convert to LAB color space for perceptually uniform matching
    src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
    ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype(np.float32)

    # Match each channel independently
    result = np.zeros_like(src_lab)
    for i in range(3):
        src_mean, src_std = src_lab[:, :, i].mean(), src_lab[:, :, i].std()
        ref_mean, ref_std = ref_lab[:, :, i].mean(), ref_lab[:, :, i].std()

        # Normalize source to reference distribution
        # Avoid division by zero
        if src_std > 1e-6:
            result[:, :, i] = (src_lab[:, :, i] - src_mean) * (ref_std / src_std) + ref_mean
        else:
            result[:, :, i] = src_lab[:, :, i]

    # Clip to valid range and convert back to BGR
    result = np.clip(result, 0, 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_LAB2BGR)


def correct_video_colors(
    video_path: str,
    reference_image_path: str,
    output_path: str = None,
    fps: float = 16.0,
) -> str:
    """
    Apply color correction to a video using a reference image.

    Fixes WAN's color drift by matching each frame's color histogram
    to the reference image (typically the start frame).

    Args:
        video_path: Path to input video
        reference_image_path: Path to reference image for color matching
        output_path: Output path (defaults to overwriting input)
        fps: Frame rate for output video

    Returns:
        Path to corrected video
    """
    if output_path is None:
        output_path = video_path

    # Load reference image
    reference = cv2.imread(reference_image_path)
    if reference is None:
        print_status(f"Failed to load reference image: {reference_image_path}", "error")
        return video_path

    # Open input video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print_status(f"Failed to open video: {video_path}", "error")
        return video_path

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    if original_fps > 0:
        fps = original_fps

    # Resize reference to match video dimensions if needed
    if reference.shape[:2] != (height, width):
        reference = cv2.resize(reference, (width, height), interpolation=cv2.INTER_LANCZOS4)

    # Create temporary output file
    temp_output = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False).name

    # Initialize video writer with H.264 codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))

    if not writer.isOpened():
        print_status("Failed to create video writer", "error")
        cap.release()
        return video_path

    # Process each frame
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Apply color correction
        corrected = match_histogram_lab(frame, reference)
        writer.write(corrected)
        frame_count += 1

    # Cleanup
    cap.release()
    writer.release()

    # Replace original with corrected version
    # Use shutil.move instead of os.rename for cross-drive support on Windows
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(temp_output, output_path)
    except Exception as e:
        print_status(f"Failed to save corrected video: {e}", "error")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return video_path

    return output_path


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

            if "{{PROMPT}}" in current_text or "positive" in title:
                workflow[node_id]["inputs"]["text"] = prompt
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

            is_start = any(x in title for x in ["first", "start"]) or "{{START_FRAME}}" in current_image
            is_end = any(x in title for x in ["last", "end"]) or "{{END_FRAME}}" in current_image

            if is_start and start_frame:
                workflow[node_id]["inputs"]["image"] = start_frame
            elif is_end and end_frame:
                workflow[node_id]["inputs"]["image"] = end_frame
            elif not is_end and start_frame:
                workflow[node_id]["inputs"]["image"] = start_frame

    return workflow


def update_workflow_resolution(
    workflow: dict,
    width: int = None,
    height: int = None,
    length: int = None,
) -> dict:
    """Update resolution parameters in workflow."""

    resolution_nodes = [
        "ImageScale",
        "WanImageToVideo",
        "WanFirstLastFrameToVideo",
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
            if length is not None and "length" in inputs:
                workflow[node_id]["inputs"]["length"] = length

    return workflow


def update_workflow_sampler(
    workflow: dict,
    steps: int = None,
    cfg: float = None,
    seed: int = None,
) -> dict:
    """Update sampler parameters in workflow."""

    sampler_classes = ["KSampler", "KSamplerAdvanced"]

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type in sampler_classes:
            if steps is not None and "steps" in inputs:
                workflow[node_id]["inputs"]["steps"] = steps
            if cfg is not None and "cfg" in inputs:
                workflow[node_id]["inputs"]["cfg"] = cfg
            if seed is not None and seed > 0 and "seed" in inputs:
                workflow[node_id]["inputs"]["seed"] = seed

    return workflow


def update_workflow_lora(
    workflow: dict,
    lora_strength: float = None,
) -> dict:
    """Update LoRA strength in workflow."""

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type == "LoraLoader":
            if lora_strength is not None:
                workflow[node_id]["inputs"]["strength_model"] = lora_strength
                workflow[node_id]["inputs"]["strength_clip"] = lora_strength

    return workflow


def generate_video(
    prompt: str,
    output_path: str,
    start_frame: str | None = None,
    end_frame: str | None = None,
    style_ref: str | None = None,
    length: int = 81,
    steps: int = 8,
    cfg: float = 1.0,
    seed: int = 0,
    width: int = None,
    height: int = None,
    resolution_preset: str = None,
    lora_strength: float = 1.25,
    timeout: int = 600,
    workflow_path: str = None,
    free_memory: bool = False,
    color_correct: bool = True,
    use_q6k: bool = False,
    use_moe: bool = False,
) -> str:
    """
    Generate a video using WAN 2.2 with LightX2V distillation via ComfyUI.

    Args:
        prompt: Text prompt describing the video content/motion
        output_path: Path to save the generated video
        start_frame: Optional path to starting frame image
        end_frame: Optional path to ending frame image
        style_ref: Optional path to style configuration JSON
        length: Number of frames to generate (default 81 = ~5 seconds at 16fps)
        steps: Number of sampling steps (default 8 with LightX2V distillation)
        cfg: Classifier-free guidance scale (default 1.0 with LightX2V LoRA)
        seed: Random seed (0 for random)
        width: Video width (overrides preset)
        height: Video height (overrides preset)
        resolution_preset: Resolution preset ("low", "medium", "high")
        lora_strength: LightX2V LoRA strength (default 1.25 for I2V)
        timeout: Maximum time to wait for generation
        workflow_path: Custom workflow file path

    Returns:
        Path to saved video
    """
    # Initialize client
    client = ComfyUIClient()

    if not client.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python scripts/setup_comfyui.py --start", "error")
        sys.exit(1)

    # Free memory if requested (useful when switching from Qwen to WAN)
    if free_memory:
        print_status("Freeing GPU memory before generation...", "*")
        client.free_memory()

    # Apply resolution preset if specified
    if resolution_preset and resolution_preset in RESOLUTION_PRESETS:
        preset = RESOLUTION_PRESETS[resolution_preset]
        if width is None:
            width = preset["width"]
        if height is None:
            height = preset["height"]
        if length == 81:
            length = preset["length"]
        print_status(f"Using '{resolution_preset}' preset: {width}x{height}, {length} frames")

    # Determine mode based on inputs
    if workflow_path:
        mode = "custom"
        workflow_file = Path(workflow_path)
        print_status(f"Mode: Custom workflow")
    elif start_frame and end_frame:
        mode = "flf2v"
        workflow_file = FLF2V_WORKFLOW
        print_status("Mode: First-Last-Frame (FLF2V) - 8-step LightX2V")
    elif start_frame:
        mode = "i2v"
        if use_moe:
            workflow_file = I2V_WORKFLOW_MOE
            print_status("Mode: Image-to-Video (I2V) - WAN 2.2 MoE (HighNoise + LowNoise, 20 steps)")
        elif use_q6k:
            workflow_file = I2V_WORKFLOW_Q6K
            print_status("Mode: Image-to-Video (I2V) - WAN 2.2 Q6_K (30 steps, no LoRA) [deprecated]")
        else:
            workflow_file = I2V_WORKFLOW
            print_status("Mode: Image-to-Video (I2V) - 8-step LightX2V")
    elif end_frame:
        mode = "i2v"
        start_frame = end_frame
        end_frame = None
        if use_q6k:
            workflow_file = I2V_WORKFLOW_Q6K
            print_status("Mode: Image-to-Video (I2V) - WAN 2.2 Q6_K (using end frame as start)")
        else:
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
    workflow = update_workflow_resolution(workflow, width, height, length)
    workflow = update_workflow_sampler(workflow, steps, cfg, seed)
    
    # Skip LoRA update for Q6K/MoE modes (no LoRA in workflow)
    if not use_q6k and not use_moe:
        workflow = update_workflow_lora(workflow, lora_strength)

    # Execute workflow
    print_status("Submitting video generation request...", "progress")
    if use_moe:
        print_status(f"Settings: {length} frames, 20 steps, CFG 4.0/3.0, WAN 2.2 MoE (HighNoise + LowNoise)")
    elif use_q6k:
        print_status(f"Settings: {length} frames, {steps} steps, CFG {cfg}, WAN 2.2 Q6_K (no LoRA)")
    else:
        print_status(f"Settings: {length} frames, {steps} steps, CFG {cfg}, LoRA {lora_strength}")
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
            images = client.get_output_images(result)
            if images:
                print_status("Output is image sequence, video file may be in ComfyUI output folder", "warning")
            else:
                print_status("No video generated!", "error")
                sys.exit(1)

        if videos:
            output = ensure_output_dir(output_path)

            video_info = videos[0]
            client.download_output(video_info, str(output))

            # Apply color correction to fix WAN's color drift
            if color_correct and start_frame:
                print_status("Applying color correction...", "progress")
                correct_video_colors(str(output), start_frame)
                print_status("Color correction applied", "success")

            total_time = time.time() - start_time
            print_status(f"Video saved to: {output_path} ({format_duration(total_time)})", "success")
            return str(output)
        else:
            print_status("Video may have been saved directly to ComfyUI output folder", "warning")
            print_status(f"Check: comfyui/output/", "warning")
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
        description="Generate videos using WAN 2.2 with LightX2V distillation via ComfyUI"
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
        "--lora-strength",
        type=float,
        default=1.25,
        help="LightX2V LoRA strength (default: 1.25 for I2V)"
    )
    parser.add_argument(
        "--q6k",
        action="store_true",
        help="(Deprecated) Use single Q6K model - use --moe instead"
    )
    parser.add_argument(
        "--moe",
        action="store_true",
        help="Use WAN 2.2 MoE (HighNoise + LowNoise experts, 20 steps, best quality)"
    )
    parser.add_argument(
        "--workflow",
        help="Custom workflow JSON file path"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Maximum time to wait in seconds (default: 600 = 10 min)"
    )
    parser.add_argument(
        "--free-memory",
        action="store_true",
        help="Free GPU memory before generation (useful when switching from Qwen image)"
    )
    parser.add_argument(
        "--no-color-correct",
        action="store_true",
        help="Disable automatic color correction (fixes WAN's color drift issue)"
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
        timeout=args.timeout,
        workflow_path=args.workflow,
        free_memory=args.free_memory,
        color_correct=not args.no_color_correct,
        use_q6k=args.q6k,
        use_moe=args.moe,
    )


if __name__ == "__main__":
    main()
