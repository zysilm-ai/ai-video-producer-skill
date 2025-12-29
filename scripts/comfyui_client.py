#!/usr/bin/env python3
"""
ComfyUI API Client for video generation workflows.
Handles workflow submission, progress tracking, and output retrieval.
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

try:
    import requests
    import websocket
except ImportError as e:
    print(f"Error: Required packages not installed: {e}", file=sys.stderr)
    print("Install with: pip install requests websocket-client", file=sys.stderr)
    sys.exit(1)

from utils import print_status, format_duration


class ComfyUIClient:
    """Client for interacting with ComfyUI API."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ):
        """
        Initialize ComfyUI client.

        Args:
            host: ComfyUI server host (default: from env or 127.0.0.1)
            port: ComfyUI server port (default: from env or 8188)
        """
        self.host = host or os.environ.get("COMFYUI_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("COMFYUI_PORT", "8188"))
        self.base_url = f"http://{self.host}:{self.port}"
        self.client_id = str(uuid.uuid4())

    def is_available(self) -> bool:
        """Check if ComfyUI server is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_system_stats(self) -> dict:
        """Get system stats from ComfyUI server."""
        response = requests.get(f"{self.base_url}/system_stats", timeout=10)
        response.raise_for_status()
        return response.json()

    def upload_image(self, image_path: str, subfolder: str = "") -> dict:
        """
        Upload an image to ComfyUI for use in workflows.

        Args:
            image_path: Path to the image file
            subfolder: Optional subfolder in ComfyUI input directory

        Returns:
            Dict with 'name', 'subfolder', 'type' keys
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(path, "rb") as f:
            files = {
                "image": (path.name, f, "image/png"),
            }
            data = {}
            if subfolder:
                data["subfolder"] = subfolder

            response = requests.post(
                f"{self.base_url}/upload/image",
                files=files,
                data=data,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()

    def queue_prompt(self, workflow: dict) -> str:
        """
        Submit a workflow for execution.

        Args:
            workflow: ComfyUI workflow dict (API format)

        Returns:
            prompt_id for tracking the job
        """
        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
        }

        response = requests.post(
            f"{self.base_url}/prompt",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        if "error" in result:
            raise RuntimeError(f"Workflow error: {result['error']}")

        return result["prompt_id"]

    def get_history(self, prompt_id: str) -> dict:
        """
        Get execution history for a prompt.

        Args:
            prompt_id: The prompt ID returned from queue_prompt

        Returns:
            Dict with execution history and outputs
        """
        response = requests.get(
            f"{self.base_url}/history/{prompt_id}",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get_image(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> bytes:
        """
        Download an image from ComfyUI.

        Args:
            filename: Name of the image file
            subfolder: Subfolder within the folder type
            folder_type: 'input', 'output', or 'temp'

        Returns:
            Image bytes
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type,
        }

        response = requests.get(
            f"{self.base_url}/view?{urlencode(params)}",
            timeout=60,
        )
        response.raise_for_status()
        return response.content

    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: int = 600,
        poll_interval: float = 2.0,
        on_progress: callable | None = None,
    ) -> dict:
        """
        Wait for a prompt to complete execution.

        Args:
            prompt_id: The prompt ID to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks
            on_progress: Optional callback for progress updates

        Returns:
            Execution result from history
        """
        start_time = time.time()

        # Use WebSocket for real-time updates
        ws_url = f"ws://{self.host}:{self.port}/ws?clientId={self.client_id}"

        try:
            ws = websocket.WebSocket()
            ws.settimeout(poll_interval)
            ws.connect(ws_url)

            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Workflow timed out after {timeout}s")

                try:
                    message = ws.recv()
                    if message:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "executing":
                            node = data.get("data", {}).get("node")
                            if node is None:
                                # Execution complete
                                break
                            if on_progress:
                                on_progress(f"Executing node: {node}")

                        elif msg_type == "progress":
                            value = data.get("data", {}).get("value", 0)
                            max_val = data.get("data", {}).get("max", 100)
                            pct = int((value / max_val) * 100) if max_val > 0 else 0
                            if on_progress:
                                on_progress(f"Progress: {pct}%")

                        elif msg_type == "execution_error":
                            error = data.get("data", {})
                            raise RuntimeError(f"Execution error: {error}")

                except websocket.WebSocketTimeoutException:
                    # Check if already completed via history
                    history = self.get_history(prompt_id)
                    if prompt_id in history:
                        break

            ws.close()

        except Exception as e:
            # Fallback to polling if WebSocket fails
            print_status(f"WebSocket error, falling back to polling: {e}", "warning")
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Workflow timed out after {timeout}s")

                history = self.get_history(prompt_id)
                if prompt_id in history:
                    break

                if on_progress:
                    on_progress(f"Waiting... ({format_duration(elapsed)})")
                time.sleep(poll_interval)

        # Get final result
        history = self.get_history(prompt_id)
        if prompt_id not in history:
            raise RuntimeError("Prompt not found in history after completion")

        return history[prompt_id]

    def execute_workflow(
        self,
        workflow: dict,
        timeout: int = 600,
        on_progress: callable | None = None,
    ) -> dict:
        """
        Execute a workflow and wait for completion.

        Args:
            workflow: ComfyUI workflow dict (API format)
            timeout: Maximum time to wait in seconds
            on_progress: Optional callback for progress updates

        Returns:
            Execution result with outputs
        """
        if not self.is_available():
            raise ConnectionError(
                f"ComfyUI server not available at {self.base_url}. "
                "Please ensure ComfyUI is running."
            )

        prompt_id = self.queue_prompt(workflow)
        if on_progress:
            on_progress(f"Job queued: {prompt_id}")

        result = self.wait_for_completion(
            prompt_id,
            timeout=timeout,
            on_progress=on_progress,
        )

        return result

    def get_output_images(self, result: dict) -> list[dict]:
        """
        Extract output image info from execution result.

        Args:
            result: Execution result from execute_workflow

        Returns:
            List of dicts with filename, subfolder, type keys
        """
        images = []
        outputs = result.get("outputs", {})

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                images.extend(node_output["images"])

        return images

    def get_output_videos(self, result: dict) -> list[dict]:
        """
        Extract output video info from execution result.

        Args:
            result: Execution result from execute_workflow

        Returns:
            List of dicts with filename, subfolder, type keys
        """
        videos = []
        outputs = result.get("outputs", {})

        for node_id, node_output in outputs.items():
            # VideoHelperSuite uses 'gifs' key for video outputs
            if "gifs" in node_output:
                videos.extend(node_output["gifs"])
            # Some nodes use 'videos' key
            if "videos" in node_output:
                videos.extend(node_output["videos"])

        return videos

    def download_output(
        self,
        output_info: dict,
        save_path: str,
    ) -> str:
        """
        Download an output file and save it locally.

        Args:
            output_info: Dict with filename, subfolder, type keys
            save_path: Local path to save the file

        Returns:
            Path to saved file
        """
        content = self.get_image(
            filename=output_info["filename"],
            subfolder=output_info.get("subfolder", ""),
            folder_type=output_info.get("type", "output"),
        )

        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(content)

        return str(save_path)


def load_workflow(workflow_path: str) -> dict:
    """
    Load a ComfyUI workflow from JSON file.

    Args:
        workflow_path: Path to workflow JSON file

    Returns:
        Workflow dict
    """
    path = Path(workflow_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {workflow_path}")

    with open(path, "r") as f:
        return json.load(f)


def update_workflow_value(
    workflow: dict,
    node_id: str,
    field: str,
    value: Any,
) -> dict:
    """
    Update a value in a workflow node.

    Args:
        workflow: Workflow dict to modify
        node_id: ID of the node to update
        field: Field name within the node's inputs
        value: New value to set

    Returns:
        Modified workflow dict
    """
    if node_id not in workflow:
        raise KeyError(f"Node {node_id} not found in workflow")

    if "inputs" not in workflow[node_id]:
        workflow[node_id]["inputs"] = {}

    workflow[node_id]["inputs"][field] = value
    return workflow


# Convenience function for testing
def test_connection():
    """Test connection to ComfyUI server."""
    client = ComfyUIClient()

    print(f"Testing connection to {client.base_url}...")

    if client.is_available():
        stats = client.get_system_stats()
        print("Connected!")
        print(f"  Python version: {stats.get('system', {}).get('python_version', 'unknown')}")
        print(f"  ComfyUI version: {stats.get('system', {}).get('comfyui_version', 'unknown')}")

        devices = stats.get("devices", [])
        for i, device in enumerate(devices):
            print(f"  GPU {i}: {device.get('name', 'unknown')}")
            vram_total = device.get("vram_total", 0) / (1024**3)
            vram_free = device.get("vram_free", 0) / (1024**3)
            print(f"    VRAM: {vram_free:.1f}GB free / {vram_total:.1f}GB total")

        return True
    else:
        print("Failed to connect!")
        print("Make sure ComfyUI is running:")
        print("  python main.py --listen 0.0.0.0 --port 8188")
        return False


if __name__ == "__main__":
    test_connection()
