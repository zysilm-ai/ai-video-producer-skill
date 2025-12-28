#!/usr/bin/env python3
"""
Generate videos using Google Veo API.
Supports single-frame and dual-frame generation modes.
"""

import argparse
import sys
import time
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai package not installed", file=sys.stderr)
    print("Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

from utils import (
    get_api_key,
    load_style_config,
    ensure_output_dir,
    print_status,
    format_duration,
    build_enhanced_prompt,
)


def generate_video(
    prompt: str,
    output_path: str,
    start_frame: str | None = None,
    end_frame: str | None = None,
    style_ref: str | None = None,
    duration: int = 8,
    resolution: str = "720p",
    generate_audio: bool = True,
    model: str = "veo-3.1-generate-preview",
    poll_interval: int = 10,
    max_wait: int = 600,
) -> str:
    """
    Generate a video using Veo API.

    Args:
        prompt: Text prompt describing the video content/motion
        output_path: Path to save the generated video
        start_frame: Optional path to starting frame image
        end_frame: Optional path to ending frame image
        style_ref: Optional path to style configuration JSON
        duration: Video duration in seconds (max 8)
        resolution: Video resolution (720p or 1080p)
        generate_audio: Whether to generate synchronized audio
        model: Veo model to use
        poll_interval: Seconds between status polls
        max_wait: Maximum seconds to wait for generation

    Returns:
        Path to saved video
    """
    # Initialize client
    client = genai.Client(api_key=get_api_key())

    # Validate frame configuration
    mode = "text-to-video"
    if start_frame and end_frame:
        mode = "dual-frame"
        print_status(f"Mode: Dual-frame (start + end)")
    elif start_frame:
        mode = "single-frame-start"
        print_status(f"Mode: Single-frame (start frame)")
    elif end_frame:
        mode = "single-frame-end"
        print_status(f"Mode: Single-frame (end frame)")
    else:
        print_status(f"Mode: Text-to-video (no reference frames)")

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

    # Build generation config
    video_config_params = {
        "number_of_videos": 1,
        "duration_seconds": min(duration, 8),
    }

    # Prepare image parameter for start frame
    start_img = None
    if start_frame:
        start_img = types.Image.from_file(location=start_frame)
        print_status(f"Start frame: {start_frame}")

    # Add end frame to config if provided
    if end_frame:
        end_img = types.Image.from_file(location=end_frame)
        video_config_params["last_frame"] = end_img
        print_status(f"End frame: {end_frame}")

    # Start generation
    print_status("Submitting video generation request...", "progress")
    start_time = time.time()

    try:
        # Submit async generation job
        operation = client.models.generate_videos(
            model=model,
            prompt=enhanced_prompt,
            image=start_img,
            config=types.GenerateVideosConfig(**video_config_params)
        )

        print_status(f"Job submitted. Waiting for completion...", "progress")

        # Poll for completion
        elapsed = 0
        while not operation.done and elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed = time.time() - start_time

            # Refresh operation status
            operation = client.operations.get(operation)

            state = operation.metadata.get('state', 'processing') if operation.metadata else 'processing'
            status_msg = f"Status: {state} ({format_duration(elapsed)})"
            print_status(status_msg, "progress")

        if not operation.done:
            print_status(f"Timeout after {format_duration(max_wait)}", "error")
            sys.exit(1)

        # Check for errors
        if operation.error:
            print_status(f"Generation failed: {operation.error.message}", "error")
            sys.exit(1)

        # Save generated video
        output = ensure_output_dir(output_path)

        result = operation.result
        if hasattr(result, 'generated_videos') and result.generated_videos:
            generated_video = result.generated_videos[0]

            # Download and save video content
            client.files.download(file=generated_video.video)
            generated_video.video.save(str(output))

            total_time = time.time() - start_time
            print_status(f"Video saved to: {output_path} ({format_duration(total_time)})", "success")
            return str(output)
        else:
            print_status("No video in response", "error")
            sys.exit(1)

    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate videos using Veo API"
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
        help="Path to starting frame image (optional)"
    )
    parser.add_argument(
        "--end-frame", "-e",
        help="Path to ending frame image (optional)"
    )
    parser.add_argument(
        "--style-ref",
        help="Path to style configuration JSON file"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=8,
        choices=range(1, 9),
        help="Video duration in seconds (1-8, default: 8)"
    )
    parser.add_argument(
        "--resolution", "-r",
        default="720p",
        choices=["720p", "1080p"],
        help="Video resolution (default: 720p)"
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Disable audio generation"
    )
    parser.add_argument(
        "--model", "-m",
        default="veo-3.1-generate-preview",
        help="Veo model to use"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between status polls (default: 10)"
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=600,
        help="Maximum seconds to wait for generation (default: 600)"
    )

    args = parser.parse_args()

    generate_video(
        prompt=args.prompt,
        output_path=args.output,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        style_ref=args.style_ref,
        duration=args.duration,
        resolution=args.resolution,
        generate_audio=not args.no_audio,
        model=args.model,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
    )


if __name__ == "__main__":
    main()
