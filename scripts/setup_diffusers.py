#!/usr/bin/env python3
"""
Setup script for HuggingFace diffusers-based generation.
Downloads required models and validates the installation.
"""

import argparse
import os
import sys
from pathlib import Path

# Set HF_HOME to models directory in this repository
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
MODELS_DIR = REPO_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Set environment variable before importing huggingface_hub
os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"] = str(MODELS_DIR / "hub")


# Model IDs to pre-download
REQUIRED_MODELS = [
    # Qwen Image Edit 2511
    ("Qwen/Qwen-Image-Edit-2511", "Qwen Image Edit 2511 (main model)"),
    # WAN 2.2 I2V A14B (MoE architecture)
    ("Wan-AI/Wan2.2-I2V-A14B-Diffusers", "WAN 2.2 I2V A14B"),
]

# LoRA files to download (only specific files, not entire repos)
LORA_FILES = [
    # LightX2V LoRA for WAN fast 8-step video generation
    (
        "lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v",
        "loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
        "LightX2V WAN LoRA (8-step video)",
    ),
    # Lightning LoRA for Qwen fast 4-step image generation
    (
        "lightx2v/Qwen-Image-Edit-2511-Lightning",
        "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
        "Lightning Qwen LoRA (4-step image)",
    ),
]

OPTIONAL_MODELS = [
    # Qwen ControlNet for pose-guided generation
    ("InstantX/Qwen-Image-ControlNet-Union", "Qwen ControlNet Union (for pose mode)"),
]

# GGUF quantized models for low VRAM (10GB) systems
# Source: https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF
QWEN_GGUF_REPO = "unsloth/Qwen-Image-Edit-2511-GGUF"
QWEN_GGUF_VARIANTS = {
    "q2_k": ("qwen-image-edit-2511-Q2_K.gguf", 7.2, "fastest, lowest quality"),
    "q3_k_m": ("qwen-image-edit-2511-Q3_K_M.gguf", 9.7, ""),
    "q4_k_m": ("qwen-image-edit-2511-Q4_K_M.gguf", 13.1, ""),
    "q5_k_m": ("qwen-image-edit-2511-Q5_K_M.gguf", 15.0, ""),
    "q6_k": ("qwen-image-edit-2511-Q6_K.gguf", 16.8, "recommended balance"),
    "q8_0": ("qwen-image-edit-2511-Q8_0.gguf", 21.8, "highest quality"),
}
DEFAULT_GGUF_VARIANT = "q6_k"


def print_status(message: str, status: str = "info") -> None:
    """Print formatted status message."""
    icons = {
        "info": "[i]",
        "success": "[+]",
        "error": "[x]",
        "warning": "[!]",
        "progress": "[*]",
    }
    print(f"{icons.get(status, '-')} {message}")


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print_status(f"Python 3.10+ required, found {version.major}.{version.minor}", "error")
        return False
    print_status(f"Python {version.major}.{version.minor}.{version.micro}", "success")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    print("\n=== Checking Dependencies ===\n")

    all_ok = True

    # Check PyTorch
    try:
        import torch
        print_status(f"PyTorch: {torch.__version__}", "success")

        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print_status(f"CUDA: {device_name}", "success")
            print_status(f"VRAM: {vram:.1f}GB", "success")

            if vram < 10:
                print_status("Warning: Less than 10GB VRAM, may need aggressive optimization", "warning")
        else:
            print_status("CUDA not available - CPU inference will be slow", "warning")
    except ImportError:
        print_status("PyTorch not installed", "error")
        print_status("Install with: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124", "info")
        all_ok = False

    # Check diffusers
    try:
        import diffusers
        print_status(f"Diffusers: {diffusers.__version__}", "success")
    except ImportError:
        print_status("Diffusers not installed", "error")
        print_status("Install with: pip install diffusers", "info")
        all_ok = False

    # Check transformers
    try:
        import transformers
        print_status(f"Transformers: {transformers.__version__}", "success")
    except ImportError:
        print_status("Transformers not installed", "error")
        all_ok = False

    # Check accelerate
    try:
        import accelerate
        print_status(f"Accelerate: {accelerate.__version__}", "success")
    except ImportError:
        print_status("Accelerate not installed", "error")
        all_ok = False

    # Check huggingface_hub
    try:
        import huggingface_hub
        print_status(f"HuggingFace Hub: {huggingface_hub.__version__}", "success")
    except ImportError:
        print_status("HuggingFace Hub not installed", "error")
        all_ok = False

    return all_ok


def download_gguf(variant: str = None):
    """Download GGUF quantized model for low VRAM systems."""
    from huggingface_hub import hf_hub_download

    if variant is None:
        variant = DEFAULT_GGUF_VARIANT

    if variant not in QWEN_GGUF_VARIANTS:
        print_status(f"Unknown GGUF variant: {variant}", "error")
        print_status(f"Available: {', '.join(QWEN_GGUF_VARIANTS.keys())}", "info")
        return None

    filename, size_gb, description = QWEN_GGUF_VARIANTS[variant]
    desc_suffix = f" ({description})" if description else ""

    print_status(f"Downloading GGUF {variant.upper()}{desc_suffix}...", "progress")
    print_status(f"    File: {QWEN_GGUF_REPO}/{filename} (~{size_gb}GB)", "info")

    try:
        path = hf_hub_download(
            repo_id=QWEN_GGUF_REPO,
            filename=filename,
            resume_download=True,
        )
        print_status(f"    Downloaded to: {path}", "success")
        return path
    except Exception as e:
        print_status(f"    Failed: {e}", "error")
        return None


def download_models(models: list = None, include_optional: bool = False, gguf_variant: str = None):
    """Pre-download models from HuggingFace."""
    from huggingface_hub import snapshot_download, hf_hub_download, HfFolder

    print("\n=== Downloading Models ===\n")

    # Check if logged in to HuggingFace
    token = HfFolder.get_token()
    if token:
        print_status("HuggingFace token found", "success")
    else:
        print_status("No HuggingFace token (some models may require login)", "warning")
        print_status("Login with: huggingface-cli login", "info")

    if models is None:
        models = REQUIRED_MODELS.copy()
        if include_optional:
            models.extend(OPTIONAL_MODELS)

    # Count total downloads (models + LoRAs + GGUF if specified)
    total = len(models) + len(LORA_FILES)
    if gguf_variant:
        total += 1
    idx = 0

    # Download full model repositories
    for model_id, description in models:
        idx += 1
        print_status(f"[{idx}/{total}] Downloading: {description}...", "progress")
        print_status(f"    Model ID: {model_id}", "info")

        try:
            path = snapshot_download(
                model_id,
                resume_download=True,
            )
            print_status(f"    Downloaded to: {path}", "success")
        except Exception as e:
            print_status(f"    Failed: {e}", "error")

    # Download individual LoRA files (not entire repos)
    for repo_id, filename, description in LORA_FILES:
        idx += 1
        print_status(f"[{idx}/{total}] Downloading: {description}...", "progress")
        print_status(f"    File: {repo_id}/{filename}", "info")

        try:
            path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                resume_download=True,
            )
            print_status(f"    Downloaded to: {path}", "success")
        except Exception as e:
            print_status(f"    Failed: {e}", "error")

    # Download GGUF if specified
    if gguf_variant:
        idx += 1
        filename, size_gb, description = QWEN_GGUF_VARIANTS.get(gguf_variant, (None, 0, ""))
        desc_suffix = f" ({description})" if description else ""
        print_status(f"[{idx}/{total}] Downloading: Qwen GGUF {gguf_variant.upper()}{desc_suffix}...", "progress")
        print_status(f"    File: {QWEN_GGUF_REPO}/{filename} (~{size_gb}GB)", "info")

        try:
            path = hf_hub_download(
                repo_id=QWEN_GGUF_REPO,
                filename=filename,
                resume_download=True,
            )
            print_status(f"    Downloaded to: {path}", "success")
        except Exception as e:
            print_status(f"    Failed: {e}", "error")

    print()


def check_cached_models():
    """Check which models are already cached."""
    try:
        from huggingface_hub import scan_cache_dir
        from huggingface_hub.errors import CacheNotFound
    except ImportError:
        print_status("Cannot check cache (huggingface_hub not installed)", "warning")
        return {}

    print("\n=== Cached Models ===\n")
    print_status(f"Cache location: {MODELS_DIR}", "info")

    try:
        cache_info = scan_cache_dir()
    except CacheNotFound:
        print_status("No models downloaded yet", "warning")
        return {}

    found_models = {}
    for repo in cache_info.repos:
        size_gb = repo.size_on_disk / (1024**3)
        found_models[repo.repo_id] = size_gb

    # Check required models
    print("Required Models:")
    for model_id, description in REQUIRED_MODELS:
        if model_id in found_models:
            size = found_models[model_id]
            print_status(f"{description} ({size:.1f}GB)", "success")
        else:
            print_status(f"{description} - NOT DOWNLOADED", "warning")

    # Check optional models
    print("\nOptional Models:")
    for model_id, description in OPTIONAL_MODELS:
        if model_id in found_models:
            size = found_models[model_id]
            print_status(f"{description} ({size:.1f}GB)", "success")
        else:
            print_status(f"{description} - not downloaded", "info")

    return found_models


def estimate_download_size():
    """Estimate total download size for all models."""
    # Approximate sizes in GB
    sizes = {
        "Qwen/Qwen-Image-Edit-2511": 20.5,
        "Wan-AI/Wan2.2-I2V-A14B-Diffusers": 28.0,
        "InstantX/Qwen-Image-ControlNet-Union": 3.5,
    }
    lora_sizes = {
        "lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v": 0.7,
    }

    required_total = sum(sizes.get(m[0], 0) for m in REQUIRED_MODELS)
    required_total += sum(lora_sizes.get(l[0], 0) for l in LORA_FILES)
    optional_total = sum(sizes.get(m[0], 0) for m in OPTIONAL_MODELS)

    return required_total, optional_total


def validate_setup():
    """Validate the complete diffusers setup."""
    print("\n" + "=" * 50)
    print("    Diffusers Setup Validation")
    print("=" * 50)

    all_ok = True

    # Check Python
    if not check_python_version():
        all_ok = False

    # Check dependencies
    if not check_dependencies():
        all_ok = False

    # Check cached models
    found_models = check_cached_models()

    # Check if all required models are present
    missing = []
    for model_id, description in REQUIRED_MODELS:
        if model_id not in found_models:
            missing.append((model_id, description))

    if missing:
        print("\n=== Missing Required Models ===\n")
        for model_id, description in missing:
            print_status(f"{description}", "warning")
        print("\nRun: python setup_diffusers.py --download")
        all_ok = False

    # Summary
    print("\n" + "=" * 50)
    if all_ok:
        print_status("Setup complete! Ready for generation.", "success")
    else:
        print_status("Setup incomplete. See above for details.", "warning")
    print("=" * 50 + "\n")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Setup diffusers for AI video production"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check setup status only (don't download)"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download required models"
    )
    parser.add_argument(
        "--download-all",
        action="store_true",
        help="Download required + optional models"
    )
    parser.add_argument(
        "--gguf",
        dest="gguf_variant",
        choices=list(QWEN_GGUF_VARIANTS.keys()),
        default=None,
        help=f"Download GGUF quantized Qwen model for low VRAM (default: {DEFAULT_GGUF_VARIANT} if --download used)"
    )
    parser.add_argument(
        "--no-gguf",
        action="store_true",
        help="Skip GGUF download even with --download"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show download size estimates"
    )

    args = parser.parse_args()

    if args.info:
        required, optional = estimate_download_size()
        gguf_size = QWEN_GGUF_VARIANTS[DEFAULT_GGUF_VARIANT][1]
        print("\n=== Download Size Estimates ===\n")
        print(f"Required models: ~{required:.1f}GB")
        print(f"GGUF {DEFAULT_GGUF_VARIANT.upper()} (recommended): ~{gguf_size:.1f}GB")
        print(f"Optional models: ~{optional:.1f}GB")
        print(f"Total (all):     ~{required + optional + gguf_size:.1f}GB")
        print(f"\nModels will be stored in: {MODELS_DIR}")
        print("\nGGUF variants available:")
        for variant, (filename, size, desc) in QWEN_GGUF_VARIANTS.items():
            suffix = f" - {desc}" if desc else ""
            marker = " (default)" if variant == DEFAULT_GGUF_VARIANT else ""
            print(f"  {variant}: ~{size:.1f}GB{suffix}{marker}")
        return

    if args.check:
        success = validate_setup()
        sys.exit(0 if success else 1)

    if args.download or args.download_all:
        if not check_dependencies():
            print("\nInstall dependencies first:")
            print("  pip install -r requirements.txt")
            print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124")
            sys.exit(1)

        # Determine GGUF variant to download
        gguf_variant = None
        if not args.no_gguf:
            gguf_variant = args.gguf_variant or DEFAULT_GGUF_VARIANT

        download_models(include_optional=args.download_all, gguf_variant=gguf_variant)
        validate_setup()
        return

    # Default: full setup check
    success = validate_setup()

    if not success:
        print("\nTo complete setup, run:")
        print("  1. pip install -r requirements.txt")
        print("  2. pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124")
        print("  3. python setup_diffusers.py --download")


if __name__ == "__main__":
    main()
