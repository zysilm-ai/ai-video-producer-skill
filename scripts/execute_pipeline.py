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

        print(f"Base dir: {self.base_dir}")
        print(f"Scripts dir: {self.scripts_dir}")
        print(f"Output dir: {self.output_dir}")

    def _load_pipeline(self) -> dict:
        """Load and parse pipeline.json."""
        with open(self.pipeline_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_pipeline(self):
        """Save pipeline.json with updated statuses."""
        with open(self.pipeline_path, 'w', encoding='utf-8') as f:
            json.dump(self.pipeline, f, indent=2, ensure_ascii=False)

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
        for video in self.pipeline["videos"]:
            if video["id"] == video_id:
                video["status"] = status
                self._save_pipeline()
                return

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
        """Generate all assets (characters, backgrounds, poses, styles)."""
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

        # Poses
        poses = assets.get("poses", {})
        if poses:
            print(f"\n--- Poses ({len(poses)} items) ---")
            for pose_id, pose_data in poses.items():
                if pose_data.get("status") in ["generated", "approved"]:
                    print(f"  [{pose_data['status']}] {pose_id} - skipping")
                    continue

                output_path = self.output_dir / pose_data["output"]
                output_path.parent.mkdir(parents=True, exist_ok=True)

                pose_type = pose_data.get("type", "generate")

                if pose_type == "extract":
                    # Extract pose from source image
                    source_path = pose_data.get("source", "")
                    if not source_path:
                        print(f"  [error] {pose_id} - no source specified for extract")
                        self._update_asset_status("poses", pose_id, "failed")
                        continue

                    cmd = [
                        sys.executable,
                        str(self.scripts_dir / "asset_generator.py"),
                        "pose",
                        "--source", str(self.output_dir / source_path),
                        "--output", str(output_path),
                        "--free-memory"
                    ]
                else:
                    # Generate pose reference and extract skeleton
                    ref_output = output_path.parent / "refs" / f"{pose_id}.png"
                    ref_output.parent.mkdir(parents=True, exist_ok=True)

                    cmd = [
                        sys.executable,
                        str(self.scripts_dir / "asset_generator.py"),
                        "pose-ref",
                        "--name", pose_id,
                        "--pose", pose_data["prompt"],
                        "--output", str(ref_output),
                        "--extract-skeleton",
                        "--skeleton-output", str(output_path),
                        "--free-memory"
                    ]

                print(f"  [pending] {pose_id} - generating ({pose_type})...")
                if self._run_command(cmd, f"pose {pose_id}"):
                    self._update_asset_status("poses", pose_id, "generated")
                else:
                    self._update_asset_status("poses", pose_id, "failed")

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

            # Add pose reference
            if kf.get("pose"):
                pose_id = kf["pose"]
                pose_data = self.pipeline["assets"]["poses"].get(pose_id, {})
                if pose_data:
                    pose_path = self.output_dir / pose_data["output"]
                    cmd.extend(["--pose", str(pose_path)])

            # Add settings
            settings = kf.get("settings", {})
            if "control_strength" in settings:
                cmd.extend(["--control-strength", str(settings["control_strength"])])
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

    def regenerate(self, item_id: str):
        """Regenerate a specific item by ID."""
        print(f"\nRegenerating: {item_id}")

        # Check assets
        for asset_type in ["characters", "backgrounds", "poses", "styles"]:
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
        print()

        def count_statuses(items: dict | list) -> dict:
            if isinstance(items, dict):
                statuses = [item.get("status", "unknown") for item in items.values()]
            else:
                statuses = [item.get("status", "unknown") for item in items]
            return {s: statuses.count(s) for s in set(statuses)}

        # Assets
        print("ASSETS:")
        for section in ["characters", "backgrounds", "poses", "styles"]:
            items = self.pipeline.get("assets", {}).get(section, {})
            if items:
                counts = count_statuses(items)
                status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
                print(f"  {section}: {len(items)} items ({status_str})")

        # Keyframes
        keyframes = self.pipeline.get("keyframes", [])
        if keyframes:
            counts = count_statuses(keyframes)
            status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
            print(f"\nKEYFRAMES: {len(keyframes)} items ({status_str})")
            for kf in keyframes:
                status_icon = "+" if kf.get("status") == "approved" else \
                             "o" if kf.get("status") == "generated" else \
                             "x" if kf.get("status") == "failed" else "."
                print(f"  [{status_icon}] {kf['id']}")

        # Videos
        videos = self.pipeline.get("videos", [])
        if videos:
            counts = count_statuses(videos)
            status_str = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
            print(f"\nVIDEOS: {len(videos)} items ({status_str})")
            for video in videos:
                status_icon = "+" if video.get("status") == "approved" else \
                             "o" if video.get("status") == "generated" else \
                             "x" if video.get("status") == "failed" else "."
                print(f"  [{status_icon}] {video['id']}")

        print()

    def validate(self) -> bool:
        """Validate pipeline structure and references."""
        print("\nValidating pipeline...")
        errors = []

        # Check required fields
        if "project_name" not in self.pipeline:
            errors.append("Missing 'project_name'")

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

            # Check pose reference
            if kf.get("pose"):
                pose_id = kf["pose"]
                if pose_id not in self.pipeline.get("assets", {}).get("poses", {}):
                    errors.append(f"Keyframe {kf['id']}: pose '{pose_id}' not found")

        # Check keyframe references in videos
        keyframe_ids = {kf["id"] for kf in self.pipeline.get("keyframes", [])}
        for video in self.pipeline.get("videos", []):
            if video.get("start_keyframe") not in keyframe_ids:
                errors.append(f"Video {video['id']}: start_keyframe '{video.get('start_keyframe')}' not found")
            if video.get("end_keyframe") and video["end_keyframe"] not in keyframe_ids:
                errors.append(f"Video {video['id']}: end_keyframe '{video['end_keyframe']}' not found")

        if errors:
            print("VALIDATION FAILED:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("VALIDATION PASSED")
            return True


def main():
    parser = argparse.ArgumentParser(
        description="Execute AI video pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python execute_pipeline.py pipeline.json --stage assets
  python execute_pipeline.py pipeline.json --stage keyframes
  python execute_pipeline.py pipeline.json --stage videos
  python execute_pipeline.py pipeline.json --all
  python execute_pipeline.py pipeline.json --regenerate KF-B
  python execute_pipeline.py pipeline.json --status
        """
    )
    parser.add_argument("pipeline", help="Path to pipeline.json")
    parser.add_argument("--stage", choices=["assets", "keyframes", "videos"],
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
        executor.execute_keyframes()
    elif args.stage == "videos":
        executor.execute_videos()
    elif args.all:
        executor.execute_assets()
        print("\n" + "-" * 60)
        print("Assets complete. Review before continuing to keyframes.")
        print("-" * 60)
        input("Press Enter to continue to keyframes...")

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
