#!/usr/bin/env python3
"""
Execute pipeline.json for AI video production.

Provides deterministic execution of asset, keyframe, and video generation
based on a pre-defined pipeline JSON file.

Usage:
    # Execute specific stage
    python execute_pipeline.py pipeline.json --stage assets
    python execute_pipeline.py pipeline.json --stage keyframes
    python execute_pipeline.py pipeline.json --stage videos

    # Execute all stages
    python execute_pipeline.py pipeline.json --all

    # Regenerate specific item
    python execute_pipeline.py pipeline.json --regenerate KF-B

    # Check status
    python execute_pipeline.py pipeline.json --status

    # Validate pipeline
    python execute_pipeline.py pipeline.json --validate
"""

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import cv2

from video_merger import VideoMerger


class PipelineExecutor:
    """Executes a pipeline.json file for AI video production."""

    def __init__(self, pipeline_path: str, base_dir: Optional[str] = None):
        self.pipeline_path = Path(pipeline_path).resolve()

        # Base dir is where the scripts folder lives
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            # Assume pipeline is in output/project/ and scripts are in ../../scripts
            self.base_dir = self.pipeline_path.parent.parent.parent

        self.scripts_dir = self.base_dir / "scripts"
        self.pipeline = self._load_pipeline()
        self.output_dir = self.pipeline_path.parent  # pipeline.json lives in output dir
        self.video_merger = VideoMerger()
        self.pipeline_version = self._detect_version()

        print(f"Base dir: {self.base_dir}")
        print(f"Scripts dir: {self.scripts_dir}")
        print(f"Output dir: {self.output_dir}")
        print(f"Pipeline version: {self.pipeline_version}")

    def _load_pipeline(self) -> dict:
        """Load and parse pipeline.json."""
        with open(self.pipeline_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_pipeline(self):
        """Save pipeline.json with updated statuses."""
        with open(self.pipeline_path, 'w', encoding='utf-8') as f:
            json.dump(self.pipeline, f, indent=2, ensure_ascii=False)

    def _detect_version(self) -> str:
        """
        Detect pipeline schema version.

        Returns:
            "3.0" for scene/segment hierarchy
            "2.0" for video-first flat scenes
            "1.0" for keyframe-first legacy
        """
        version = self.pipeline.get("version", "1.0")

        # Check for v3.0 markers (segments in scenes)
        scenes = self.pipeline.get("scenes", [])
        if version == "3.0" or any("segments" in s for s in scenes):
            return "3.0"

        # Check for v2.0 markers (video-first)
        if version == "2.0" or "first_keyframe" in self.pipeline:
            return "2.0"

        # Default to legacy keyframe-first
        return "1.0"

    def _compute_scene_status(self, scene: dict) -> str:
        """
        Compute scene status from segment statuses (hierarchical).

        Args:
            scene: Scene dict with 'segments' list

        Returns:
            Computed status string
        """
        segments = scene.get("segments", [])
        if not segments:
            return scene.get("status", "pending")

        statuses = [s.get("status", "pending") for s in segments]

        if all(s == "approved" for s in statuses):
            return "approved"
        elif all(s in ["generated", "approved"] for s in statuses):
            return "generated"
        elif any(s == "failed" for s in statuses):
            return "failed"
        elif any(s == "in_progress" for s in statuses):
            return "in_progress"
        else:
            return "pending"

    def _update_asset_status(self, asset_type: str, item_id: str, status: str):
        """Update status for an asset item."""
        if asset_type in self.pipeline["assets"]:
            if item_id in self.pipeline["assets"][asset_type]:
                self.pipeline["assets"][asset_type][item_id]["status"] = status
                self._save_pipeline()

    def _update_keyframe_status(self, kf_id: str, status: str):
        """Update status for a keyframe."""
        for kf in self.pipeline["keyframes"]:
            if kf["id"] == kf_id:
                kf["status"] = status
                self._save_pipeline()
                return

    def _update_video_status(self, video_id: str, status: str):
        """Update status for a video."""
        for video in self.pipeline.get("videos", []):
            if video["id"] == video_id:
                video["status"] = status
                self._save_pipeline()
                return

    def _update_first_keyframe_status(self, status: str):
        """Update status for the first keyframe (video-first mode)."""
        if "first_keyframe" in self.pipeline:
            self.pipeline["first_keyframe"]["status"] = status
            self._save_pipeline()

    def _update_scene_status(self, scene_id: str, status: str):
        """Update status for a scene (video-first mode)."""
        for scene in self.pipeline.get("scenes", []):
            if scene["id"] == scene_id:
                scene["status"] = status
                self._save_pipeline()
                return

    def _update_segment_status(self, scene_id: str, segment_id: str, status: str):
        """Update status for a segment within a scene (v3.0)."""
        for scene in self.pipeline.get("scenes", []):
            if scene["id"] == scene_id:
                for segment in scene.get("segments", []):
                    if segment["id"] == segment_id:
                        segment["status"] = status
                        self._save_pipeline()
                        return

    def _update_scene_keyframe_status(self, scene_id: str, status: str):
        """Update status for a scene's first keyframe (v3.0)."""
        for scene in self.pipeline.get("scenes", []):
            if scene["id"] == scene_id:
                if "first_keyframe" in scene:
                    scene["first_keyframe"]["status"] = status
                    self._save_pipeline()
                return

    def _update_final_video_status(self, status: str):
        """Update status for final merged video (v3.0)."""
        if "final_video" in self.pipeline:
            self.pipeline["final_video"]["status"] = status
            self._save_pipeline()

    def _extract_last_frame(self, video_path: str, output_path: str) -> bool:
        """
        Extract the last frame from a video file.

        Args:
            video_path: Path to input video
            output_path: Path to save extracted frame

        Returns:
            True if successful, False otherwise
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"    [FAIL] Could not open video: {video_path}")
                return False

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                print(f"    [FAIL] Video has no frames: {video_path}")
                cap.release()
                return False

            # Seek to last frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
            ret, frame = cap.read()

            # If last frame is mostly black, try second-to-last
            if ret and frame is not None and frame.mean() < 10:
                print(f"    [WARN] Last frame appears black, trying second-to-last")
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 2)
                ret, frame = cap.read()

            cap.release()

            if not ret or frame is None:
                print(f"    [FAIL] Could not read frame from video")
                return False

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Save frame as PNG
            cv2.imwrite(output_path, frame)
            print(f"    [OK] Extracted last frame to: {Path(output_path).name}")
            return True

        except Exception as e:
            print(f"    [FAIL] Frame extraction error: {e}")
            return False

    def _run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and return success status."""
        print(f"    Command: {' '.join(cmd[:3])}...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900  # 15 min timeout
            )

            if result.returncode == 0:
                print(f"    [OK] Success")
                return True
            else:
                print(f"    [FAIL] Exit code {result.returncode}")
                if result.stderr:
                    print(f"    Error: {result.stderr[:500]}")
                return False

        except subprocess.TimeoutExpired:
            print(f"    [FAIL] Timeout after 15 minutes")
            return False
        except Exception as e:
            print(f"    [FAIL] Exception: {e}")
            return False

    def execute_assets(self):
        """Generate all assets (characters, backgrounds, styles)."""
        print("\n" + "=" * 60)
        print("STAGE: ASSETS")
        print("=" * 60)

        assets = self.pipeline.get("assets", {})

        # Characters
        characters = assets.get("characters", {})
        if characters:
            print(f"\n--- Characters ({len(characters)} items) ---")
            for char_id, char_data in characters.items():
                if char_data.get("status") in ["generated", "approved"]:
                    print(f"  [{char_data['status']}] {char_id} - skipping")
                    continue

                output_path = self.output_dir / char_data["output"]
                output_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = [
                    sys.executable,
                    str(self.scripts_dir / "asset_generator.py"),
                    "character",
                    "--name", char_id,
                    "--description", char_data["prompt"],
                    "--output", str(output_path),
                    "--free-memory"
                ]

                print(f"  [pending] {char_id} - generating...")
                if self._run_command(cmd, f"character {char_id}"):
                    self._update_asset_status("characters", char_id, "generated")
                else:
                    self._update_asset_status("characters", char_id, "failed")

        # Backgrounds
        backgrounds = assets.get("backgrounds", {})
        if backgrounds:
            print(f"\n--- Backgrounds ({len(backgrounds)} items) ---")
            for bg_id, bg_data in backgrounds.items():
                if bg_data.get("status") in ["generated", "approved"]:
                    print(f"  [{bg_data['status']}] {bg_id} - skipping")
                    continue

                output_path = self.output_dir / bg_data["output"]
                output_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = [
                    sys.executable,
                    str(self.scripts_dir / "asset_generator.py"),
                    "background",
                    "--name", bg_id,
                    "--description", bg_data["prompt"],
                    "--output", str(output_path),
                    "--free-memory"
                ]

                print(f"  [pending] {bg_id} - generating...")
                if self._run_command(cmd, f"background {bg_id}"):
                    self._update_asset_status("backgrounds", bg_id, "generated")
                else:
                    self._update_asset_status("backgrounds", bg_id, "failed")

        # Styles
        styles = assets.get("styles", {})
        if styles:
            print(f"\n--- Styles ({len(styles)} items) ---")
            for style_id, style_data in styles.items():
                if style_data.get("status") in ["generated", "approved"]:
                    print(f"  [{style_data['status']}] {style_id} - skipping")
                    continue

                output_path = self.output_dir / style_data["output"]
                output_path.parent.mkdir(parents=True, exist_ok=True)

                cmd = [
                    sys.executable,
                    str(self.scripts_dir / "asset_generator.py"),
                    "style",
                    "--name", style_id,
                    "--description", style_data["prompt"],
                    "--output", str(output_path),
                    "--free-memory"
                ]

                print(f"  [pending] {style_id} - generating...")
                if self._run_command(cmd, f"style {style_id}"):
                    self._update_asset_status("styles", style_id, "generated")
                else:
                    self._update_asset_status("styles", style_id, "failed")

        print("\n--- Assets stage complete ---")

    def execute_keyframes(self):
        """Generate all keyframes."""
        print("\n" + "=" * 60)
        print("STAGE: KEYFRAMES")
        print("=" * 60)

        keyframes = self.pipeline.get("keyframes", [])
        print(f"\n--- Keyframes ({len(keyframes)} items) ---")

        for kf in keyframes:
            kf_id = kf["id"]

            if kf.get("status") in ["generated", "approved"]:
                print(f"  [{kf['status']}] {kf_id} - skipping")
                continue

            output_path = self.output_dir / kf["output"]
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build command
            cmd = [
                sys.executable,
                str(self.scripts_dir / "keyframe_generator.py"),
                "--free-memory",  # MANDATORY for every keyframe
                "--prompt", kf["prompt"],
                "--output", str(output_path)
            ]

            # Add background reference if specified
            if kf.get("background"):
                bg_id = kf["background"]
                bg_data = self.pipeline["assets"]["backgrounds"].get(bg_id, {})
                if bg_data:
                    bg_path = self.output_dir / bg_data["output"]
                    cmd.extend(["--background", str(bg_path)])

            # Add character references
            for char_id in kf.get("characters", []):
                char_data = self.pipeline["assets"]["characters"].get(char_id, {})
                if char_data:
                    char_path = self.output_dir / char_data["output"]
                    cmd.extend(["--character", str(char_path)])

            # Add settings
            settings = kf.get("settings", {})
            if "preset" in settings:
                cmd.extend(["--preset", settings["preset"]])

            print(f"  [pending] {kf_id} - generating...")
            if self._run_command(cmd, f"keyframe {kf_id}"):
                self._update_keyframe_status(kf_id, "generated")
            else:
                self._update_keyframe_status(kf_id, "failed")

        print("\n--- Keyframes stage complete ---")

    def execute_videos(self):
        """Generate all videos."""
        print("\n" + "=" * 60)
        print("STAGE: VIDEOS")
        print("=" * 60)

        videos = self.pipeline.get("videos", [])
        print(f"\n--- Videos ({len(videos)} items) ---")

        first_video = True
        for video in videos:
            video_id = video["id"]

            if video.get("status") in ["generated", "approved"]:
                print(f"  [{video['status']}] {video_id} - skipping")
                first_video = False  # Don't use --free-memory if we skipped
                continue

            output_path = self.output_dir / video["output"]
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Find start keyframe
            start_kf_id = video["start_keyframe"]
            start_kf = next((kf for kf in self.pipeline["keyframes"]
                           if kf["id"] == start_kf_id), None)

            if not start_kf:
                print(f"  [error] {video_id} - start keyframe {start_kf_id} not found")
                self._update_video_status(video_id, "failed")
                continue

            start_frame_path = self.output_dir / start_kf["output"]

            # Build command
            cmd = [
                sys.executable,
                str(self.scripts_dir / "wan_video_comfyui.py"),
                "--prompt", video["prompt"],
                "--start-frame", str(start_frame_path),
                "--output", str(output_path)
            ]

            # Add --free-memory only for first video (switching from image to video models)
            if first_video:
                cmd.insert(2, "--free-memory")
                first_video = False

            # Add end frame if specified
            if video.get("end_keyframe"):
                end_kf_id = video["end_keyframe"]
                end_kf = next((kf for kf in self.pipeline["keyframes"]
                              if kf["id"] == end_kf_id), None)
                if end_kf:
                    end_frame_path = self.output_dir / end_kf["output"]
                    cmd.extend(["--end-frame", str(end_frame_path)])

            print(f"  [pending] {video_id} - generating...")
            if self._run_command(cmd, f"video {video_id}"):
                self._update_video_status(video_id, "generated")
            else:
                self._update_video_status(video_id, "failed")

        print("\n--- Videos stage complete ---")

    def execute_first_keyframe(self):
        """Generate the first keyframe only (video-first mode)."""
        print("\n" + "=" * 60)
        print("STAGE: FIRST KEYFRAME (video-first mode)")
        print("=" * 60)

        first_kf = self.pipeline.get("first_keyframe")
        if not first_kf:
            print("  [ERROR] No 'first_keyframe' found in pipeline")
            print("  This pipeline may use the old keyframe-first schema.")
            return

        kf_id = first_kf["id"]

        if first_kf.get("status") in ["generated", "approved"]:
            print(f"  [{first_kf['status']}] {kf_id} - skipping")
            print("\n--- First keyframe stage complete ---")
            return

        output_path = self.output_dir / first_kf["output"]
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine keyframe type
        kf_type = first_kf.get("type", "character")

        if kf_type == "landscape":
            # Landscape keyframes use asset_generator.py background mode
            cmd = [
                sys.executable,
                str(self.scripts_dir / "asset_generator.py"),
                "background",
                "--name", kf_id,
                "--description", first_kf["prompt"],
                "--output", str(output_path),
                "--free-memory"
            ]
        else:
            # Character keyframes use keyframe_generator.py
            cmd = [
                sys.executable,
                str(self.scripts_dir / "keyframe_generator.py"),
                "--free-memory",
                "--prompt", first_kf["prompt"],
                "--output", str(output_path)
            ]

            # Add background reference if specified
            if first_kf.get("background"):
                bg_id = first_kf["background"]
                bg_data = self.pipeline.get("assets", {}).get("backgrounds", {}).get(bg_id, {})
                if bg_data:
                    bg_path = self.output_dir / bg_data["output"]
                    cmd.extend(["--background", str(bg_path)])

            # Add character references
            for char_id in first_kf.get("characters", []):
                char_data = self.pipeline.get("assets", {}).get("characters", {}).get(char_id, {})
                if char_data:
                    char_path = self.output_dir / char_data["output"]
                    cmd.extend(["--character", str(char_path)])

            # Add settings
            settings = first_kf.get("settings", {})
            if "preset" in settings:
                cmd.extend(["--preset", settings["preset"]])

        print(f"  [pending] {kf_id} ({kf_type}) - generating...")
        if self._run_command(cmd, f"first keyframe {kf_id}"):
            self._update_first_keyframe_status("generated")
        else:
            self._update_first_keyframe_status("failed")

        print("\n--- First keyframe stage complete ---")

    def execute_scenes(self):
        """Generate all scenes sequentially (video-first mode).

        For each scene:
        1. Use start keyframe (from first_keyframe or previous scene's output)
        2. Generate video with I2V mode
        3. Extract last frame as next scene's start keyframe
        """
        print("\n" + "=" * 60)
        print("STAGE: SCENES (video-first mode)")
        print("=" * 60)

        scenes = self.pipeline.get("scenes", [])
        if not scenes:
            print("  [ERROR] No 'scenes' found in pipeline")
            print("  This pipeline may use the old keyframe-first schema.")
            return

        print(f"\n--- Scenes ({len(scenes)} items) ---")

        # Build keyframe lookup: keyframe_id -> file path
        keyframe_paths = {}

        # First keyframe
        first_kf = self.pipeline.get("first_keyframe")
        if first_kf:
            keyframe_paths[first_kf["id"]] = self.output_dir / first_kf["output"]

        # Output keyframes from scenes (populated as we generate)
        for scene in scenes:
            if scene.get("output_keyframe"):
                # Map the output keyframe to a pseudo-ID based on scene
                # The next scene's start_keyframe references this
                scene_idx = scenes.index(scene)
                if scene_idx < len(scenes) - 1:
                    next_scene = scenes[scene_idx + 1]
                    next_start_kf = next_scene.get("start_keyframe")
                    if next_start_kf:
                        keyframe_paths[next_start_kf] = self.output_dir / scene["output_keyframe"]

        first_video = True
        for scene in scenes:
            scene_id = scene["id"]

            if scene.get("status") in ["generated", "approved"]:
                print(f"  [{scene['status']}] {scene_id} - skipping")
                first_video = False
                continue

            # Get start keyframe path
            start_kf_id = scene.get("start_keyframe")
            start_frame_path = keyframe_paths.get(start_kf_id)

            if not start_frame_path or not start_frame_path.exists():
                print(f"  [ERROR] {scene_id}: start keyframe '{start_kf_id}' not found at {start_frame_path}")
                self._update_scene_status(scene_id, "failed")
                print("  Stopping scene execution (sequential dependency)")
                return

            # Video output path
            video_output = self.output_dir / scene["output_video"]
            video_output.parent.mkdir(parents=True, exist_ok=True)

            # Build video generation command (I2V mode only)
            cmd = [
                sys.executable,
                str(self.scripts_dir / "wan_video_comfyui.py"),
                "--prompt", scene["motion_prompt"],
                "--start-frame", str(start_frame_path),
                "--output", str(video_output)
            ]

            # Add --free-memory only for first video
            if first_video:
                cmd.insert(2, "--free-memory")
                first_video = False

            print(f"  [pending] {scene_id} - generating video...")
            if not self._run_command(cmd, f"scene video {scene_id}"):
                self._update_scene_status(scene_id, "failed")
                print("  Stopping scene execution (sequential dependency)")
                return

            # Extract last frame for next scene
            if scene.get("output_keyframe"):
                kf_output = self.output_dir / scene["output_keyframe"]
                kf_output.parent.mkdir(parents=True, exist_ok=True)

                print(f"    Extracting last frame for next scene...")
                if not self._extract_last_frame(str(video_output), str(kf_output)):
                    print(f"    [WARN] Failed to extract keyframe, next scene may fail")

                # Update keyframe_paths for subsequent scenes
                scene_idx = scenes.index(scene)
                if scene_idx < len(scenes) - 1:
                    next_scene = scenes[scene_idx + 1]
                    next_start_kf = next_scene.get("start_keyframe")
                    if next_start_kf:
                        keyframe_paths[next_start_kf] = kf_output

            self._update_scene_status(scene_id, "generated")

        print("\n--- Scenes stage complete ---")

    # =========================================================================
    # V3.0 Scene/Segment Methods
    # =========================================================================

    def execute_scene_keyframes(self):
        """
        Generate starting keyframes for scenes with type='generated' (v3.0).

        Only generates keyframes for scenes where first_keyframe.type == "generated".
        Scenes with type="extracted" get their keyframe from the previous scene.
        """
        print("\n" + "=" * 60)
        print("STAGE: SCENE KEYFRAMES (v3.0)")
        print("=" * 60)

        if self.pipeline_version != "3.0":
            print("  [ERROR] This is not a v3.0 pipeline.")
            print("  Use --stage first_keyframe for v2.0 pipelines.")
            return

        scenes = self.pipeline.get("scenes", [])
        generated_count = 0

        for scene in scenes:
            scene_id = scene["id"]
            first_kf = scene.get("first_keyframe", {})
            kf_type = first_kf.get("type", "generated")

            if kf_type != "generated":
                print(f"  [skip] {scene_id}: keyframe type is '{kf_type}'")
                continue

            kf_status = first_kf.get("status", "pending")
            if kf_status in ["generated", "approved"]:
                print(f"  [{kf_status}] {scene_id}: keyframe already done")
                continue

            generated_count += 1
            output_path = self.output_dir / first_kf["output"]
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine keyframe type (character vs landscape)
            scene_kf_type = first_kf.get("keyframe_type", "character")

            if scene_kf_type == "landscape":
                cmd = [
                    sys.executable,
                    str(self.scripts_dir / "asset_generator.py"),
                    "background",
                    "--name", f"{scene_id}_keyframe",
                    "--description", first_kf["prompt"],
                    "--output", str(output_path),
                    "--free-memory"
                ]
            else:
                # Character keyframe
                cmd = [
                    sys.executable,
                    str(self.scripts_dir / "keyframe_generator.py"),
                    "--free-memory",
                    "--prompt", first_kf["prompt"],
                    "--output", str(output_path)
                ]

                # Add background reference if specified
                if first_kf.get("background"):
                    bg_id = first_kf["background"]
                    bg_data = self.pipeline.get("assets", {}).get("backgrounds", {}).get(bg_id, {})
                    if bg_data:
                        bg_path = self.output_dir / bg_data["output"]
                        cmd.extend(["--background", str(bg_path)])

                # Add character references
                for char_id in first_kf.get("characters", []):
                    char_data = self.pipeline.get("assets", {}).get("characters", {}).get(char_id, {})
                    if char_data:
                        char_path = self.output_dir / char_data["output"]
                        cmd.extend(["--character", str(char_path)])

                # Add settings
                settings = first_kf.get("settings", {})
                if "preset" in settings:
                    cmd.extend(["--preset", settings["preset"]])

            print(f"  [pending] {scene_id}: generating keyframe...")
            if self._run_command(cmd, f"scene keyframe {scene_id}"):
                self._update_scene_keyframe_status(scene_id, "generated")
            else:
                self._update_scene_keyframe_status(scene_id, "failed")

        if generated_count == 0:
            print("  No keyframes to generate (all extracted or already done)")

        print("\n--- Scene keyframes stage complete ---")

    def execute_scene_segments(
        self,
        scene: dict,
        start_keyframe_path: Path,
        first_video_in_pipeline: bool = False
    ) -> Optional[Path]:
        """
        Execute all segments within a single scene sequentially (v3.0).

        Args:
            scene: Scene dict with 'segments' list
            start_keyframe_path: Path to the starting keyframe
            first_video_in_pipeline: Whether this is the first video (use --free-memory)

        Returns:
            Path to the last segment's extracted keyframe, or None if failed
        """
        scene_id = scene["id"]
        segments = scene.get("segments", [])

        if not segments:
            print(f"    [WARN] Scene {scene_id} has no segments")
            return None

        keyframe_path = start_keyframe_path
        first_video = first_video_in_pipeline

        for i, segment in enumerate(segments):
            seg_id = segment["id"]
            seg_status = segment.get("status", "pending")

            if seg_status in ["generated", "approved"]:
                print(f"    [{seg_status}] {seg_id} - skipping")
                # Update keyframe path from output_keyframe if exists
                if segment.get("output_keyframe"):
                    keyframe_path = self.output_dir / segment["output_keyframe"]
                first_video = False
                continue

            # Video output
            video_output = self.output_dir / segment["output_video"]
            video_output.parent.mkdir(parents=True, exist_ok=True)

            # Build command
            cmd = [
                sys.executable,
                str(self.scripts_dir / "wan_video_comfyui.py"),
                "--prompt", segment["motion_prompt"],
                "--start-frame", str(keyframe_path),
                "--output", str(video_output)
            ]

            if first_video:
                cmd.insert(2, "--free-memory")
                first_video = False

            print(f"    [pending] {seg_id} - generating video...")
            self._update_segment_status(scene_id, seg_id, "in_progress")

            if not self._run_command(cmd, f"segment {seg_id}"):
                self._update_segment_status(scene_id, seg_id, "failed")
                print(f"    [FAIL] Segment {seg_id} failed")
                return None

            # Extract last frame for next segment
            if segment.get("output_keyframe"):
                kf_output = self.output_dir / segment["output_keyframe"]
                kf_output.parent.mkdir(parents=True, exist_ok=True)

                print(f"    Extracting last frame...")
                if self._extract_last_frame(str(video_output), str(kf_output)):
                    keyframe_path = kf_output
                else:
                    print(f"    [WARN] Failed to extract keyframe")

            self._update_segment_status(scene_id, seg_id, "generated")

        return keyframe_path

    def _merge_scene_segments(self, scene: dict) -> bool:
        """
        Merge all segments within a scene into a single video.

        Args:
            scene: Scene dict with 'segments' list and 'output_video'

        Returns:
            True if successful, False otherwise
        """
        scene_id = scene["id"]
        segments = scene.get("segments", [])
        output_video = scene.get("output_video")

        if not output_video:
            print(f"    [WARN] Scene {scene_id} has no output_video defined")
            return False

        output_path = self.output_dir / output_video
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Collect segment video paths
        video_paths = []
        for segment in segments:
            seg_video = self.output_dir / segment["output_video"]
            if seg_video.exists():
                video_paths.append(str(seg_video))
            else:
                print(f"    [WARN] Segment video not found: {seg_video}")

        if not video_paths:
            print(f"    [FAIL] No segment videos to merge for {scene_id}")
            return False

        print(f"    Merging {len(video_paths)} segments into scene video...")
        return self.video_merger.concatenate(video_paths, str(output_path))

    def execute_scenes_v3(self):
        """
        Execute all scenes with segment hierarchy (v3.0).

        For each scene:
        1. Determine start keyframe (generated or extracted from prev scene)
        2. Execute all segments sequentially
        3. Merge segments into scene video
        4. Extract end keyframe for next scene
        """
        print("\n" + "=" * 60)
        print("STAGE: SCENES (v3.0 - with segments)")
        print("=" * 60)

        if self.pipeline_version != "3.0":
            print("  [ERROR] This is not a v3.0 pipeline.")
            print("  Use --stage scenes for v2.0 pipelines.")
            return

        scenes = self.pipeline.get("scenes", [])
        if not scenes:
            print("  [ERROR] No scenes in pipeline")
            return

        print(f"\n--- Processing {len(scenes)} scenes ---")

        prev_scene_end_keyframe: Optional[Path] = None
        first_video_in_pipeline = True

        for scene in scenes:
            scene_id = scene["id"]
            scene_status = self._compute_scene_status(scene)

            if scene_status in ["generated", "approved"]:
                print(f"\n  [{scene_status}] {scene_id} - skipping")
                # Get last segment's output keyframe for next scene
                segments = scene.get("segments", [])
                if segments and segments[-1].get("output_keyframe"):
                    prev_scene_end_keyframe = self.output_dir / segments[-1]["output_keyframe"]
                first_video_in_pipeline = False
                continue

            print(f"\n  [pending] {scene_id} - processing...")

            # Determine start keyframe
            first_kf = scene.get("first_keyframe", {})
            kf_type = first_kf.get("type", "generated")

            if kf_type == "generated":
                kf_output = first_kf.get("output")
                if not kf_output:
                    print(f"    [ERROR] No output path for generated keyframe")
                    continue
                start_keyframe_path = self.output_dir / kf_output
            else:  # extracted
                if prev_scene_end_keyframe is None:
                    print(f"    [ERROR] No previous keyframe for extracted type")
                    print("    First scene cannot have type='extracted'")
                    continue
                start_keyframe_path = prev_scene_end_keyframe

            if not start_keyframe_path.exists():
                print(f"    [ERROR] Start keyframe not found: {start_keyframe_path}")
                continue

            # Execute segments
            end_keyframe = self.execute_scene_segments(
                scene,
                start_keyframe_path,
                first_video_in_pipeline
            )
            first_video_in_pipeline = False

            if end_keyframe is None:
                print(f"    [FAIL] Scene {scene_id} segment execution failed")
                continue

            # Merge segments into scene video
            if len(scene.get("segments", [])) > 1:
                if not self._merge_scene_segments(scene):
                    print(f"    [WARN] Scene merge failed")
            else:
                # Single segment, just copy/rename
                single_seg = scene["segments"][0]
                seg_video = self.output_dir / single_seg["output_video"]
                scene_video = self.output_dir / scene["output_video"]
                if seg_video != scene_video:
                    import shutil
                    scene_video.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(seg_video, scene_video)

            prev_scene_end_keyframe = end_keyframe
            print(f"    [OK] Scene {scene_id} complete")

        # Auto-merge final video
        self.merge_final_video()

        print("\n--- Scenes stage complete ---")

    def merge_final_video(self):
        """
        Merge all scene videos with transitions into final output (v3.0).
        """
        print("\n--- Merging final video ---")

        if self.pipeline_version != "3.0":
            print("  [SKIP] Final merge only for v3.0 pipelines")
            return

        final_config = self.pipeline.get("final_video")
        if not final_config:
            print("  [SKIP] No final_video config in pipeline")
            return

        final_output = self.output_dir / final_config["output"]
        final_output.parent.mkdir(parents=True, exist_ok=True)

        scenes = self.pipeline.get("scenes", [])

        # Build scene configs for merger
        scene_configs = []
        for scene in scenes:
            scene_video = self.output_dir / scene.get("output_video", "")
            if not scene_video.exists():
                print(f"  [WARN] Scene video not found: {scene_video}")
                continue

            transition = scene.get("transition_from_previous")
            scene_configs.append({
                "video": str(scene_video),
                "transition": transition
            })

        if not scene_configs:
            print("  [FAIL] No scene videos to merge")
            self._update_final_video_status("failed")
            return

        print(f"  Merging {len(scene_configs)} scenes...")
        if self.video_merger.merge_all_scenes(scene_configs, str(final_output)):
            self._update_final_video_status("generated")
            print(f"  [OK] Final video: {final_output}")
        else:
            self._update_final_video_status("failed")
            print("  [FAIL] Final merge failed")

    def regenerate(self, item_id: str):
        """Regenerate a specific item by ID."""
        print(f"\nRegenerating: {item_id}")

        # Check assets
        for asset_type in ["characters", "backgrounds", "styles"]:
            assets = self.pipeline.get("assets", {}).get(asset_type, {})
            if item_id in assets:
                print(f"  Found in assets/{asset_type}")
                self._update_asset_status(asset_type, item_id, "pending")

                # Re-run just this asset type
                # (simplified - regenerates all pending in that type)
                original_assets = self.pipeline["assets"][asset_type].copy()
                self.pipeline["assets"][asset_type] = {item_id: assets[item_id]}
                self.execute_assets()
                self.pipeline["assets"][asset_type] = original_assets
                return

        # Check keyframes
        for kf in self.pipeline.get("keyframes", []):
            if kf["id"] == item_id:
                print(f"  Found in keyframes")
                self._update_keyframe_status(item_id, "pending")

                # Generate just this keyframe
                original_keyframes = self.pipeline["keyframes"].copy()
                self.pipeline["keyframes"] = [kf]
                self.execute_keyframes()
                self.pipeline["keyframes"] = original_keyframes
                return

        # Check videos
        for video in self.pipeline.get("videos", []):
            if video["id"] == item_id:
                print(f"  Found in videos")
                self._update_video_status(item_id, "pending")

                # Generate just this video
                original_videos = self.pipeline["videos"].copy()
                self.pipeline["videos"] = [video]
                self.execute_videos()
                self.pipeline["videos"] = original_videos
                return

        print(f"  ERROR: Item '{item_id}' not found in pipeline")

    def status(self):
        """Print pipeline status summary."""
        print("\n" + "=" * 60)
        print(f"PIPELINE STATUS: {self.pipeline.get('project_name', 'Unknown')}")
        print("=" * 60)
        print(f"Pipeline file: {self.pipeline_path}")
        print(f"Output dir: {self.output_dir}")
        print(f"Version: {self.pipeline_version}")
        print()

        def count_statuses(items: dict | list) -> dict:
            if isinstance(items, dict):
                statuses = [item.get("status", "unknown") for item in items.values()]
            else:
                statuses = [item.get("status", "unknown") for item in items]
            return {s: statuses.count(s) for s in set(statuses)}

        def status_icon(status: str) -> str:
            return "+" if status == "approved" else \
                   "o" if status == "generated" else \
                   "x" if status == "failed" else \
                   ">" if status == "in_progress" else "."

        # Assets
        print("ASSETS:")
        for section in ["characters", "backgrounds", "styles"]:
            items = self.pipeline.get("assets", {}).get(section, {})
            if items:
                counts = count_statuses(items)
                status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                print(f"  {section}: {len(items)} items ({status_str})")

        if self.pipeline_version == "3.0":
            # v3.0 scene/segment mode
            scenes = self.pipeline.get("scenes", [])
            if scenes:
                print(f"\nSCENES: {len(scenes)} scenes")
                for scene in scenes:
                    scene_id = scene["id"]
                    scene_status = self._compute_scene_status(scene)
                    icon = status_icon(scene_status)

                    # Keyframe info
                    first_kf = scene.get("first_keyframe", {})
                    kf_type = first_kf.get("type", "generated")
                    kf_status = first_kf.get("status", "pending") if kf_type == "generated" else "n/a"

                    # Transition info
                    transition = scene.get("transition_from_previous")
                    t_str = ""
                    if transition:
                        t_type = transition.get("type") if isinstance(transition, dict) else transition
                        t_str = f" [{t_type}]"

                    print(f"  [{icon}] {scene_id}{t_str} (kf: {kf_type}/{kf_status})")

                    # Show segments
                    segments = scene.get("segments", [])
                    for seg in segments:
                        seg_icon = status_icon(seg.get("status", "pending"))
                        print(f"      [{seg_icon}] {seg['id']}")

            # Final video status
            final_video = self.pipeline.get("final_video")
            if final_video:
                icon = status_icon(final_video.get("status", "pending"))
                print(f"\nFINAL VIDEO:")
                print(f"  [{icon}] {final_video.get('output', 'N/A')}")

        elif self.pipeline_version == "2.0":
            # v2.0 video-first mode
            first_kf = self.pipeline.get("first_keyframe")
            if first_kf:
                icon = status_icon(first_kf.get("status", "pending"))
                kf_type = first_kf.get("type", "character")
                print(f"\nFIRST KEYFRAME:")
                print(f"  [{icon}] {first_kf['id']} ({kf_type})")

            scenes = self.pipeline.get("scenes", [])
            if scenes:
                counts = count_statuses(scenes)
                status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                print(f"\nSCENES: {len(scenes)} items ({status_str})")
                for scene in scenes:
                    icon = status_icon(scene.get("status", "pending"))
                    start_kf = scene.get("start_keyframe", "?")
                    output_kf = scene.get("output_keyframe", "")
                    kf_info = f"{start_kf}"
                    if output_kf:
                        kf_info += f" -> {Path(output_kf).stem}"
                    print(f"  [{icon}] {scene['id']} ({kf_info})")
        else:
            # v1.0 keyframe-first mode (legacy)
            keyframes = self.pipeline.get("keyframes", [])
            if keyframes:
                counts = count_statuses(keyframes)
                status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                print(f"\nKEYFRAMES: {len(keyframes)} items ({status_str})")
                for kf in keyframes:
                    icon = status_icon(kf.get("status", "pending"))
                    print(f"  [{icon}] {kf['id']}")

            videos = self.pipeline.get("videos", [])
            if videos:
                counts = count_statuses(videos)
                status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                print(f"\nVIDEOS: {len(videos)} items ({status_str})")
                for video in videos:
                    icon = status_icon(video.get("status", "pending"))
                    print(f"  [{icon}] {video['id']}")

        print()

    def validate(self) -> bool:
        """Validate pipeline structure and references."""
        print("\nValidating pipeline...")
        print(f"  Detected version: {self.pipeline_version}")
        errors = []

        # Check required fields
        if "project_name" not in self.pipeline:
            errors.append("Missing 'project_name'")

        # Validate based on version
        if self.pipeline_version == "3.0":
            errors.extend(self._validate_v3())
        elif self.pipeline_version == "2.0":
            errors.extend(self._validate_video_first())
        else:
            errors.extend(self._validate_keyframe_first())

        if errors:
            print("VALIDATION FAILED:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("VALIDATION PASSED")
            return True

    def _validate_keyframe_first(self) -> List[str]:
        """Validate keyframe-first (legacy) schema."""
        errors = []

        # Check asset references in keyframes
        for kf in self.pipeline.get("keyframes", []):
            # Check background reference
            if kf.get("background"):
                bg_id = kf["background"]
                if bg_id not in self.pipeline.get("assets", {}).get("backgrounds", {}):
                    errors.append(f"Keyframe {kf['id']}: background '{bg_id}' not found")

            # Check character references
            for char_id in kf.get("characters", []):
                if char_id not in self.pipeline.get("assets", {}).get("characters", {}):
                    errors.append(f"Keyframe {kf['id']}: character '{char_id}' not found")

        # Check keyframe references in videos
        keyframe_ids = {kf["id"] for kf in self.pipeline.get("keyframes", [])}
        for video in self.pipeline.get("videos", []):
            if video.get("start_keyframe") not in keyframe_ids:
                errors.append(f"Video {video['id']}: start_keyframe '{video.get('start_keyframe')}' not found")
            if video.get("end_keyframe") and video["end_keyframe"] not in keyframe_ids:
                errors.append(f"Video {video['id']}: end_keyframe '{video['end_keyframe']}' not found")

        return errors

    def _validate_video_first(self) -> List[str]:
        """Validate video-first schema."""
        errors = []

        # Validate first_keyframe
        first_kf = self.pipeline.get("first_keyframe")
        if not first_kf:
            errors.append("Missing 'first_keyframe' in video-first pipeline")
        else:
            if "id" not in first_kf:
                errors.append("first_keyframe: missing 'id'")
            if "prompt" not in first_kf:
                errors.append("first_keyframe: missing 'prompt'")
            if "output" not in first_kf:
                errors.append("first_keyframe: missing 'output'")

            # Check asset references
            if first_kf.get("background"):
                bg_id = first_kf["background"]
                if bg_id not in self.pipeline.get("assets", {}).get("backgrounds", {}):
                    errors.append(f"first_keyframe: background '{bg_id}' not found")

            for char_id in first_kf.get("characters", []):
                if char_id not in self.pipeline.get("assets", {}).get("characters", {}):
                    errors.append(f"first_keyframe: character '{char_id}' not found")

        # Validate scenes
        scenes = self.pipeline.get("scenes", [])
        if not scenes:
            errors.append("Missing 'scenes' in video-first pipeline")
        else:
            # Build valid keyframe IDs (first_keyframe + output_keyframes from previous scenes)
            valid_keyframe_ids = set()
            if first_kf and first_kf.get("id"):
                valid_keyframe_ids.add(first_kf["id"])

            for i, scene in enumerate(scenes):
                scene_id = scene.get("id", f"scene-{i}")

                if "motion_prompt" not in scene:
                    errors.append(f"Scene {scene_id}: missing 'motion_prompt'")
                if "output_video" not in scene:
                    errors.append(f"Scene {scene_id}: missing 'output_video'")

                # Check start_keyframe reference
                start_kf = scene.get("start_keyframe")
                if not start_kf:
                    errors.append(f"Scene {scene_id}: missing 'start_keyframe'")
                elif start_kf not in valid_keyframe_ids:
                    errors.append(f"Scene {scene_id}: start_keyframe '{start_kf}' not available at this point")

                # Add this scene's output_keyframe to valid IDs for subsequent scenes
                if scene.get("output_keyframe"):
                    # The output_keyframe becomes available for the next scene
                    # We use a derived ID based on scene index
                    if i < len(scenes) - 1:
                        next_scene = scenes[i + 1]
                        next_start = next_scene.get("start_keyframe")
                        if next_start:
                            valid_keyframe_ids.add(next_start)

        return errors

    def _validate_v3(self) -> List[str]:
        """Validate v3.0 schema with scene/segment hierarchy."""
        errors = []
        valid_transitions = {"cut", "continuous", "fade", "dissolve"}

        scenes = self.pipeline.get("scenes", [])
        if not scenes:
            errors.append("Missing 'scenes' in v3.0 pipeline")
            return errors

        for i, scene in enumerate(scenes):
            scene_id = scene.get("id", f"scene-{i}")

            # Validate scene structure
            if "id" not in scene:
                errors.append(f"Scene {i}: missing 'id'")

            if "output_video" not in scene:
                errors.append(f"Scene {scene_id}: missing 'output_video'")

            # Validate first_keyframe
            first_kf = scene.get("first_keyframe", {})
            kf_type = first_kf.get("type", "generated")

            if kf_type == "generated":
                if "prompt" not in first_kf:
                    errors.append(f"Scene {scene_id}: first_keyframe missing 'prompt'")
                if "output" not in first_kf:
                    errors.append(f"Scene {scene_id}: first_keyframe missing 'output'")

                # Validate asset references
                if first_kf.get("background"):
                    bg_id = first_kf["background"]
                    if bg_id not in self.pipeline.get("assets", {}).get("backgrounds", {}):
                        errors.append(f"Scene {scene_id}: background '{bg_id}' not found")

                for char_id in first_kf.get("characters", []):
                    if char_id not in self.pipeline.get("assets", {}).get("characters", {}):
                        errors.append(f"Scene {scene_id}: character '{char_id}' not found")

            elif kf_type == "extracted":
                if i == 0:
                    errors.append(f"Scene {scene_id}: first scene cannot have type='extracted'")
            else:
                errors.append(f"Scene {scene_id}: invalid keyframe type '{kf_type}'")

            # Validate transition
            transition = scene.get("transition_from_previous")
            if transition is not None:
                if i == 0:
                    errors.append(f"Scene {scene_id}: first scene should not have transition_from_previous")
                else:
                    t_type = transition.get("type") if isinstance(transition, dict) else transition
                    if t_type not in valid_transitions:
                        errors.append(f"Scene {scene_id}: invalid transition type '{t_type}'")

            # Validate segments
            segments = scene.get("segments", [])
            if not segments:
                errors.append(f"Scene {scene_id}: missing 'segments'")
            else:
                for j, segment in enumerate(segments):
                    seg_id = segment.get("id", f"seg-{j}")

                    if "id" not in segment:
                        errors.append(f"Scene {scene_id}, segment {j}: missing 'id'")
                    if "motion_prompt" not in segment:
                        errors.append(f"Scene {scene_id}, segment {seg_id}: missing 'motion_prompt'")
                    if "output_video" not in segment:
                        errors.append(f"Scene {scene_id}, segment {seg_id}: missing 'output_video'")

                    # All segments except last should have output_keyframe
                    if j < len(segments) - 1 and "output_keyframe" not in segment:
                        errors.append(f"Scene {scene_id}, segment {seg_id}: missing 'output_keyframe' (required for non-last segments)")

        # Validate final_video if present
        final_video = self.pipeline.get("final_video")
        if final_video and "output" not in final_video:
            errors.append("final_video: missing 'output'")

        return errors


def main():
    parser = argparse.ArgumentParser(
        description="Execute AI video pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # v1.0 Keyframe-first mode (legacy):
  python execute_pipeline.py pipeline.json --stage assets
  python execute_pipeline.py pipeline.json --stage keyframes
  python execute_pipeline.py pipeline.json --stage videos
  python execute_pipeline.py pipeline.json --all

  # v2.0 Video-first mode:
  python execute_pipeline.py pipeline.json --stage assets
  python execute_pipeline.py pipeline.json --stage first_keyframe
  python execute_pipeline.py pipeline.json --stage scenes
  python execute_pipeline.py pipeline.json --all

  # v3.0 Scene/Segment mode:
  python execute_pipeline.py pipeline.json --stage assets
  python execute_pipeline.py pipeline.json --stage scene_keyframes
  python execute_pipeline.py pipeline.json --stage scenes
  python execute_pipeline.py pipeline.json --all

  # Other commands:
  python execute_pipeline.py pipeline.json --regenerate KF-B
  python execute_pipeline.py pipeline.json --status
  python execute_pipeline.py pipeline.json --validate
        """
    )
    parser.add_argument("pipeline", help="Path to pipeline.json")
    parser.add_argument("--stage",
                       choices=["assets", "keyframes", "videos", "first_keyframe",
                                "scenes", "scene_keyframes"],
                       help="Execute specific stage")
    parser.add_argument("--all", action="store_true",
                       help="Execute all stages sequentially")
    parser.add_argument("--regenerate", metavar="ID",
                       help="Regenerate specific item by ID")
    parser.add_argument("--status", action="store_true",
                       help="Show pipeline status")
    parser.add_argument("--validate", action="store_true",
                       help="Validate pipeline without executing")
    parser.add_argument("--base-dir",
                       help="Base directory for scripts (default: auto-detect)")

    args = parser.parse_args()

    if not os.path.exists(args.pipeline):
        print(f"ERROR: Pipeline file not found: {args.pipeline}")
        sys.exit(1)

    executor = PipelineExecutor(args.pipeline, args.base_dir)
    version = executor.pipeline_version

    if args.status:
        executor.status()
    elif args.validate:
        success = executor.validate()
        sys.exit(0 if success else 1)
    elif args.regenerate:
        executor.regenerate(args.regenerate)
    elif args.stage == "assets":
        executor.execute_assets()
    elif args.stage == "keyframes":
        if version != "1.0":
            print(f"ERROR: This is a v{version} pipeline. Use appropriate stage instead.")
            sys.exit(1)
        executor.execute_keyframes()
    elif args.stage == "videos":
        if version != "1.0":
            print(f"ERROR: This is a v{version} pipeline. Use --stage scenes instead.")
            sys.exit(1)
        executor.execute_videos()
    elif args.stage == "first_keyframe":
        if version != "2.0":
            print(f"ERROR: This is a v{version} pipeline.")
            if version == "3.0":
                print("Use --stage scene_keyframes instead.")
            sys.exit(1)
        executor.execute_first_keyframe()
    elif args.stage == "scene_keyframes":
        if version != "3.0":
            print(f"ERROR: This is a v{version} pipeline.")
            if version == "2.0":
                print("Use --stage first_keyframe instead.")
            sys.exit(1)
        executor.execute_scene_keyframes()
    elif args.stage == "scenes":
        if version == "1.0":
            print("ERROR: This is a v1.0 keyframe-first pipeline. Use --stage videos instead.")
            sys.exit(1)
        if version == "3.0":
            executor.execute_scenes_v3()
        else:
            executor.execute_scenes()
    elif args.all:
        executor.execute_assets()
        print("\n" + "-" * 60)
        print("Assets complete. Review before continuing.")
        print("-" * 60)
        input("Press Enter to continue...")

        if version == "3.0":
            # v3.0 scene/segment mode
            executor.execute_scene_keyframes()
            print("\n" + "-" * 60)
            print("Scene keyframes complete. Review before continuing to scenes.")
            print("-" * 60)
            input("Press Enter to continue to scenes...")

            executor.execute_scenes_v3()
        elif version == "2.0":
            # v2.0 video-first mode
            executor.execute_first_keyframe()
            print("\n" + "-" * 60)
            print("First keyframe complete. Review before continuing to scenes.")
            print("-" * 60)
            input("Press Enter to continue to scenes...")

            executor.execute_scenes()
        else:
            # Keyframe-first mode (legacy)
            executor.execute_keyframes()
            print("\n" + "-" * 60)
            print("Keyframes complete. Review before continuing to videos.")
            print("-" * 60)
            input("Press Enter to continue to videos...")

            executor.execute_videos()

        print("\n" + "-" * 60)
        print("All stages complete!")
        print("-" * 60)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
