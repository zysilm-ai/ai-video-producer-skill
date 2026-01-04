#!/usr/bin/env python3
"""
Core utilities for AI Video Producer image generation.
Shared functionality for asset generation, keyframe generation, and pose extraction.

This module preserves all existing GGUF, LoRA, and memory management logic
from qwen_image_comfyui.py while providing a cleaner API for new scripts.
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional, Callable, Any

from comfyui_client import (
    ComfyUIClient,
    ComfyUIError,
    WorkflowValidationError,
    load_workflow,
)
from utils import (
    load_style_config,
    ensure_output_dir,
    print_status,
    format_duration,
    build_enhanced_prompt,
)


# =============================================================================
# Model Constants (preserved from qwen_image_comfyui.py)
# =============================================================================

WORKFLOW_DIR = Path(__file__).parent / "workflows"

# GGUF model variants (file must be in ComfyUI diffusion_models folder)
GGUF_VARIANTS = {
    "q2_k": "qwen-image-edit-2511-Q2_K.gguf",      # ~7GB - fastest, lower quality
    "q3_k_m": "qwen-image-edit-2511-Q3_K_M.gguf",  # ~10GB
    "q4_k_m": "qwen-image-edit-2511-Q4_K_M.gguf",  # ~13GB - recommended
    "q5_k_m": "qwen-image-edit-2511-Q5_K_M.gguf",  # ~15GB
    "q6_k": "qwen-image-edit-2511-Q6_K.gguf",      # ~17GB - best quality/speed
    "q8_0": "qwen-image-edit-2511-Q8_0.gguf",      # ~22GB - highest quality
}

# Lightning LoRA for fast 4-step generation
LIGHTNING_LORA = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"

# Resolution presets
RESOLUTION_PRESETS = {
    "low": {"width": 640, "height": 384},
    "medium": {"width": 832, "height": 480},
    "high": {"width": 1280, "height": 720},
}

# Default negative prompt
DEFAULT_NEGATIVE = "bad quality, worst quality, blurry, distorted, deformed, ugly, low resolution, poorly drawn"

# Workflow paths
T2I_WORKFLOW = WORKFLOW_DIR / "qwen_t2i.json"
EDIT_WORKFLOW = WORKFLOW_DIR / "qwen_edit.json"
POSE_WORKFLOW = WORKFLOW_DIR / "qwen_pose.json"
DWPOSE_WORKFLOW = WORKFLOW_DIR / "dwpose_extract.json"


# =============================================================================
# Workflow Update Functions (preserved from qwen_image_comfyui.py)
# =============================================================================

def update_workflow_model(workflow: dict, model_name: str, lora_name: str) -> dict:
    """Update model and LoRA names in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})

        # Update GGUF model name
        if "unet_name" in inputs and "{{MODEL_NAME}}" in str(inputs.get("unet_name", "")):
            workflow[node_id]["inputs"]["unet_name"] = model_name
        elif inputs.get("unet_name") == "{{MODEL_NAME}}":
            workflow[node_id]["inputs"]["unet_name"] = model_name

        # Update LoRA name
        if "lora_name" in inputs and "{{LORA_NAME}}" in str(inputs.get("lora_name", "")):
            workflow[node_id]["inputs"]["lora_name"] = lora_name
        elif inputs.get("lora_name") == "{{LORA_NAME}}":
            workflow[node_id]["inputs"]["lora_name"] = lora_name

    return workflow


def update_workflow_prompts(
    workflow: dict,
    prompt: str,
    negative_prompt: str = None
) -> dict:
    """Update text prompts in workflow."""
    if negative_prompt is None:
        negative_prompt = DEFAULT_NEGATIVE

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})

        # Update positive prompt
        if inputs.get("prompt") == "{{PROMPT}}":
            workflow[node_id]["inputs"]["prompt"] = prompt

        # Update negative prompt
        if inputs.get("text") == "{{NEGATIVE_PROMPT}}":
            workflow[node_id]["inputs"]["text"] = negative_prompt

    return workflow


def update_workflow_images(
    workflow: dict,
    reference: str = None,
    pose: str = None
) -> dict:
    """Update image inputs in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs", {})
        title = node.get("_meta", {}).get("title", "").lower()

        if node.get("class_type") == "LoadImage":
            current_image = str(inputs.get("image", ""))

            # Reference image
            if "{{REFERENCE}}" in current_image or "reference" in title:
                if reference:
                    workflow[node_id]["inputs"]["image"] = reference

            # Pose image
            if "{{POSE}}" in current_image or "pose" in title:
                if pose:
                    workflow[node_id]["inputs"]["image"] = pose

    return workflow


def update_workflow_resolution(
    workflow: dict,
    width: int = None,
    height: int = None,
) -> dict:
    """Update resolution parameters in workflow."""
    resolution_nodes = [
        "EmptyQwenImageLayeredLatentImage",
        "EmptySD3LatentImage",
        "ImageScale",
        "OpenposePreprocessor",
        "DWPreprocessor",
    ]

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        if class_type in resolution_nodes:
            if width is not None and "width" in inputs:
                workflow[node_id]["inputs"]["width"] = width
            if height is not None and "height" in inputs:
                workflow[node_id]["inputs"]["height"] = height
            # OpenposePreprocessor/DWPreprocessor uses 'resolution' instead of width/height
            if class_type in ["OpenposePreprocessor", "DWPreprocessor"] and width is not None:
                workflow[node_id]["inputs"]["resolution"] = width

    return workflow


def update_workflow_sampler(
    workflow: dict,
    steps: int = None,
    cfg: float = None,
    seed: int = None,
    shift: float = None,
) -> dict:
    """Update sampler and flow matching parameters in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # Update KSampler
        if class_type == "KSampler":
            if steps is not None:
                workflow[node_id]["inputs"]["steps"] = steps
            if cfg is not None:
                workflow[node_id]["inputs"]["cfg"] = cfg
            if seed is not None and seed > 0:
                workflow[node_id]["inputs"]["seed"] = seed

        # Update ModelSamplingAuraFlow (shift parameter)
        if class_type == "ModelSamplingAuraFlow":
            if shift is not None:
                workflow[node_id]["inputs"]["shift"] = shift

    return workflow


def update_workflow_controlnet(
    workflow: dict,
    control_strength: float = None,
) -> dict:
    """Update ControlNet strength in workflow."""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        class_type = node.get("class_type", "")

        if class_type == "ControlNetApplySD3":
            if control_strength is not None:
                workflow[node_id]["inputs"]["strength"] = control_strength

    return workflow


# =============================================================================
# Image Generator Class
# =============================================================================

class QwenImageGenerator:
    """
    High-level interface for Qwen Image Edit generation.
    Wraps ComfyUI client with all GGUF/LoRA/memory management logic.
    """

    def __init__(
        self,
        gguf_variant: str = "q4_k_m",
        use_lightning: bool = True,
        resolution_preset: str = "medium",
    ):
        """
        Initialize generator.

        Args:
            gguf_variant: GGUF quantization variant (q2_k, q3_k_m, q4_k_m, q5_k_m, q6_k, q8_0)
            use_lightning: Use Lightning LoRA for fast 4-step generation
            resolution_preset: Resolution preset (low, medium, high)
        """
        self.client = ComfyUIClient()
        self.gguf_variant = gguf_variant
        self.use_lightning = use_lightning
        self.resolution_preset = resolution_preset

        # Validate GGUF variant
        if gguf_variant not in GGUF_VARIANTS:
            print_status(f"Unknown GGUF variant: {gguf_variant}, using q4_k_m", "warning")
            self.gguf_variant = "q4_k_m"

        # Get model names
        self.model_name = GGUF_VARIANTS[self.gguf_variant]
        self.lora_name = LIGHTNING_LORA if use_lightning else ""

        # Get resolution
        if resolution_preset in RESOLUTION_PRESETS:
            preset = RESOLUTION_PRESETS[resolution_preset]
            self.width = preset["width"]
            self.height = preset["height"]
        else:
            self.width = 832
            self.height = 480

    def is_available(self) -> bool:
        """Check if ComfyUI server is available."""
        return self.client.is_available()

    def free_memory(self) -> None:
        """Free GPU memory (useful when switching from WAN video)."""
        print_status("Freeing GPU memory before generation...", "*")
        self.client.free_memory()

    def _upload_image(self, image_path: str, description: str) -> str:
        """Upload image to ComfyUI and return uploaded name."""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"{description} not found: {image_path}")

        result = self.client.upload_image(image_path)
        uploaded_name = result["name"]
        print_status(f"Uploaded {description}: {uploaded_name}")
        return uploaded_name

    def generate(
        self,
        prompt: str,
        output_path: str,
        workflow_path: Path,
        reference_image: str = None,
        pose_image: str = None,
        control_strength: float = 0.9,
        width: int = None,
        height: int = None,
        seed: int = 0,
        steps: int = 4,
        cfg: float = 1.0,
        shift: float = 5.0,
        style_config: dict = None,
        timeout: int = 300,
        free_memory: bool = False,
    ) -> str:
        """
        Generate an image using specified workflow.

        Args:
            prompt: Text prompt describing the image
            output_path: Path to save generated image
            workflow_path: Path to workflow JSON file
            reference_image: Optional reference image for consistency
            pose_image: Optional pose image (skeleton) for ControlNet
            control_strength: ControlNet strength (0.0 - 1.0)
            width: Image width (or use preset)
            height: Image height (or use preset)
            seed: Random seed (0 for random)
            steps: Sampling steps (default 4 with Lightning)
            cfg: Guidance scale (default 1.0 with Lightning)
            shift: Flow matching shift (default 5.0)
            style_config: Optional style configuration dict
            timeout: Maximum wait time in seconds
            free_memory: Free GPU memory before generation

        Returns:
            Path to saved image
        """
        if not self.is_available():
            print_status("ComfyUI server not available!", "error")
            print_status("Please start ComfyUI: python scripts/setup_comfyui.py --start", "error")
            sys.exit(1)

        if free_memory:
            self.free_memory()

        # Use preset resolution if not specified
        if width is None:
            width = self.width
        if height is None:
            height = self.height

        # Build enhanced prompt
        enhanced_prompt = build_enhanced_prompt(prompt, style_config)
        print_status(f"Prompt: {enhanced_prompt[:100]}...")

        # Load workflow
        if not workflow_path.exists():
            print_status(f"Workflow not found: {workflow_path}", "error")
            sys.exit(1)

        try:
            workflow = load_workflow(str(workflow_path))
        except json.JSONDecodeError as e:
            print_status(f"Invalid workflow JSON: {e}", "error")
            sys.exit(1)

        # Upload images if needed
        ref_image_name = None
        pose_image_name = None

        if reference_image:
            print_status("Uploading reference image to ComfyUI...", "progress")
            ref_image_name = self._upload_image(reference_image, "reference")

        if pose_image:
            print_status("Uploading pose image to ComfyUI...", "progress")
            pose_image_name = self._upload_image(pose_image, "pose")

        # Update workflow with all parameters
        workflow = update_workflow_model(workflow, self.model_name, self.lora_name)
        workflow = update_workflow_prompts(workflow, enhanced_prompt)
        workflow = update_workflow_images(workflow, ref_image_name, pose_image_name)
        workflow = update_workflow_resolution(workflow, width, height)
        workflow = update_workflow_sampler(workflow, steps, cfg, seed, shift)
        workflow = update_workflow_controlnet(workflow, control_strength)

        # Execute workflow
        print_status("Submitting image generation request...", "progress")
        print_status(f"Model: {self.model_name}")
        if self.use_lightning:
            print_status("Using Lightning LoRA (4-step fast mode)")
        print_status(f"Settings: {width}x{height}, {steps} steps, CFG {cfg}, Shift {shift}")

        start_time = time.time()

        def on_progress(msg):
            elapsed = time.time() - start_time
            print_status(f"{msg} ({format_duration(elapsed)})", "progress")

        try:
            result = self.client.execute_workflow(
                workflow,
                timeout=timeout,
                on_progress=on_progress,
                validate=True,
            )

            # Get output images
            images = self.client.get_output_images(result)

            if not images:
                print_status("No image generated!", "error")
                sys.exit(1)

            # Download and save the first image
            output = ensure_output_dir(output_path)
            image_info = images[0]
            self.client.download_output(image_info, str(output))

            total_time = time.time() - start_time
            print_status(f"Image saved to: {output_path} ({format_duration(total_time)})", "success")

            return str(output)

        except WorkflowValidationError as e:
            print_status("Workflow validation failed:", "error")
            print(str(e))
            sys.exit(1)
        except ComfyUIError as e:
            print_status("ComfyUI error:", "error")
            print(str(e))
            sys.exit(1)
        except TimeoutError:
            print_status(f"Generation timed out after {timeout}s", "error")
            sys.exit(1)
        except Exception as e:
            print_status(f"Generation failed: {e}", "error")
            sys.exit(1)


# =============================================================================
# Pose Extraction
# =============================================================================

def extract_pose_skeleton(
    image_path: str,
    output_path: str,
    resolution: int = 832,
    detect_body: bool = True,
    detect_hand: bool = True,
    detect_face: bool = False,
    timeout: int = 120,
) -> str:
    """
    Extract pose skeleton from an image using DWPose.

    This uses the DWPose preprocessor to extract a stick-figure skeleton
    from any image (photo, artwork, etc.) for use as pose reference.

    Args:
        image_path: Path to source image
        output_path: Path to save skeleton image
        resolution: Processing resolution (default 832)
        detect_body: Detect body keypoints
        detect_hand: Detect hand keypoints
        detect_face: Detect face keypoints
        timeout: Maximum wait time

    Returns:
        Path to saved skeleton image
    """
    client = ComfyUIClient()

    if not client.is_available():
        print_status("ComfyUI server not available!", "error")
        sys.exit(1)

    if not Path(image_path).exists():
        print_status(f"Image not found: {image_path}", "error")
        sys.exit(1)

    # Check if DWPose workflow exists
    if not DWPOSE_WORKFLOW.exists():
        print_status(f"DWPose workflow not found: {DWPOSE_WORKFLOW}", "error")
        print_status("Please ensure dwpose_extract.json is in the workflows folder", "error")
        sys.exit(1)

    print_status(f"Extracting pose skeleton from: {image_path}")

    # Upload image
    try:
        result = client.upload_image(image_path)
        uploaded_name = result["name"]
        print_status(f"Uploaded: {uploaded_name}")
    except Exception as e:
        print_status(f"Failed to upload image: {e}", "error")
        sys.exit(1)

    # Load and update workflow
    workflow = load_workflow(str(DWPOSE_WORKFLOW))

    # Update image input
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "LoadImage":
            workflow[node_id]["inputs"]["image"] = uploaded_name

    # Update DWPose settings
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "DWPreprocessor":
            workflow[node_id]["inputs"]["detect_body"] = "enable" if detect_body else "disable"
            workflow[node_id]["inputs"]["detect_hand"] = "enable" if detect_hand else "disable"
            workflow[node_id]["inputs"]["detect_face"] = "enable" if detect_face else "disable"
            workflow[node_id]["inputs"]["resolution"] = resolution

    # Execute
    start_time = time.time()

    def on_progress(msg):
        elapsed = time.time() - start_time
        print_status(f"{msg} ({format_duration(elapsed)})", "progress")

    try:
        result = client.execute_workflow(
            workflow,
            timeout=timeout,
            on_progress=on_progress,
            validate=True,
        )

        images = client.get_output_images(result)
        if not images:
            print_status("No skeleton generated!", "error")
            sys.exit(1)

        output = ensure_output_dir(output_path)
        client.download_output(images[0], str(output))

        total_time = time.time() - start_time
        print_status(f"Skeleton saved to: {output_path} ({format_duration(total_time)})", "success")

        return str(output)

    except Exception as e:
        print_status(f"Skeleton extraction failed: {e}", "error")
        sys.exit(1)
