#!/usr/bin/env python3
"""
Validate ComfyUI setup and report missing models.
Checks all required models and provides guidance for manual downloads.
"""

import argparse
import json
import os
import sys
from pathlib import Path


# Status icons (ASCII for Windows compatibility)
ICONS = {
    "ok": "[+]",
    "missing": "[x]",
    "warning": "[!]",
    "info": "[i]",
}

# Common ComfyUI installation paths
COMMON_PATHS = [
    Path("D:/comfyui"),
    Path("C:/comfyui"),
    Path.home() / "ComfyUI",
    Path.home() / "comfyui",
    Path("/opt/ComfyUI"),
]


# Model definitions with expected locations and sizes
REQUIRED_MODELS = {
    # Qwen Image Edit 2511 models (for keyframe generation)
    "Qwen Image Edit 2511": {
        "path": "models/unet/qwen_image_edit_2511_fp8mixed.safetensors",
        "size_mb": 12000,  # ~12GB
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/Qwen_Image_Edit_2511_ComfyUI_Repackaged",
    },
    "Qwen VL Text Encoder": {
        "path": "models/clip/qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "size_mb": 7500,  # ~7.5GB
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/Qwen_Image_Edit_2511_ComfyUI_Repackaged",
    },
    "Qwen VAE": {
        "path": "models/vae/qwen_image_vae.safetensors",
        "size_mb": 200,
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/Qwen_Image_Edit_2511_ComfyUI_Repackaged",
    },
    # WAN 2.2 models (for video generation)
    "WAN Low Noise Model": {
        "path": "models/diffusion_models/wan2.2_i2v_low_noise_14B_Q4_K_M.gguf",
        "size_mb": 8000,  # ~8GB
        "auto_download": True,
        "source": "https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF",
    },
    "WAN VAE": {
        "path": "models/vae/wan_2.1_vae.safetensors",
        "size_mb": 300,
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged",
    },
    "WAN Text Encoder": {
        "path": "models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "alt_paths": ["models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"],
        "size_mb": 4900,  # ~4.9GB
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged",
    },
    "WAN LightX2V LoRA": {
        "path": "models/loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
        "size_mb": 700,
        "auto_download": True,
        "source": "https://huggingface.co/Kijai/WanVideo_comfy/tree/main/Lightx2v",
    },
}

OPTIONAL_MODELS = {
    "Qwen ControlNet Union": {
        "path": "models/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors",
        "size_mb": 3500,  # ~3.5GB
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/Qwen-Image-InstantX-ControlNets",
        "note": "For pose-guided keyframe generation",
    },
    "SigLIP Vision Encoder": {
        "path": "models/clip_vision/sigclip_vision_patch14_384.safetensors",
        "size_mb": 800,
        "auto_download": True,
        "source": "https://huggingface.co/Comfy-Org/sigclip_vision_384",
        "note": "Used for image reference features",
    },
}

REQUIRED_NODES = [
    "ComfyUI-GGUF",
    "ComfyUI-WanVideoWrapper",
    "ComfyUI-VideoHelperSuite",
    "ComfyUI_RH_Qwen-Image",
]

OPTIONAL_NODES = [
    "comfyui_controlnet_aux",  # For pose preprocessing
]


def find_comfyui() -> Path | None:
    """Find ComfyUI installation path."""
    # Check environment variable first
    env_path = os.environ.get("COMFYUI_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # Check common paths
    for path in COMMON_PATHS:
        if path.exists() and (path / "main.py").exists():
            return path

    return None


def check_model(comfyui_path: Path, model_name: str, model_info: dict) -> dict:
    """Check if a model exists and validate its size."""
    result = {
        "name": model_name,
        "found": False,
        "path": None,
        "size_ok": False,
        "actual_size_mb": 0,
        "expected_size_mb": model_info.get("size_mb", 0),
        "auto_download": model_info.get("auto_download", True),
        "source": model_info.get("source", ""),
        "note": model_info.get("note", ""),
    }

    # Check primary path
    paths_to_check = [model_info["path"]]
    if "alt_paths" in model_info:
        paths_to_check.extend(model_info["alt_paths"])

    for rel_path in paths_to_check:
        full_path = comfyui_path / rel_path
        if full_path.exists():
            result["found"] = True
            result["path"] = str(full_path)

            # Check file size
            actual_size_mb = full_path.stat().st_size / (1024 * 1024)
            result["actual_size_mb"] = round(actual_size_mb, 1)

            # Allow 10% variance in size
            expected = model_info.get("size_mb", 0)
            if expected > 0:
                result["size_ok"] = actual_size_mb >= expected * 0.9
            else:
                result["size_ok"] = True
            break

    return result


def check_custom_nodes(comfyui_path: Path) -> dict:
    """Check if required custom nodes are installed."""
    nodes_path = comfyui_path / "custom_nodes"
    results = {}

    for node_name in REQUIRED_NODES:
        node_path = nodes_path / node_name
        results[node_name] = node_path.exists()

    return results


def check_server_running() -> bool:
    """Check if ComfyUI server is running."""
    try:
        import requests
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def print_status(message: str, status: str = "info"):
    """Print a status message with icon."""
    icon = ICONS.get(status, "-")
    print(f"{icon} {message}")


def validate_setup(comfyui_path: Path | None = None, detailed: bool = False) -> bool:
    """Run full validation and return True if setup is complete."""
    print("\n=== ComfyUI Setup Validation ===\n")

    all_ok = True

    # Find ComfyUI
    if comfyui_path is None:
        comfyui_path = find_comfyui()

    if comfyui_path is None:
        print_status("ComfyUI installation not found!", "missing")
        print("\nComfyUI not detected in common locations:")
        for path in COMMON_PATHS:
            print(f"  - {path}")
        print("\nRun setup script to install:")
        print("  python scripts/setup_comfyui.py --install-path <PATH>")
        return False

    print_status(f"ComfyUI found at: {comfyui_path}", "ok")

    # Check server
    if check_server_running():
        print_status("ComfyUI server is running", "ok")
    else:
        print_status("ComfyUI server is not running", "warning")
        print("  Start with: python scripts/setup_comfyui.py --start")

    # Check custom nodes
    print("\n--- Custom Nodes ---")
    nodes_status = check_custom_nodes(comfyui_path)
    for node_name, installed in nodes_status.items():
        if installed:
            print_status(f"{node_name}", "ok")
        else:
            print_status(f"{node_name} - NOT INSTALLED", "missing")
            all_ok = False

    # Check required models
    print("\n--- Required Models ---")
    missing_manual = []
    missing_auto = []

    for model_name, model_info in REQUIRED_MODELS.items():
        result = check_model(comfyui_path, model_name, model_info)

        if result["found"]:
            if result["size_ok"]:
                print_status(f"{model_name}", "ok")
                if detailed:
                    print(f"      Path: {result['path']}")
                    print(f"      Size: {result['actual_size_mb']}MB")
            else:
                print_status(f"{model_name} - SIZE MISMATCH (may be corrupted)", "warning")
                print(f"      Expected: ~{result['expected_size_mb']}MB, Got: {result['actual_size_mb']}MB")
                all_ok = False
        else:
            print_status(f"{model_name} - MISSING", "missing")
            all_ok = False

            if result["auto_download"]:
                missing_auto.append(result)
            else:
                missing_manual.append(result)

    # Check optional models
    print("\n--- Optional Models ---")
    for model_name, model_info in OPTIONAL_MODELS.items():
        result = check_model(comfyui_path, model_name, model_info)

        if result["found"]:
            print_status(f"{model_name}", "ok")
        else:
            print_status(f"{model_name} - not installed (optional)", "info")
            if result["note"]:
                print(f"      Note: {result['note']}")

    # Summary
    print("\n=== Summary ===\n")

    if all_ok:
        print_status("All required components are installed!", "ok")
    else:
        print_status("Some components are missing", "warning")

        if missing_auto:
            print("\nModels that can be auto-downloaded (run setup script):")
            for m in missing_auto:
                print(f"  - {m['name']}")
            print("\n  Run: python scripts/setup_comfyui.py")

        if missing_manual:
            print("\nModels requiring manual download:")
            for m in missing_manual:
                print(f"\n  {m['name']}:")
                print(f"    Source: {m['source']}")
                if m["note"]:
                    print(f"    Note: {m['note']}")
            print("\n  See SETUP.md for detailed instructions.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Validate ComfyUI setup for AI Video Producer"
    )
    parser.add_argument(
        "--path",
        help="Path to ComfyUI installation",
        type=Path,
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information for each model",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    comfyui_path = args.path
    if comfyui_path and not comfyui_path.exists():
        print(f"Error: Specified path does not exist: {comfyui_path}")
        sys.exit(1)

    if args.json:
        # JSON output mode
        path = comfyui_path or find_comfyui()
        if path is None:
            print(json.dumps({"error": "ComfyUI not found", "installed": False}))
            sys.exit(1)

        results = {
            "installed": True,
            "path": str(path),
            "server_running": check_server_running(),
            "custom_nodes": check_custom_nodes(path),
            "required_models": {},
            "optional_models": {},
        }

        for name, info in REQUIRED_MODELS.items():
            results["required_models"][name] = check_model(path, name, info)

        for name, info in OPTIONAL_MODELS.items():
            results["optional_models"][name] = check_model(path, name, info)

        print(json.dumps(results, indent=2))
    else:
        # Normal output mode
        success = validate_setup(comfyui_path, args.detailed)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
