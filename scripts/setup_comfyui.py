#!/usr/bin/env python3
"""
Auto-setup script for ComfyUI with WAN 2.2 video generation and SD 3.5 keyframe generation.
Downloads and configures everything needed to run the AI video skill.

Uses SD 3.5 Large (GGUF quantized) for keyframe generation with ControlNet and IP-Adapter
for character consistency across frames.

Usage:
    python setup_comfyui.py              # Full setup
    python setup_comfyui.py --check      # Check if setup is complete
    python setup_comfyui.py --start      # Start ComfyUI server
    python setup_comfyui.py --models     # Download models only
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


# Configuration
COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI.git"
COMFYUI_DIR = Path("D:/comfyui")

CUSTOM_NODES = {
    "ComfyUI-GGUF": "https://github.com/city96/ComfyUI-GGUF.git",
    "ComfyUI-VideoHelperSuite": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
    "ComfyUI-Manager": "https://github.com/ltdrdata/ComfyUI-Manager.git",
    # SD 3.5 IP-Adapter for character consistency
    "ComfyUI-InstantX-IPAdapter-SD3": "https://github.com/Slickytail/ComfyUI-InstantX-IPAdapter-SD3.git",
}

# Model URLs and paths (relative to ComfyUI/models/)
MODELS = {
    # ===========================================
    # WAN 2.2 Models (Video Generation)
    # ===========================================
    # WAN 2.2 GGUF models (Q4_K_M for 10GB VRAM)
    "diffusion_models/wan2.2_i2v_low_noise_14B_Q4_K_M.gguf": {
        "url": "https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/wan2.2_i2v_low_noise_14B_Q4_K_M.gguf",
        "size_gb": 8.5,
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
    # LightX2V Distillation LoRA (enables 8-step fast generation with CFG 1.0)
    "loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors": {
        "url": "https://huggingface.co/lightx2v/Wan2.1-I2V-14B-480P-StepDistill-CfgDistill-Lightx2v/resolve/main/loras/Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
        "size_gb": 0.7,
        "required": True,
    },
    # ===========================================
    # SD 3.5 Models (Keyframe/Image Generation)
    # ===========================================
    # SD 3.5 Large GGUF (Q4 quantization for 10GB VRAM)
    "unet/sd3.5_large-Q4_0.gguf": {
        "url": "https://huggingface.co/city96/stable-diffusion-3.5-large-gguf/resolve/main/sd3.5_large-Q4_0.gguf",
        "size_gb": 4.8,
        "required": True,
    },
    # SD 3.5 Text encoders (shared T5 already downloaded for WAN)
    "clip/clip_g.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/resolve/main/text_encoders/clip_g.safetensors",
        "size_gb": 1.4,
        "required": True,
    },
    "clip/clip_l.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/resolve/main/text_encoders/clip_l.safetensors",
        "size_gb": 0.2,
        "required": True,
    },
    "clip/t5xxl_fp8_e4m3fn.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/stable-diffusion-3.5-fp8/resolve/main/text_encoders/t5xxl_fp8_e4m3fn.safetensors",
        "size_gb": 4.9,
        "required": True,
    },
    # SD 3.5 VAE (same as SD3, public mirror)
    "vae/sd3.5_vae.safetensors": {
        "url": "https://huggingface.co/diffusers-internal-dev/private-model/resolve/6e465cb8e03ddd0e34adf401d12d756c7c056ed1/sd3_vae.safetensors",
        "size_gb": 0.2,
        "required": True,
    },
    # ===========================================
    # SD 3.5 ControlNet (Consistency Tools) - from public mirror
    # ===========================================
    "controlnet/sd3.5_large_controlnet_canny.safetensors": {
        "url": "https://huggingface.co/licyk/sd3_controlnet/resolve/main/sd3.5_large_controlnet_canny.safetensors",
        "size_gb": 8.7,
        "required": False,  # Optional - canny edge detection
    },
    "controlnet/sd3.5_large_controlnet_depth.safetensors": {
        "url": "https://huggingface.co/licyk/sd3_controlnet/resolve/main/sd3.5_large_controlnet_depth.safetensors",
        "size_gb": 8.7,
        "required": True,  # Required for spatial consistency
    },
    # ===========================================
    # SD 3.5 IP-Adapter (Character Consistency)
    # ===========================================
    "ipadapter/ip-adapter-sd3.bin": {
        "url": "https://huggingface.co/InstantX/SD3.5-Large-IP-Adapter/resolve/main/ip-adapter.bin",
        "size_gb": 1.0,
        "required": True,
    },
    "clip_vision/siglip_vision_patch14_384.safetensors": {
        "url": "https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors",
        "size_gb": 0.9,
        "required": True,
    },
}


def print_status(message: str, status: str = "info"):
    """Print a status message with color."""
    colors = {
        "info": "\033[94m",      # Blue
        "success": "\033[92m",   # Green
        "warning": "\033[93m",   # Yellow
        "error": "\033[91m",     # Red
        "progress": "\033[96m",  # Cyan
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

    # Determine pip command
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
            run_command([sys.executable, "-m", "pip", "install", "-r", str(req_file)])

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
        # Simple download with urllib
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

    # Download WAN models
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

    # Check custom nodes
    if status["comfyui"]:
        custom_nodes_dir = comfyui_dir / "custom_nodes"
        for name in CUSTOM_NODES:
            status["custom_nodes"][name] = (custom_nodes_dir / name).exists()

    # Check models
    if status["comfyui"]:
        models_dir = comfyui_dir / "models"
        for path, info in MODELS.items():
            if info["required"]:
                status["models"][path] = (models_dir / path).exists()

    # Overall ready status
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

    # ComfyUI
    if status["comfyui"]:
        print_status("ComfyUI installed", "success")
    else:
        print_status("ComfyUI not installed", "error")

    # Custom nodes
    print("\nCustom Nodes:")
    for name, installed in status["custom_nodes"].items():
        if installed:
            print_status(f"  {name}", "success")
        else:
            print_status(f"  {name}", "error")

    # Models
    print("\nModels:")
    for path, exists in status["models"].items():
        name = Path(path).name
        if exists:
            print_status(f"  {name}", "success")
        else:
            print_status(f"  {name}", "error")

    print("\n" + "="*50)
    if status["ready"]:
        print_status("Setup complete! Ready to generate keyframes and videos.", "success")
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
        description="Setup ComfyUI for AI video production (SD 3.5 keyframes + WAN 2.2 video)"
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
    print("AI Video Producer Setup")
    print("(SD 3.5 for keyframes + WAN 2.2 for video)")
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

    check_cuda()  # Warning only, not required

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
        print(f"  python {__file__} --start")
        print()
        print_status("Or start manually:", "info")
        print(f"  cd {comfyui_dir}")
        print(f"  python main.py --listen 0.0.0.0 --port 8188")

    return 0 if status["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
