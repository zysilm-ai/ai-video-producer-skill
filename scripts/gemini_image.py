#!/usr/bin/env python3
"""
Generate images using Google Gemini API.
Used for creating keyframes in the AI video production workflow.
"""

import argparse
import sys
from pathlib import Path

try:
    from google import genai
    from google.genai import types
    from PIL import Image
except ImportError as e:
    if "PIL" in str(e):
        print("Error: Pillow package not installed", file=sys.stderr)
        print("Install with: pip install Pillow", file=sys.stderr)
    else:
        print("Error: google-genai package not installed", file=sys.stderr)
        print("Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

from utils import (
    get_api_key,
    load_style_config,
    ensure_output_dir,
    print_status,
    build_enhanced_prompt,
)


def generate_image(
    prompt: str,
    output_path: str,
    style_ref: str | None = None,
    reference_images: list[str] | None = None,
    aspect_ratio: str = "16:9",
    model: str = "gemini-3-pro-image-preview",
) -> str:
    """
    Generate an image using Gemini API.

    Args:
        prompt: Text prompt describing the image
        output_path: Path to save the generated image
        style_ref: Optional path to style configuration JSON
        reference_images: Optional list of reference image paths
        aspect_ratio: Aspect ratio (16:9, 9:16, 1:1, 4:3)
        model: Gemini model to use

    Returns:
        Path to saved image
    """
    # Initialize client
    client = genai.Client(api_key=get_api_key())

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
    print_status(f"Generating image with prompt: {enhanced_prompt[:100]}...")

    # Build content parts - reference images first, then prompt
    contents = []

    # Add reference images if provided (for character/style consistency)
    if reference_images:
        for img_path in reference_images:
            try:
                if not Path(img_path).exists():
                    raise FileNotFoundError(f"Image not found: {img_path}")
                # Use PIL.Image.open() as per Google's API documentation
                img = Image.open(img_path)
                contents.append(img)
                print_status(f"Added reference image: {img_path}")
            except FileNotFoundError:
                print_status(f"Reference image not found: {img_path}", "warning")
            except Exception as e:
                print_status(f"Failed to load reference image {img_path}: {e}", "warning")

    # Add the prompt after reference images
    # Include instruction to maintain consistency if references provided
    if reference_images and len(contents) > 0:
        enhanced_prompt = f"Using the reference image(s) provided, maintain character and style consistency. {enhanced_prompt}"

    contents.append(enhanced_prompt)

    # Generate image
    print_status("Calling Gemini API...", "progress")

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["image", "text"],
            )
        )

        # Extract and save image
        output = ensure_output_dir(output_path)

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                with open(output, "wb") as f:
                    f.write(part.inline_data.data)
                print_status(f"Image saved to: {output_path}", "success")
                return str(output)

        # If no image in response, check for text
        for part in response.candidates[0].content.parts:
            if part.text:
                print_status(f"Model response: {part.text}", "warning")

        print_status("No image generated in response", "error")
        sys.exit(1)

    except Exception as e:
        print_status(f"Generation failed: {e}", "error")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Gemini API for video keyframes"
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
        help="Reference image path (can be specified multiple times)"
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        default="16:9",
        choices=["16:9", "9:16", "1:1", "4:3"],
        help="Aspect ratio for generated image"
    )
    parser.add_argument(
        "--model", "-m",
        default="gemini-3-pro-image-preview",
        help="Gemini model to use"
    )

    args = parser.parse_args()

    generate_image(
        prompt=args.prompt,
        output_path=args.output,
        style_ref=args.style_ref,
        reference_images=args.reference_images,
        aspect_ratio=args.aspect_ratio,
        model=args.model,
    )


if __name__ == "__main__":
    main()
