#!/usr/bin/env python3
"""
Keyframe Generator for AI Video Producer.

Generates keyframe images using character reference images.
This script properly separates:
- Character IDENTITY from reference images (WHO)
- Action/context from text prompt (WHAT is happening)

Usage:
    # Single character
    python keyframe_generator.py \\
        --prompt "Athena in fighting stance, fists raised" \\
        --character assets/characters/athena.png \\
        --output keyframes/KF-A.png

    # Multi-character scene
    python keyframe_generator.py \\
        --prompt "Athena blocking, Iori attacking with flames" \\
        --character assets/characters/athena.png \\
        --character assets/characters/iori.png \\
        --output keyframes/KF-B.png

    # With background
    python keyframe_generator.py \\
        --prompt "Athena standing in ancient temple" \\
        --character assets/characters/athena.png \\
        --background assets/backgrounds/temple.png \\
        --output keyframes/KF-C.png
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from core import (
    QwenImageGenerator,
    REFERENCE_WORKFLOW,
    RESOLUTION_PRESETS,
    print_status,
)
from utils import ensure_output_dir, load_style_config


def generate_keyframe(
    prompt: str,
    output_path: str,
    characters: List[str],
    background: str = None,
    style: str = None,
    resolution_preset: str = "medium",
    seed: int = 0,
    free_memory: bool = False,
) -> str:
    """
    Generate a keyframe using character reference images.

    This function integrates:
    - Character identity from reference images (WHO)
    - Scene context from prompt (WHAT is happening)

    Args:
        prompt: Action/scene description (WHAT is happening)
        output_path: Path to save generated keyframe
        characters: List of character identity asset paths (1-3)
        background: Optional background reference image
        style: Optional path to style.json configuration
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

    # Determine reference slot allocation strategy
    # Supports up to 3 reference images:
    #   - If background provided: image1=background, image2=char1, image3=char2
    #   - If no background: image1=char1, image2=char2, image3=char3
    if background:
        ref1 = background
        ref2 = characters[0] if len(characters) >= 1 else None
        ref3 = characters[1] if len(characters) >= 2 else None
        print_status("Reference allocation: background + characters")
        print_status(f"  image1 (background): {background}")
        if ref2:
            print_status(f"  image2 (character 1): {ref2}")
        if ref3:
            print_status(f"  image3 (character 2): {ref3}")
        if len(characters) > 2:
            print_status(f"Warning: Only 2 characters supported with background (ignoring {len(characters)-2})", "warning")
    else:
        ref1 = characters[0] if len(characters) >= 1 else None
        ref2 = characters[1] if len(characters) >= 2 else None
        ref3 = characters[2] if len(characters) >= 3 else None
        print_status("Reference allocation: characters only")
        if ref1:
            print_status(f"  image1 (character 1): {ref1}")
        if ref2:
            print_status(f"  image2 (character 2): {ref2}")
        if ref3:
            print_status(f"  image3 (character 3): {ref3}")

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

    # Use reference workflow for keyframe generation
    workflow_path = REFERENCE_WORKFLOW
    print_status("Mode: Reference-based keyframe generation")

    result = generator.generate(
        prompt=enhanced_prompt,
        output_path=output_path,
        workflow_path=workflow_path,
        reference_image=ref1,
        reference_image2=ref2,
        reference_image3=ref3,
        seed=seed,
        style_config=style_config,
        free_memory=False,  # Already handled above
    )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate keyframe images using character reference images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single character
  python keyframe_generator.py \\
    --prompt "Athena in fighting stance" \\
    --character assets/characters/athena.png \\
    --output keyframes/KF-A.png

  # With background
  python keyframe_generator.py \\
    --prompt "Athena standing in ancient temple" \\
    --character assets/characters/athena.png \\
    --background assets/backgrounds/temple.png \\
    --output keyframes/KF-B.png

  # Multi-character scene
  python keyframe_generator.py \\
    --prompt "On the left: Athena blocking. On the right: Iori attacking" \\
    -c assets/characters/athena.png \\
    -c assets/characters/iori.png \\
    --output keyframes/KF-C.png
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

    generate_keyframe(
        prompt=args.prompt,
        output_path=args.output,
        characters=args.characters,
        background=args.background,
        style=args.style,
        resolution_preset=args.preset,
        seed=args.seed,
        free_memory=args.free_memory,
    )


if __name__ == "__main__":
    main()
