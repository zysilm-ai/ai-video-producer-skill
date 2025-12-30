"""
Shared utilities for AI Video Producer skill.
Handles configuration, file I/O, and common operations.
"""

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any


def get_api_key() -> str:
    """Get Google API key from environment."""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("Error: GOOGLE_API_KEY environment variable not set", file=sys.stderr)
        print("Set it with: export GOOGLE_API_KEY='your-api-key'", file=sys.stderr)
        sys.exit(1)
    return key


def load_image_as_base64(image_path: str) -> str:
    """Load an image file and return base64-encoded string."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime_type(file_path: str) -> str:
    """Get MIME type based on file extension."""
    ext = Path(file_path).suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }
    return mime_types.get(ext, "application/octet-stream")


def load_style_config(style_path: str) -> dict[str, Any]:
    """Load style configuration from JSON file."""
    path = Path(style_path)
    if not path.exists():
        raise FileNotFoundError(f"Style config not found: {style_path}")

    with open(path) as f:
        return json.load(f)


def save_style_config(style_config: dict[str, Any], output_path: str) -> None:
    """Save style configuration to JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(style_config, f, indent=2)

    print(f"Style config saved to: {output_path}")


def ensure_output_dir(output_path: str) -> Path:
    """Ensure output directory exists and return Path object."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def print_status(message: str, status: str = "info") -> None:
    """Print formatted status message."""
    icons = {
        "info": "[i]",
        "success": "[+]",
        "error": "[x]",
        "warning": "[!]",
        "progress": "[*]",
    }
    icon = icons.get(status, "-")
    print(f"{icon} {message}")


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def get_vram_gb() -> float | None:
    """
    Get available VRAM in gigabytes.

    Returns:
        VRAM in GB or None if unavailable
    """
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except ImportError:
        pass
    return None


def get_recommended_resolution(vram_gb: float | None = None) -> dict:
    """
    Get recommended resolution based on available VRAM.

    Args:
        vram_gb: VRAM in GB (auto-detected if None)

    Returns:
        Dict with width, height, num_frames keys
    """
    if vram_gb is None:
        vram_gb = get_vram_gb()

    if vram_gb is None:
        # Default to medium if can't detect
        return {"width": 832, "height": 480, "num_frames": 49, "preset": "medium"}

    if vram_gb >= 16:
        return {"width": 1280, "height": 720, "num_frames": 81, "preset": "high"}
    elif vram_gb >= 10:
        return {"width": 832, "height": 480, "num_frames": 49, "preset": "medium"}
    else:
        return {"width": 640, "height": 384, "num_frames": 49, "preset": "low"}


def print_system_info() -> None:
    """Print system information for debugging."""
    print_status("System Information:", "info")

    # Python version
    import platform
    print(f"  Python: {platform.python_version()}")
    print(f"  Platform: {platform.system()} {platform.release()}")

    # CUDA/GPU info
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  GPU: {device_name}")
            print(f"  VRAM: {vram_total:.1f} GB")

            rec = get_recommended_resolution(vram_total)
            print(f"  Recommended preset: {rec['preset']} ({rec['width']}x{rec['height']})")
        else:
            print("  GPU: Not available (CUDA not found)")
    except ImportError:
        print("  GPU: Unknown (PyTorch not installed)")


def build_enhanced_prompt(
    base_prompt: str,
    style_config: dict[str, Any] | None = None,
    additional_constraints: list[str] | None = None,
) -> str:
    """
    Build an enhanced prompt incorporating style configuration.

    Args:
        base_prompt: The core prompt describing the scene/action
        style_config: Optional style configuration dict
        additional_constraints: Optional list of additional constraints

    Returns:
        Enhanced prompt string
    """
    parts = [base_prompt]

    if style_config:
        # Add visual style
        if "visual_style" in style_config:
            vs = style_config["visual_style"]
            if "art_style" in vs:
                parts.append(f"Art style: {vs['art_style']}")
            if "color_palette" in vs:
                parts.append(f"Color palette: {vs['color_palette']}")
            if "lighting" in vs:
                parts.append(f"Lighting: {vs['lighting']}")

        # Add motion language
        if "motion_language" in style_config:
            ml = style_config["motion_language"]
            if "movement_quality" in ml:
                parts.append(f"Movement: {ml['movement_quality']}")
            if "camera_style" in ml:
                parts.append(f"Camera: {ml['camera_style']}")

    if additional_constraints:
        parts.extend(additional_constraints)

    return ". ".join(parts)
