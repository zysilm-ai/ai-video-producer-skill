#!/usr/bin/env python3
"""
Auto-setup script for ComfyUI with WAN 2.2 video generation.
Downloads and configures everything needed to run the AI video skill.

Installs ComfyUI directly into the repository folder (./comfyui).

Usage:
    python setup_comfyui.py              # Full setup
    python setup_comfyui.py --check      # Check if setup is complete
    python setup_comfyui.py --start      # Start ComfyUI server
    python setup_comfyui.py --models     # Download models only
"""

import argparse
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


# Configuration - ComfyUI installs in repository folder
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
COMFYUI_DIR = PROJECT_DIR / "comfyui"

COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI.git"

# Additional pip packages required for custom nodes
ADDITIONAL_PIP_PACKAGES = [
    "matplotlib",
    "scikit-image",
    "scipy",
    "einops",
    "fvcore",
    "addict",
    "yacs",
    "trimesh",
    "albumentations",
    "mediapipe",
]

CUSTOM_NODES = {
    "ComfyUI-GGUF": "https://github.com/city96/ComfyUI-GGUF.git",
    "ComfyUI-VideoHelperSuite": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
    "ComfyUI-Manager": "https://github.com/ltdrdata/ComfyUI-Manager.git",
}

# Model URLs and paths (relative to ComfyUI/models/)
MODELS = {
    # WAN 2.1 GGUF model (Q4_K_M for 10GB VRAM - 11.3GB file)
    "diffusion_models/wan2.1-i2v-14b-480p-Q4_K_M.gguf": {
        "url": "https://huggingface.co/city96/Wan2.1-I2V-14B-480P-GGUF/resolve/main/wan2.1-i2v-14b-480p-Q4_K_M.gguf",
        "size_gb": 11.3,
        "required": True,
    },
    # WAN Text encoder
    "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "size_gb": 4.9,
        "required": True,
    },
    # WAN VAE
    "vae/wan_2.1_vae.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
        "size_gb": 0.2,
        "required": True,
    },
    # LightX2V Distillation LoRA (enables 8-step fast generation)
    "loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors": {
        "url": "https://huggingface.co/lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v/resolve/main/loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
        "size_gb": 0.7,
        "required": True,
    },
}


def print_status(message: str, status: str = "info"):
    """Print a status message with color."""
    colors = {
        "info": "\033[94m",
        "success": "\033[92m",
        "warning": "\033[93m",
        "error": "\033[91m",
        "progress": "\033[96m",
    }
    icons = {
        "info": "[i]",
        "success": "[+]",
        "warning": "[!]",
        "error": "[x]",
        "progress": "[*]",
    }
    reset = "\033[0m"
    color = colors.get(status, "")
    icon = icons.get(status, "")
    print(f"{color}{icon} {message}{reset}")


def run_command(cmd: list, cwd: Path = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as e:
        print_status(f"Command failed: {' '.join(cmd)}", "error")
        print_status(f"Error: {e.stderr}", "error")
        raise


def check_python():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print_status(f"Python 3.10+ required, found {version.major}.{version.minor}", "error")
        return False
    print_status(f"Python {version.major}.{version.minor}.{version.micro}", "success")
    return True


def check_git():
    """Check if git is available."""
    try:
        result = run_command(["git", "--version"], check=False)
        if result.returncode == 0:
            print_status(f"Git: {result.stdout.strip()}", "success")
            return True
    except FileNotFoundError:
        pass
    print_status("Git not found. Please install git.", "error")
    return False


def check_cuda():
    """Check for CUDA availability."""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print_status(f"CUDA: {device_name} ({vram:.1f}GB VRAM)", "success")
            if vram < 10:
                print_status(f"Warning: 10GB+ VRAM recommended for WAN 2.2 Q4_K_M", "warning")
            return True
        else:
            print_status("CUDA not available", "warning")
            return False
    except ImportError:
        print_status("PyTorch not installed yet", "info")
        return None


def clone_or_update_repo(url: str, target: Path, name: str):
    """Clone a git repo or update if exists."""
    if target.exists():
        print_status(f"{name} already exists, updating...", "progress")
        run_command(["git", "pull"], cwd=target)
        print_status(f"{name} updated", "success")
    else:
        print_status(f"Cloning {name}...", "progress")
        run_command(["git", "clone", url, str(target)])
        print_status(f"{name} cloned", "success")


def setup_comfyui(comfyui_dir: Path):
    """Set up ComfyUI installation."""
    print_status("Setting up ComfyUI...", "progress")

    # Clone ComfyUI
    clone_or_update_repo(COMFYUI_REPO, comfyui_dir, "ComfyUI")

    # Install requirements
    print_status("Installing ComfyUI dependencies...", "progress")

    pip_cmd = [sys.executable, "-m", "pip"]

    # Install PyTorch with CUDA
    print_status("Installing PyTorch with CUDA support...", "progress")
    run_command([
        *pip_cmd, "install",
        "torch", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu124"
    ])

    # Install ComfyUI requirements
    requirements_file = comfyui_dir / "requirements.txt"
    if requirements_file.exists():
        run_command([*pip_cmd, "install", "-r", str(requirements_file)])

    # Install additional dependencies
    run_command([*pip_cmd, "install", "websocket-client", "requests"])

    print_status("ComfyUI dependencies installed", "success")


def setup_custom_nodes(comfyui_dir: Path):
    """Install required custom nodes."""
    print_status("Setting up custom nodes...", "progress")

    custom_nodes_dir = comfyui_dir / "custom_nodes"
    custom_nodes_dir.mkdir(exist_ok=True)

    for name, url in CUSTOM_NODES.items():
        node_dir = custom_nodes_dir / name
        clone_or_update_repo(url, node_dir, name)

        # Install node requirements if exists
        req_file = node_dir / "requirements.txt"
        if req_file.exists():
            print_status(f"Installing {name} dependencies...", "progress")
            try:
                run_command([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
            except subprocess.CalledProcessError:
                print_status(f"Some {name} dependencies failed, trying with --user...", "warning")
                run_command([sys.executable, "-m", "pip", "install", "--user", "-r", str(req_file)], check=False)

    # Install additional pip packages
    if ADDITIONAL_PIP_PACKAGES:
        print_status("Installing additional dependencies...", "progress")
        try:
            run_command([sys.executable, "-m", "pip", "install", "--user"] + ADDITIONAL_PIP_PACKAGES)
        except subprocess.CalledProcessError:
            print_status("Some additional packages failed to install", "warning")

    print_status("Custom nodes installed", "success")


def download_file(url: str, target: Path, desc: str = None):
    """Download a file with progress indication."""
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        print_status(f"Already exists: {target.name}", "success")
        return True

    desc = desc or target.name
    print_status(f"Downloading {desc}...", "progress")

    try:
        urllib.request.urlretrieve(url, str(target))
        print_status(f"Downloaded: {target.name}", "success")
        return True
    except Exception as e:
        print_status(f"Failed to download {desc}: {e}", "error")
        return False


def download_models(comfyui_dir: Path):
    """Download required models."""
    print_status("Downloading models (this may take a while)...", "progress")

    models_dir = comfyui_dir / "models"

    # Calculate total size
    total_size = sum(m["size_gb"] for m in MODELS.values() if m["required"])
    print_status(f"Total download size: ~{total_size:.1f}GB", "info")

    for path, info in MODELS.items():
        if info["required"]:
            target = models_dir / path
            if not download_file(info["url"], target, path):
                return False

    print_status("Models downloaded", "success")
    return True


def check_setup(comfyui_dir: Path) -> dict:
    """Check if setup is complete."""
    status = {
        "comfyui": comfyui_dir.exists(),
        "custom_nodes": {},
        "models": {},
        "ready": False,
    }

    if status["comfyui"]:
        custom_nodes_dir = comfyui_dir / "custom_nodes"
        for name in CUSTOM_NODES:
            status["custom_nodes"][name] = (custom_nodes_dir / name).exists()

    if status["comfyui"]:
        models_dir = comfyui_dir / "models"
        for path, info in MODELS.items():
            if info["required"]:
                status["models"][path] = (models_dir / path).exists()

    status["ready"] = (
        status["comfyui"] and
        all(status["custom_nodes"].values()) and
        all(status["models"].values())
    )

    return status


def print_setup_status(status: dict):
    """Print setup status."""
    print("\n" + "="*50)
    print("Setup Status")
    print("="*50)

    if status["comfyui"]:
        print_status("ComfyUI installed", "success")
    else:
        print_status("ComfyUI not installed", "error")

    print("\nCustom Nodes:")
    for name, installed in status["custom_nodes"].items():
        if installed:
            print_status(f"  {name}", "success")
        else:
            print_status(f"  {name}", "error")

    print("\nModels:")
    for path, exists in status["models"].items():
        name = Path(path).name
        if exists:
            print_status(f"  {name}", "success")
        else:
            print_status(f"  {name}", "error")

    print("\n" + "="*50)
    if status["ready"]:
        print_status("Setup complete! Ready to generate videos.", "success")
    else:
        print_status("Setup incomplete. Run: python setup_comfyui.py", "warning")
    print("="*50 + "\n")


def start_comfyui(comfyui_dir: Path, port: int = 8188):
    """Start ComfyUI server."""
    if not comfyui_dir.exists():
        print_status("ComfyUI not installed. Run setup first.", "error")
        return False

    print_status(f"Starting ComfyUI on port {port}...", "progress")
    print_status("Press Ctrl+C to stop", "info")
    print_status(f"Web UI: http://localhost:{port}", "info")

    main_py = comfyui_dir / "main.py"

    try:
        subprocess.run(
            [sys.executable, str(main_py), "--listen", "0.0.0.0", "--port", str(port)],
            cwd=comfyui_dir,
        )
    except KeyboardInterrupt:
        print_status("ComfyUI stopped", "info")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Setup ComfyUI for WAN 2.2 video generation"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check setup status only"
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start ComfyUI server"
    )
    parser.add_argument(
        "--models",
        action="store_true",
        help="Download models only"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=COMFYUI_DIR,
        help=f"ComfyUI installation directory (default: {COMFYUI_DIR})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8188,
        help="ComfyUI server port (default: 8188)"
    )

    args = parser.parse_args()
    comfyui_dir = args.dir

    print("\n" + "="*50)
    print("ComfyUI Setup for WAN 2.2 Video Generation")
    print(f"Install directory: {comfyui_dir}")
    print("="*50 + "\n")

    # Check only
    if args.check:
        status = check_setup(comfyui_dir)
        print_setup_status(status)
        return 0 if status["ready"] else 1

    # Start server
    if args.start:
        start_comfyui(comfyui_dir, args.port)
        return 0

    # Download models only
    if args.models:
        if not comfyui_dir.exists():
            print_status("ComfyUI not installed. Run full setup first.", "error")
            return 1
        download_models(comfyui_dir)
        return 0

    # Full setup
    print_status("Checking system requirements...", "progress")

    if not check_python():
        return 1

    if not check_git():
        return 1

    check_cuda()

    print()

    # Setup ComfyUI
    setup_comfyui(comfyui_dir)

    # Setup custom nodes
    setup_custom_nodes(comfyui_dir)

    # Download models
    if not download_models(comfyui_dir):
        print_status("Model download failed. Run again with --models", "error")
        return 1

    # Final status
    status = check_setup(comfyui_dir)
    print_setup_status(status)

    if status["ready"]:
        print_status("To start ComfyUI, run:", "info")
        print(f"  python scripts/setup_comfyui.py --start")

    return 0 if status["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
