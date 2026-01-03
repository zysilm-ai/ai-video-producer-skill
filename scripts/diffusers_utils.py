"""
Shared utilities for diffusers-based generation.
Handles model loading, memory optimization, and progress tracking.
"""

import os
from pathlib import Path

# Set HF_HOME to models directory in this repository BEFORE importing torch/diffusers
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
MODELS_DIR = REPO_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"] = str(MODELS_DIR / "hub")

import torch
from typing import Optional, Callable, Any


# Global pipeline cache to avoid reloading models
_pipeline_cache: dict[str, Any] = {}


def get_device() -> str:
    """Get best available device for inference."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_torch_dtype(device: str = None) -> torch.dtype:
    """Get appropriate dtype for device."""
    if device is None:
        device = get_device()

    if device == "cuda":
        # Check if GPU supports bfloat16
        if torch.cuda.is_bf16_supported():
            return torch.bfloat16
        return torch.float16
    return torch.float32


def get_vram_gb() -> Optional[float]:
    """Get available VRAM in gigabytes."""
    if torch.cuda.is_available():
        return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    return None


def get_free_vram_gb() -> Optional[float]:
    """Get free VRAM in gigabytes."""
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info(0)
        return free / (1024**3)
    return None


def clear_vram():
    """Clear VRAM cache."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()


def get_quantization_config(mode: str = "fp8"):
    """
    Create quantization config for low VRAM usage.

    Args:
        mode: Quantization mode - "fp8", "int8", or None for no quantization

    Returns:
        Quantization config or None
    """
    if mode == "fp8":
        try:
            from diffusers import BitsAndBytesConfig
            return BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=True,
            )
        except ImportError:
            # Fall back to quanto if bitsandbytes not available
            try:
                from optimum.quanto import QuantizationConfig
                return QuantizationConfig(weights="float8")
            except ImportError:
                pass
    elif mode == "int8":
        try:
            from diffusers import BitsAndBytesConfig
            return BitsAndBytesConfig(load_in_8bit=True)
        except ImportError:
            pass

    return None


def enable_memory_optimization(pipe, vram_gb: float = None, aggressive: bool = False):
    """
    Apply memory optimizations based on available VRAM.

    Args:
        pipe: Diffusers pipeline
        vram_gb: Available VRAM in GB (auto-detected if None)
        aggressive: Use more aggressive offloading

    Returns:
        The optimized pipeline
    """
    if vram_gb is None:
        vram_gb = get_vram_gb()

    if vram_gb is None:
        # Can't detect, assume limited VRAM
        vram_gb = 8

    if vram_gb < 8 or aggressive:
        # Very low VRAM - use sequential CPU offload
        pipe.enable_sequential_cpu_offload()
    elif vram_gb < 12:
        # Low-medium VRAM - use model CPU offload
        pipe.enable_model_cpu_offload()
    elif vram_gb < 16:
        # Medium VRAM - enable attention slicing
        if hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing(slice_size="auto")
    # 16GB+ can run without optimization

    # Enable xformers if available for all VRAM levels
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass  # xformers not available

    return pipe


def create_progress_callback(
    total_steps: int,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    print_progress: bool = True,
):
    """
    Create a progress callback for diffusers pipelines.

    Args:
        total_steps: Total number of inference steps
        on_progress: Optional callback(step, total, message)
        print_progress: Whether to print progress to stdout

    Returns:
        Callback function compatible with diffusers
    """
    from utils import print_status

    def callback(pipe, step: int, timestep: int, callback_kwargs: dict) -> dict:
        progress_pct = int((step / total_steps) * 100)
        msg = f"Step {step}/{total_steps} ({progress_pct}%)"

        if print_progress:
            print_status(msg, "progress")

        if on_progress:
            on_progress(step, total_steps, msg)

        return callback_kwargs

    return callback


def get_pipeline_from_cache(key: str):
    """Get a cached pipeline by key."""
    return _pipeline_cache.get(key)


def set_pipeline_cache(key: str, pipe):
    """Cache a pipeline for reuse."""
    _pipeline_cache[key] = pipe


def clear_pipeline_cache():
    """Clear all cached pipelines and free VRAM."""
    global _pipeline_cache
    _pipeline_cache = {}
    clear_vram()


def print_memory_stats():
    """Print current VRAM usage stats."""
    from utils import print_status

    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / (1024**3)
        reserved = torch.cuda.memory_reserved(0) / (1024**3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)

        print_status(f"VRAM: {allocated:.1f}GB allocated, {reserved:.1f}GB reserved, {total:.1f}GB total", "info")
    else:
        print_status("CUDA not available", "warning")


# Resolution presets shared across scripts
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384, "length": 49},
    "medium": {"width": 832, "height": 480, "length": 81},
    "high": {"width": 1280, "height": 720, "length": 81},
}


def get_resolution_preset(preset: str, vram_gb: float = None) -> dict:
    """
    Get resolution preset, with automatic downgrade for low VRAM.

    Args:
        preset: Desired preset name
        vram_gb: Available VRAM (auto-detected if None)

    Returns:
        Resolution dict with width, height, length
    """
    if vram_gb is None:
        vram_gb = get_vram_gb() or 10

    # Auto-downgrade if VRAM is insufficient
    if preset == "high" and vram_gb < 16:
        preset = "medium"
    if preset == "medium" and vram_gb < 10:
        preset = "low"

    return RESOLUTION_PRESETS.get(preset, RESOLUTION_PRESETS["medium"])
