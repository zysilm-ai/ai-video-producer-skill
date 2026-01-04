#!/usr/bin/env python3
"""
Keyframe Generator for AI Video Producer.

Generates keyframe images using character assets and pose control.
This script properly separates:
- Character IDENTITY from reference images (WHO)
- Character POSE from skeleton images (WHAT position)
- Action/context from text prompt (WHAT is happening)

Usage:
    # Single character with pre-extracted skeleton
    python keyframe_generator.py \\
        --prompt "Athena in fighting stance, fists raised" \\
        --character assets/characters/athena.png \\
        --pose assets/poses/fighting_stance_skeleton.png \\
        --output keyframes/KF-A.png

    # Extract skeleton on-the-fly from reference image
    python keyframe_generator.py \\
        --prompt "Athena collapsed on ground" \\
        --character assets/characters/athena.png \\
        --pose-image references/collapse_photo.jpg \\
        --output keyframes/KF-D.png

    # Multi-character scene
    python keyframe_generator.py \\
        --prompt "Athena blocking, Iori attacking with flames" \\
        --character assets/characters/athena.png \\
        --character assets/characters/iori.png \\
        --pose assets/poses/combat_skeleton.png \\
        --output keyframes/KF-B.png
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from core import (
    QwenImageGenerator,
    extract_pose_skeleton,
    T2I_WORKFLOW,
    EDIT_WORKFLOW,
    POSE_WORKFLOW,
    RESOLUTION_PRESETS,
    print_status,
)
from utils import ensure_output_dir, load_style_config


def generate_keyframe(
    prompt: str,
    output_path: str,
    characters: List[str],
    pose_skeleton: str = None,
    pose_image: str = None,
    background: str = None,
    style: str = None,
    control_strength: float = 0.8,
    resolution_preset: str = "medium",
    seed: int = 0,
    free_memory: bool = False,
) -> str:
    """
    Generate a keyframe using character assets and pose control.

    This function properly integrates:
    - Character identity from reference images
    - Pose from skeleton (extracted via DWPose)
    - Scene context from prompt

    Args:
        prompt: Action/scene description (WHAT is happening)
        output_path: Path to save generated keyframe
        characters: List of character identity asset paths (1-3)
        pose_skeleton: Path to pre-extracted pose skeleton image
        pose_image: Path to image to extract pose from (alternative to pose_skeleton)
        background: Optional background reference image
        style: Optional path to style.json configuration
        control_strength: ControlNet strength for pose (0.0-1.0)
        resolution_preset: Resolution preset (low, medium, high)
        seed: Random seed (0 for random)
        free_memory: Free GPU memory before generation

    Returns:
        Path to saved keyframe
    """
    # Validate inputs
    if not characters:
        print_status("At least one character reference is required", "error")
        sys.exit(1)

    if len(characters) > 3:
        print_status("Maximum 3 character references supported", "error")
        sys.exit(1)

    for char_path in characters:
        if not Path(char_path).exists():
            print_status(f"Character asset not found: {char_path}", "error")
            sys.exit(1)

    # Handle pose: either use provided skeleton or extract from image
    skeleton_path = pose_skeleton
    temp_skeleton = None

    if pose_image and not pose_skeleton:
        if not Path(pose_image).exists():
            print_status(f"Pose image not found: {pose_image}", "error")
            sys.exit(1)

        # Extract skeleton to temp file
        print_status("Extracting pose skeleton from reference image...")
        temp_skeleton = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        skeleton_path = extract_pose_skeleton(
            image_path=pose_image,
            output_path=temp_skeleton.name,
        )

    elif pose_skeleton:
        if not Path(pose_skeleton).exists():
            print_status(f"Pose skeleton not found: {pose_skeleton}", "error")
            sys.exit(1)

    # Validate background if provided
    if background and not Path(background).exists():
        print_status(f"Background not found: {background}", "error")
        sys.exit(1)

    # Load style config if provided
    style_config = None
    if style:
        try:
            style_config = load_style_config(style)
            print_status(f"Loaded style config: {style}")
        except FileNotFoundError:
            print_status(f"Style config not found: {style}", "warning")

    # Initialize generator
    generator = QwenImageGenerator(resolution_preset=resolution_preset)

    if not generator.is_available():
        print_status("ComfyUI server not available!", "error")
        print_status("Please start ComfyUI: python scripts/setup_comfyui.py --start", "error")
        sys.exit(1)

    if free_memory:
        generator.free_memory()

    # Determine workflow and reference strategy
    primary_character = characters[0]

    # Build enhanced prompt with character context
    char_names = [Path(c).stem for c in characters]
    if len(characters) > 1:
        # Multi-character: include positioning hints in prompt
        enhanced_prompt = prompt
        if "left" not in prompt.lower() and "right" not in prompt.lower():
            # Add default positioning if not specified
            enhanced_prompt = f"Multiple characters in scene. {prompt}"
    else:
        enhanced_prompt = prompt

    # Choose workflow based on inputs
    if skeleton_path:
        # Use pose workflow with ControlNet
        workflow_path = POSE_WORKFLOW
        print_status("Mode: Pose-controlled keyframe generation")
        print_status(f"Character identity: {primary_character}")
        print_status(f"Pose skeleton: {skeleton_path}")

        result = generator.generate(
            prompt=enhanced_prompt,
            output_path=output_path,
            workflow_path=workflow_path,
            reference_image=primary_character,
            pose_image=skeleton_path,
            control_strength=control_strength,
            seed=seed,
            style_config=style_config,
            free_memory=False,  # Already handled above
        )
    else:
        # Use edit workflow with just character reference
        workflow_path = EDIT_WORKFLOW
        print_status("Mode: Reference-guided keyframe generation (no pose control)")
        print_status(f"Character identity: {primary_character}")

        result = generator.generate(
            prompt=enhanced_prompt,
            output_path=output_path,
            workflow_path=workflow_path,
            reference_image=primary_character,
            seed=seed,
            style_config=style_config,
            free_memory=False,
        )

    # Cleanup temp skeleton if created
    if temp_skeleton:
        try:
            Path(temp_skeleton.name).unlink()
        except Exception:
            pass

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate keyframe images using character assets and pose control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single character with skeleton
  python keyframe_generator.py \\
    --prompt "Athena in fighting stance" \\
    --character assets/characters/athena.png \\
    --pose assets/poses/stance_skeleton.png \\
    --output keyframes/KF-A.png

  # Extract pose from reference image
  python keyframe_generator.py \\
    --prompt "Athena collapsed" \\
    --character assets/characters/athena.png \\
    --pose-image refs/collapse.jpg \\
    --output keyframes/KF-D.png

  # Multi-character scene
  python keyframe_generator.py \\
    --prompt "On the left: Athena blocking. On the right: Iori attacking" \\
    -c assets/characters/athena.png \\
    -c assets/characters/iori.png \\
    --pose assets/poses/combat.png \\
    --output keyframes/KF-B.png
"""
    )

    # Required arguments
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Action/scene description (WHAT is happening)"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output path for generated keyframe"
    )
    parser.add_argument(
        "--character", "-c",
        action="append",
        required=True,
        dest="characters",
        help="Path to character identity asset (WHO). Can specify up to 3."
    )

    # Pose options (mutually exclusive preference)
    pose_group = parser.add_argument_group("Pose Control")
    pose_group.add_argument(
        "--pose",
        dest="pose_skeleton",
        help="Path to pre-extracted pose skeleton image (stick figure on black)"
    )
    pose_group.add_argument(
        "--pose-image",
        help="Path to reference image to extract pose from (will run DWPose)"
    )

    # Optional references
    ref_group = parser.add_argument_group("Optional References")
    ref_group.add_argument(
        "--background", "-b",
        help="Path to background reference image"
    )
    ref_group.add_argument(
        "--style", "-s",
        help="Path to style.json configuration file"
    )

    # Generation settings
    gen_group = parser.add_argument_group("Generation Settings")
    gen_group.add_argument(
        "--control-strength",
        type=float,
        default=0.8,
        help="ControlNet strength for pose guidance (default: 0.8)"
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
        help="Free GPU memory before generation (use when switching from video)"
    )

    args = parser.parse_args()

    # Validate pose arguments
    if args.pose_skeleton and args.pose_image:
        print_status("Specify either --pose (skeleton) or --pose-image, not both", "warning")
        print_status("Using --pose (pre-extracted skeleton)")

    generate_keyframe(
        prompt=args.prompt,
        output_path=args.output,
        characters=args.characters,
        pose_skeleton=args.pose_skeleton,
        pose_image=args.pose_image,
        background=args.background,
        style=args.style,
        control_strength=args.control_strength,
        resolution_preset=args.preset,
        seed=args.seed,
        free_memory=args.free_memory,
    )


if __name__ == "__main__":
    main()
