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
from typing import Any, Callable
from urllib.parse import urlencode

try:
    import requests
    import websocket
except ImportError as e:
    print(f"Error: Required packages not installed: {e}", file=sys.stderr)
    print("Install with: pip install requests websocket-client", file=sys.stderr)
    sys.exit(1)

from utils import print_status, format_duration


class ComfyUIError(Exception):
    """Base exception for ComfyUI errors."""
    pass


class WorkflowValidationError(ComfyUIError):
    """Raised when workflow validation fails."""
    pass


class NodeNotFoundError(ComfyUIError):
    """Raised when a required node type is not available."""
    pass


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
        self._object_info_cache = None

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

    def get_object_info(self, force_refresh: bool = False) -> dict:
        """
        Get available node types and their input/output specifications.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict mapping node class names to their specifications
        """
        if self._object_info_cache is None or force_refresh:
            response = requests.get(f"{self.base_url}/object_info", timeout=30)
            response.raise_for_status()
            self._object_info_cache = response.json()
        return self._object_info_cache

    def validate_workflow(self, workflow: dict) -> list[str]:
        """
        Validate a workflow against available nodes.

        Args:
            workflow: ComfyUI workflow dict

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Basic structure validation
        if not isinstance(workflow, dict):
            errors.append("Workflow must be a dictionary")
            return errors

        if not workflow:
            errors.append("Workflow is empty")
            return errors

        # Get available nodes
        try:
            object_info = self.get_object_info()
        except Exception as e:
            errors.append(f"Could not fetch node info: {e}")
            return errors

        available_nodes = set(object_info.keys())

        for node_id, node_data in workflow.items():
            # Skip non-dict entries (like _comment)
            if not isinstance(node_data, dict):
                continue

            # Check if node has class_type
            if "class_type" not in node_data:
                errors.append(f"Node '{node_id}' missing 'class_type'")
                continue

            class_type = node_data["class_type"]

            # Check if node type exists
            if class_type not in available_nodes:
                # Try to suggest similar nodes
                similar = [n for n in available_nodes if class_type.lower() in n.lower()]
                if similar:
                    errors.append(
                        f"Node '{node_id}': Unknown class_type '{class_type}'. "
                        f"Similar nodes: {', '.join(similar[:3])}"
                    )
                else:
                    errors.append(f"Node '{node_id}': Unknown class_type '{class_type}'")
                continue

            # Validate required inputs
            node_spec = object_info[class_type]
            required_inputs = node_spec.get("input", {}).get("required", {})
            node_inputs = node_data.get("inputs", {})

            for input_name, input_spec in required_inputs.items():
                if input_name not in node_inputs:
                    errors.append(
                        f"Node '{node_id}' ({class_type}): "
                        f"Missing required input '{input_name}'"
                    )

        return errors

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

    def queue_prompt(self, workflow: dict, validate: bool = True) -> str:
        """
        Submit a workflow for execution.

        Args:
            workflow: ComfyUI workflow dict (API format)
            validate: If True, validate workflow before submission

        Returns:
            prompt_id for tracking the job
        """
        # Validate workflow first
        if validate:
            errors = self.validate_workflow(workflow)
            if errors:
                error_msg = "Workflow validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
                raise WorkflowValidationError(error_msg)

        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
        }

        response = requests.post(
            f"{self.base_url}/prompt",
            json=payload,
            timeout=30,
        )

        # Handle error responses
        result = response.json()

        if "error" in result:
            error_info = result["error"]
            error_msg = self._format_error(error_info, result.get("node_errors", {}))
            raise ComfyUIError(f"Workflow submission failed:\n{error_msg}")

        if response.status_code != 200:
            raise ComfyUIError(f"Unexpected response: {response.status_code} - {response.text}")

        return result["prompt_id"]

    def _format_error(self, error: Any, node_errors: dict) -> str:
        """Format ComfyUI error into readable message."""
        lines = []

        if isinstance(error, dict):
            if "message" in error:
                lines.append(f"Error: {error['message']}")
            if "details" in error:
                lines.append(f"Details: {error['details']}")
        else:
            lines.append(f"Error: {error}")

        # Add node-specific errors
        if node_errors:
            lines.append("\nNode errors:")
            for node_id, node_error in node_errors.items():
                if isinstance(node_error, dict):
                    class_type = node_error.get("class_type", "unknown")
                    errors = node_error.get("errors", [])
                    lines.append(f"  Node '{node_id}' ({class_type}):")
                    for err in errors:
                        if isinstance(err, dict):
                            lines.append(f"    - {err.get('message', err)}")
                        else:
                            lines.append(f"    - {err}")
                else:
                    lines.append(f"  Node '{node_id}': {node_error}")

        return "\n".join(lines)

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

    def get_queue(self) -> dict:
        """
        Get current queue status.

        Returns:
            Dict with 'queue_running' and 'queue_pending' lists
        """
        response = requests.get(
            f"{self.base_url}/queue",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def free_memory(self, unload_models: bool = True, free_memory: bool = True) -> dict:
        """
        Free GPU memory by unloading models.

        Useful when switching between different model types (e.g., Qwen ↔ WAN)
        to avoid VRAM issues on constrained GPUs.

        Args:
            unload_models: Whether to unload all cached models
            free_memory: Whether to free cached memory

        Returns:
            Response from the server
        """
        try:
            response = requests.post(
                f"{self.base_url}/free",
                json={"unload_models": unload_models, "free_memory": free_memory},
                timeout=30,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except Exception as e:
            # Non-critical - just log and continue
            print_status(f"Warning: Could not free memory: {e}", "!")
            return {}

    def get_system_stats(self) -> dict:
        """
        Get system statistics including VRAM usage.

        Returns:
            Dict with device info, VRAM usage, etc.
        """
        response = requests.get(
            f"{self.base_url}/system_stats",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def is_prompt_in_queue(self, prompt_id: str) -> bool:
        """
        Check if a prompt is still in the queue (running or pending).

        Args:
            prompt_id: The prompt ID to check

        Returns:
            True if prompt is in queue, False if completed or not found
        """
        try:
            queue = self.get_queue()
            # Check running queue - format: [[priority, prompt_id, workflow, extra, outputs], ...]
            for item in queue.get("queue_running", []):
                if len(item) > 1 and item[1] == prompt_id:
                    return True
            # Check pending queue
            for item in queue.get("queue_pending", []):
                if len(item) > 1 and item[1] == prompt_id:
                    return True
            return False
        except Exception:
            return False

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
        on_progress: Callable | None = None,
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
        last_history_check = 0
        history_check_interval = 3.0  # Check history every 3 seconds

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

                # Periodic history check to catch completion even if websocket misses it
                if elapsed - last_history_check >= history_check_interval:
                    last_history_check = elapsed
                    try:
                        history = self.get_history(prompt_id)
                        if prompt_id in history and "outputs" in history[prompt_id]:
                            break
                    except Exception:
                        pass  # Ignore errors, continue with websocket

                try:
                    message = ws.recv()
                    if message:
                        data = json.loads(message)
                        msg_type = data.get("type")

                        if msg_type == "executing":
                            exec_data = data.get("data", {})
                            node = exec_data.get("node")
                            if node is None and exec_data.get("prompt_id") == prompt_id:
                                # Execution complete
                                break
                            if on_progress and node:
                                on_progress(f"Executing node: {node}")

                        elif msg_type == "progress":
                            value = data.get("data", {}).get("value", 0)
                            max_val = data.get("data", {}).get("max", 100)
                            pct = int((value / max_val) * 100) if max_val > 0 else 0
                            if on_progress:
                                on_progress(f"Progress: {pct}%")

                        elif msg_type == "execution_error":
                            error_data = data.get("data", {})
                            error_msg = self._format_execution_error(error_data)
                            raise ComfyUIError(f"Execution error:\n{error_msg}")

                except websocket.WebSocketTimeoutException:
                    # Check if job completed - first check queue, then history
                    in_queue = self.is_prompt_in_queue(prompt_id)

                    if not in_queue:
                        # Job not in queue - check history for results
                        history = self.get_history(prompt_id)
                        if prompt_id in history:
                            break
                        # If not in queue AND not in history, wait a bit for history to populate
                        time.sleep(0.5)
                        history = self.get_history(prompt_id)
                        if prompt_id in history:
                            break
                        # Still not in history - wait longer and try again
                        time.sleep(1.5)
                        history = self.get_history(prompt_id)
                        if prompt_id in history:
                            break

                    # Also check history even if in queue - might have completed between checks
                    # This handles race condition where completion message was missed
                    history = self.get_history(prompt_id)
                    if prompt_id in history:
                        result_status = history[prompt_id].get("status", {})
                        # Only break if status indicates completion (not still running)
                        if result_status.get("completed", False) or "outputs" in history[prompt_id]:
                            break

            ws.close()

        except TimeoutError:
            # Re-raise timeout errors - don't fall back to polling
            raise
        except (websocket.WebSocketException, OSError) as e:
            # Fallback to polling if WebSocket fails (but not for timeouts)
            print_status(f"WebSocket error, falling back to polling: {e}", "warning")
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Workflow timed out after {timeout}s")

                # Check queue first - more reliable than history during execution
                in_queue = self.is_prompt_in_queue(prompt_id)

                if not in_queue:
                    # Job not in queue - wait briefly for history to populate, then check
                    time.sleep(1)
                    history = self.get_history(prompt_id)
                    if prompt_id in history:
                        # Check for execution errors
                        status = history[prompt_id].get("status", {})
                        if status.get("status_str") == "error":
                            messages = status.get("messages", [])
                            error_msg = "\n".join(str(m) for m in messages)
                            raise ComfyUIError(f"Execution error:\n{error_msg}")
                        break

                if on_progress:
                    on_progress(f"Waiting... ({format_duration(elapsed)})")
                time.sleep(poll_interval)

        # Get final result
        history = self.get_history(prompt_id)
        if prompt_id not in history:
            raise ComfyUIError("Prompt not found in history after completion")

        result = history[prompt_id]

        # Check for errors in result
        status = result.get("status", {})
        if status.get("status_str") == "error":
            messages = status.get("messages", [])
            error_msg = "\n".join(str(m) for m in messages)
            raise ComfyUIError(f"Execution failed:\n{error_msg}")

        return result

    def _format_execution_error(self, error_data: dict) -> str:
        """Format execution error data into readable message."""
        lines = []

        exception_type = error_data.get("exception_type", "Unknown")
        exception_message = error_data.get("exception_message", "No details")
        node_id = error_data.get("node_id", "unknown")
        node_type = error_data.get("node_type", "unknown")

        lines.append(f"Node '{node_id}' ({node_type}) failed:")
        lines.append(f"  {exception_type}: {exception_message}")

        # Add traceback if available
        traceback = error_data.get("traceback", [])
        if traceback:
            lines.append("\nTraceback:")
            for line in traceback[-5:]:  # Last 5 lines
                lines.append(f"  {line.strip()}")

        return "\n".join(lines)

    def execute_workflow(
        self,
        workflow: dict,
        timeout: int = 600,
        on_progress: Callable | None = None,
        validate: bool = True,
    ) -> dict:
        """
        Execute a workflow and wait for completion.

        Args:
            workflow: ComfyUI workflow dict (API format)
            timeout: Maximum time to wait in seconds
            on_progress: Optional callback for progress updates
            validate: If True, validate workflow before submission

        Returns:
            Execution result with outputs
        """
        if not self.is_available():
            raise ConnectionError(
                f"ComfyUI server not available at {self.base_url}. "
                "Please ensure ComfyUI is running."
            )

        prompt_id = self.queue_prompt(workflow, validate=validate)
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
        workflow = json.load(f)

    # Filter out non-node entries like _comment
    return {k: v for k, v in workflow.items() if isinstance(v, dict)}


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


def find_node_by_title(workflow: dict, title: str) -> str | None:
    """
    Find a node ID by its title (from _meta).

    Args:
        workflow: Workflow dict
        title: Title to search for

    Returns:
        Node ID or None if not found
    """
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict):
            continue
        meta = node_data.get("_meta", {})
        if meta.get("title", "").lower() == title.lower():
            return node_id
    return None


def find_node_by_class(workflow: dict, class_type: str) -> str | None:
    """
    Find first node ID by class type.

    Args:
        workflow: Workflow dict
        class_type: Class type to search for

    Returns:
        Node ID or None if not found
    """
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict):
            continue
        if node_data.get("class_type") == class_type:
            return node_id
    return None


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

        # Test fetching object info
        print("\nFetching available nodes...")
        try:
            object_info = client.get_object_info()
            print(f"  {len(object_info)} node types available")

            # Check for WAN nodes
            wan_nodes = [n for n in object_info if "wan" in n.lower()]
            if wan_nodes:
                print(f"  WAN nodes found: {len(wan_nodes)}")
                for node in sorted(wan_nodes)[:10]:
                    print(f"    - {node}")
        except Exception as e:
            print(f"  Failed to fetch nodes: {e}")

        return True
    else:
        print("Failed to connect!")
        print("Make sure ComfyUI is running:")
        print("  python main.py --listen 0.0.0.0 --port 8188")
        return False


if __name__ == "__main__":
    test_connection()
