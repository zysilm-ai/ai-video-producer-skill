#!/usr/bin/env python3
"""
Validate diffusers setup for AI video production.
Checks dependencies, models, and optionally tests pipeline loading.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Set HF_HOME to models directory in this repository
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_DIR = SCRIPT_DIR.parent
MODELS_DIR = REPO_DIR / "models"

os.environ["HF_HOME"] = str(MODELS_DIR)
os.environ["HUGGINGFACE_HUB_CACHE"] = str(MODELS_DIR / "hub")


# Required models
REQUIRED_MODELS = {
    "Qwen/Qwen-Image-Edit-2511": {
        "description": "Qwen Image Edit 2511",
        "purpose": "Keyframe generation (T2I, Edit modes)",
        "size_gb": 20.5,
    },
    "Wan-AI/Wan2.2-I2V-A14B-Diffusers": {
        "description": "WAN 2.2 I2V A14B",
        "purpose": "Video generation (I2V, FLF2V modes)",
        "size_gb": 28.0,
    },
}

# LoRA files (checked separately as single files, not full repos)
REQUIRED_LORAS = {
    "lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v": {
        "description": "LightX2V WAN LoRA",
        "purpose": "Fast 8-step video generation",
        "size_gb": 0.7,
        "filename": "loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
    },
    "lightx2v/Qwen-Image-Edit-2511-Lightning": {
        "description": "Lightning Qwen LoRA",
        "purpose": "Fast 4-step image generation",
        "size_gb": 0.85,
        "filename": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
    },
}

OPTIONAL_MODELS = {
    "InstantX/Qwen-Image-ControlNet-Union": {
        "description": "Qwen ControlNet Union",
        "purpose": "Pose-guided keyframe generation",
        "size_gb": 3.5,
    },
}


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


def check_dependencies() -> dict:
    """Check if required packages are installed."""
    results = {
        "python_version": None,
        "packages": {},
        "cuda": None,
        "vram_gb": None,
    }

    # Python version
    import platform
    results["python_version"] = platform.python_version()

    # PyTorch
    try:
        import torch
        results["packages"]["torch"] = torch.__version__

        if torch.cuda.is_available():
            results["cuda"] = {
                "available": True,
                "device": torch.cuda.get_device_name(0),
                "version": torch.version.cuda,
            }
            results["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        else:
            results["cuda"] = {"available": False}
    except ImportError:
        results["packages"]["torch"] = None

    # Other packages
    packages_to_check = [
        ("diffusers", "diffusers"),
        ("transformers", "transformers"),
        ("accelerate", "accelerate"),
        ("huggingface_hub", "huggingface_hub"),
        ("PIL", "Pillow"),
    ]

    for import_name, package_name in packages_to_check:
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", "installed")
            results["packages"][package_name] = version
        except ImportError:
            results["packages"][package_name] = None

    return results


def check_models() -> dict:
    """Check which models are cached."""
    results = {
        "required": {},
        "loras": {},
        "optional": {},
        "cache_path": None,
    }

    try:
        from huggingface_hub import scan_cache_dir, try_to_load_from_cache
        from huggingface_hub.errors import CacheNotFound

        results["cache_path"] = str(MODELS_DIR)

        try:
            cache_info = scan_cache_dir()
            cached_repos = {repo.repo_id: repo.size_on_disk / (1024**3) for repo in cache_info.repos}
        except CacheNotFound:
            cached_repos = {}

        # Check required models
        for model_id, info in REQUIRED_MODELS.items():
            if model_id in cached_repos:
                results["required"][model_id] = {
                    "status": "installed",
                    "size_gb": cached_repos[model_id],
                    **info,
                }
            else:
                results["required"][model_id] = {
                    "status": "missing",
                    **info,
                }

        # Check required LoRA files
        for repo_id, info in REQUIRED_LORAS.items():
            filename = info.get("filename", "")
            try:
                cached_path = try_to_load_from_cache(repo_id, filename)
                if cached_path is not None:
                    size_gb = Path(cached_path).stat().st_size / (1024**3)
                    results["loras"][repo_id] = {
                        "status": "installed",
                        "size_gb": size_gb,
                        **info,
                    }
                else:
                    results["loras"][repo_id] = {
                        "status": "missing",
                        **info,
                    }
            except Exception:
                results["loras"][repo_id] = {
                    "status": "missing",
                    **info,
                }

        # Check optional models
        for model_id, info in OPTIONAL_MODELS.items():
            if model_id in cached_repos:
                results["optional"][model_id] = {
                    "status": "installed",
                    "size_gb": cached_repos[model_id],
                    **info,
                }
            else:
                results["optional"][model_id] = {
                    "status": "not_installed",
                    **info,
                }

    except ImportError:
        results["error"] = "huggingface_hub not installed"

    return results


def test_pipeline_loading(quick: bool = True) -> dict:
    """Test that pipelines can be loaded."""
    results = {
        "qwen_image": None,
        "wan_video": None,
    }

    try:
        import torch

        if quick:
            # Just test imports
            print_status("Testing imports...", "progress")

            try:
                from diffusers import FluxPipeline
                results["qwen_image"] = "import_ok"
            except ImportError as e:
                results["qwen_image"] = f"import_error: {e}"

            try:
                from diffusers import WanImageToVideoPipeline
                results["wan_video"] = "import_ok"
            except ImportError as e:
                results["wan_video"] = f"import_error: {e}"
        else:
            # Actually load pipelines (slow, requires models)
            print_status("Testing pipeline loading (this may take a while)...", "progress")

            try:
                from diffusers import FluxPipeline
                pipe = FluxPipeline.from_pretrained(
                    "Qwen/Qwen-Image-Edit-2511",
                    torch_dtype=torch.bfloat16,
                )
                del pipe
                results["qwen_image"] = "load_ok"
            except Exception as e:
                results["qwen_image"] = f"load_error: {e}"

            try:
                from diffusers import WanImageToVideoPipeline
                pipe = WanImageToVideoPipeline.from_pretrained(
                    "Wan-AI/Wan2.2-I2V-A14B-Diffusers",
                    torch_dtype=torch.bfloat16,
                )
                del pipe
                results["wan_video"] = "load_ok"
            except Exception as e:
                results["wan_video"] = f"load_error: {e}"

            # Clear VRAM
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    except ImportError:
        results["error"] = "torch or diffusers not installed"

    return results


def validate_all(detailed: bool = False, test_load: bool = False) -> dict:
    """Run all validation checks."""
    results = {
        "dependencies": check_dependencies(),
        "models": check_models(),
        "ready": False,
    }

    if test_load:
        results["pipeline_test"] = test_pipeline_loading(quick=not detailed)

    # Determine if ready
    deps = results["dependencies"]
    models = results["models"]

    # Check dependencies
    deps_ok = all([
        deps["packages"].get("torch"),
        deps["packages"].get("diffusers"),
        deps["packages"].get("transformers"),
        deps["packages"].get("accelerate"),
    ])

    # Check required models
    models_ok = all(
        info["status"] == "installed"
        for info in models.get("required", {}).values()
    )

    # Check required LoRAs (optional for functionality, but included in "ready" check)
    loras_ok = all(
        info["status"] == "installed"
        for info in models.get("loras", {}).values()
    )

    results["ready"] = deps_ok and models_ok and loras_ok

    return results


def print_report(results: dict, detailed: bool = False):
    """Print human-readable validation report."""
    print("\n" + "=" * 50)
    print("    Diffusers Setup Validation Report")
    print("=" * 50 + "\n")

    # Dependencies
    print("=== Dependencies ===\n")
    deps = results["dependencies"]

    print_status(f"Python: {deps['python_version']}", "success" if deps['python_version'] else "error")

    for pkg, version in deps["packages"].items():
        if version:
            print_status(f"{pkg}: {version}", "success")
        else:
            print_status(f"{pkg}: NOT INSTALLED", "error")

    if deps["cuda"]:
        if deps["cuda"]["available"]:
            print_status(f"CUDA: {deps['cuda']['device']}", "success")
            print_status(f"VRAM: {deps['vram_gb']:.1f}GB", "success")
        else:
            print_status("CUDA: Not available", "warning")

    # Models
    print("\n=== Required Models ===\n")
    models = results["models"]

    for model_id, info in models.get("required", {}).items():
        status = info["status"]
        desc = info["description"]

        if status == "installed":
            size = info.get("size_gb", 0)
            print_status(f"{desc} ({size:.1f}GB)", "success")
            if detailed:
                print(f"      Model: {model_id}")
                print(f"      Purpose: {info['purpose']}")
        else:
            print_status(f"{desc} - MISSING", "error")
            if detailed:
                print(f"      Model: {model_id}")
                print(f"      Expected size: ~{info['size_gb']:.1f}GB")

    # LoRAs
    if models.get("loras"):
        print("\n=== Required LoRAs ===\n")
        for repo_id, info in models.get("loras", {}).items():
            status = info["status"]
            desc = info["description"]

            if status == "installed":
                size = info.get("size_gb", 0)
                print_status(f"{desc} ({size*1024:.0f}MB)", "success")
                if detailed:
                    print(f"      File: {info.get('filename', repo_id)}")
                    print(f"      Purpose: {info['purpose']}")
            else:
                print_status(f"{desc} - MISSING", "error")
                if detailed:
                    print(f"      File: {info.get('filename', repo_id)}")
                    print(f"      Expected size: ~{info['size_gb']*1024:.0f}MB")

    print("\n=== Optional Models ===\n")
    for model_id, info in models.get("optional", {}).items():
        status = info["status"]
        desc = info["description"]

        if status == "installed":
            size = info.get("size_gb", 0)
            print_status(f"{desc} ({size:.1f}GB)", "success")
        else:
            print_status(f"{desc} - not installed", "info")

    if detailed and models.get("cache_path"):
        print(f"\n    Cache location: {models['cache_path']}")

    # Pipeline test
    if "pipeline_test" in results:
        print("\n=== Pipeline Tests ===\n")
        tests = results["pipeline_test"]

        for name, status in tests.items():
            if name == "error":
                print_status(f"Error: {status}", "error")
            elif status and "ok" in status:
                print_status(f"{name}: {status}", "success")
            else:
                print_status(f"{name}: {status}", "error")

    # Summary
    print("\n" + "=" * 50)
    if results["ready"]:
        print_status("Setup complete! Ready for generation.", "success")
    else:
        print_status("Setup incomplete. See details above.", "warning")
        print("\nTo complete setup:")
        print("  python setup_diffusers.py --download")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate diffusers setup for AI video production"
    )
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Show detailed information"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--test-load",
        action="store_true",
        help="Test pipeline loading (slow)"
    )

    args = parser.parse_args()

    results = validate_all(detailed=args.detailed, test_load=args.test_load)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results, detailed=args.detailed)

    sys.exit(0 if results["ready"] else 1)


if __name__ == "__main__":
    main()
