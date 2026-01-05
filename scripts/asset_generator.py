#!/usr/bin/env python3
"""
Asset Generator for AI Video Producer.

Generates reusable assets for keyframe generation:
- Character identity references (neutral pose, clean background)
- Background references
- Style references

These assets are used by keyframe_generator.py to create consistent keyframes.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from core import (
    QwenImageGenerator,
    T2I_WORKFLOW,
    RESOLUTION_PRESETS,
    print_status,
)
from utils import ensure_output_dir


# =============================================================================
# Asset Generation Functions
# =============================================================================

def generate_character_asset(
    generator: QwenImageGenerator,
    name: str,
    description: str,
    output_path: str,
    style: str = "anime",
    seed: int = 0,
) -> str:
    """
    Generate a character identity reference asset.

    Creates a clean character reference suitable for identity preservation:
    - Neutral A-pose or standing pose
    - Clean white/gray background
    - Full body visible
    - Flat, even lighting
    - No action or dynamic poses

    Args:
        generator: QwenImageGenerator instance
        name: Character name (for logging)
        description: Detailed character description (appearance, clothing, etc.)
        output_path: Path to save the asset
        style: Art style (anime, realistic, etc.)
        seed: Random seed for reproducibility

    Returns:
        Path to saved asset
    """
    # Build prompt for clean character reference
    prompt = (
        f"Character design sheet of {description}, "
        f"full body, neutral A-pose standing straight, arms slightly away from body, "
        f"facing front, neutral expression, "
        f"clean white background, flat even studio lighting, "
        f"character reference sheet, {style} art style, "
        f"high quality, detailed, no shadows on background"
    )

    print_status(f"Generating character asset: {name}")

    return generator.generate(
        prompt=prompt,
        output_path=output_path,
        workflow_path=T2I_WORKFLOW,
        seed=seed,
    )


def generate_background_asset(
    generator: QwenImageGenerator,
    name: str,
    description: str,
    output_path: str,
    camera_angle: str = "front view",
    style: str = "anime",
    seed: int = 0,
) -> str:
    """
    Generate a background/environment reference asset.

    Creates a clean environment reference:
    - No characters or people in scene
    - Establishes lighting direction
    - Shows environment details

    Args:
        generator: QwenImageGenerator instance
        name: Background name (for logging)
        description: Environment description
        output_path: Path to save the asset
        camera_angle: Camera angle description (front view, side angle, etc.)
        style: Art style
        seed: Random seed

    Returns:
        Path to saved asset
    """
    prompt = (
        f"{description}, "
        f"establishing shot, {camera_angle}, "
        f"no people, no characters, empty scene, "
        f"environment background, {style} art style, "
        f"high quality, detailed"
    )

    print_status(f"Generating background asset: {name}")

    return generator.generate(
        prompt=prompt,
        output_path=output_path,
        workflow_path=T2I_WORKFLOW,
        seed=seed,
    )


def generate_style_asset(
    generator: QwenImageGenerator,
    name: str,
    description: str,
    output_path: str,
    seed: int = 0,
) -> str:
    """
    Generate a style reference asset.

    Creates an example image that demonstrates the target visual style:
    - Color palette
    - Line work style
    - Shading approach
    - Overall aesthetic

    Args:
        generator: QwenImageGenerator instance
        name: Style name (for logging)
        description: Style description
        output_path: Path to save the asset
        seed: Random seed

    Returns:
        Path to saved asset
    """
    prompt = (
        f"Example scene demonstrating {description} art style, "
        f"showing characteristic color palette, line work, and shading, "
        f"high quality illustration, style reference"
    )

    print_status(f"Generating style asset: {name}")

    return generator.generate(
        prompt=prompt,
        output_path=output_path,
        workflow_path=T2I_WORKFLOW,
        seed=seed,
    )


# =============================================================================
# Batch Asset Generation
# =============================================================================

def generate_assets_from_config(
    config_path: str,
    output_dir: str,
    free_memory: bool = False,
) -> dict:
    """
    Generate all assets defined in an assets.json configuration file.

    Args:
        config_path: Path to assets.json configuration
        output_dir: Base output directory for assets
        free_memory: Free GPU memory before starting

    Returns:
        Dict mapping asset names to their generated paths
    """
    config_path = Path(config_path)
    if not config_path.exists():
        print_status(f"Config not found: {config_path}", "error")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    output_dir = Path(output_dir)
    results = {}

    # Initialize generator
    generator = QwenImageGenerator()

    if not generator.is_available():
        print_status("ComfyUI server not available!", "error")
        sys.exit(1)

    if free_memory:
        generator.free_memory()

    # Generate character assets
    characters = config.get("characters", {})
    for name, char_config in characters.items():
        char_output = output_dir / "characters" / f"{name}.png"
        ensure_output_dir(str(char_output))

        generate_character_asset(
            generator=generator,
            name=name,
            description=char_config.get("description", name),
            output_path=str(char_output),
        )
        results[f"character:{name}"] = str(char_output)

    # Generate background assets
    backgrounds = config.get("backgrounds", {})
    for name, bg_config in backgrounds.items():
        bg_output = output_dir / "backgrounds" / f"{name}.png"
        ensure_output_dir(str(bg_output))

        generate_background_asset(
            generator=generator,
            name=name,
            description=bg_config.get("description", name),
            output_path=str(bg_output),
        )
        results[f"background:{name}"] = str(bg_output)

    # Generate style assets
    styles = config.get("styles", {})
    for name, style_config in styles.items():
        style_output = output_dir / "styles" / f"{name}.png"
        ensure_output_dir(str(style_output))

        generate_style_asset(
            generator=generator,
            name=name,
            description=style_config.get("description", name),
            output_path=str(style_output),
        )
        results[f"style:{name}"] = str(style_output)

    print_status(f"Generated {len(results)} assets", "success")
    return results


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate assets for AI Video Producer keyframe generation"
    )

    subparsers = parser.add_subparsers(dest="command", help="Asset type to generate")

    # Character asset command
    char_parser = subparsers.add_parser("character", help="Generate character identity asset")
    char_parser.add_argument("--name", "-n", required=True, help="Character name")
    char_parser.add_argument("--description", "-d", required=True, help="Character description")
    char_parser.add_argument("--output", "-o", required=True, help="Output path")
    char_parser.add_argument("--style", default="anime", help="Art style (default: anime)")
    char_parser.add_argument("--seed", type=int, default=0, help="Random seed")
    char_parser.add_argument("--free-memory", action="store_true", help="Free GPU memory first")

    # Background asset command
    bg_parser = subparsers.add_parser("background", help="Generate background asset")
    bg_parser.add_argument("--name", "-n", required=True, help="Background name")
    bg_parser.add_argument("--description", "-d", required=True, help="Environment description")
    bg_parser.add_argument("--output", "-o", required=True, help="Output path")
    bg_parser.add_argument("--camera-angle", default="front view", help="Camera angle")
    bg_parser.add_argument("--style", default="anime", help="Art style")
    bg_parser.add_argument("--seed", type=int, default=0, help="Random seed")
    bg_parser.add_argument("--free-memory", action="store_true", help="Free GPU memory first")

    # Style asset command
    style_parser = subparsers.add_parser("style", help="Generate style reference asset")
    style_parser.add_argument("--name", "-n", required=True, help="Style name")
    style_parser.add_argument("--description", "-d", required=True, help="Style description")
    style_parser.add_argument("--output", "-o", required=True, help="Output path")
    style_parser.add_argument("--seed", type=int, default=0, help="Random seed")
    style_parser.add_argument("--free-memory", action="store_true", help="Free GPU memory first")

    # Batch generation from config
    batch_parser = subparsers.add_parser("batch", help="Generate all assets from config file")
    batch_parser.add_argument("--config", "-c", required=True, help="Path to assets.json")
    batch_parser.add_argument("--output-dir", "-o", required=True, help="Output directory")
    batch_parser.add_argument("--free-memory", action="store_true", help="Free GPU memory first")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "character":
        generator = QwenImageGenerator()
        if args.free_memory:
            generator.free_memory()
        generate_character_asset(
            generator=generator,
            name=args.name,
            description=args.description,
            output_path=args.output,
            style=args.style,
            seed=args.seed,
        )

    elif args.command == "background":
        generator = QwenImageGenerator()
        if args.free_memory:
            generator.free_memory()
        generate_background_asset(
            generator=generator,
            name=args.name,
            description=args.description,
            output_path=args.output,
            camera_angle=args.camera_angle,
            style=args.style,
            seed=args.seed,
        )

    elif args.command == "style":
        generator = QwenImageGenerator()
        if args.free_memory:
            generator.free_memory()
        generate_style_asset(
            generator=generator,
            name=args.name,
            description=args.description,
            output_path=args.output,
            seed=args.seed,
        )

    elif args.command == "batch":
        generate_assets_from_config(
            config_path=args.config,
            output_dir=args.output_dir,
            free_memory=args.free_memory,
        )


if __name__ == "__main__":
    main()
