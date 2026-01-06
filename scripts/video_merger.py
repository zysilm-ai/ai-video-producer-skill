#!/usr/bin/env python3
"""
Video merging utility using FFmpeg.

Provides functionality to:
- Concatenate video segments (within a scene)
- Merge videos with transitions (between scenes)
- Create final video from all scenes

Supported transitions:
- cut: Instant switch (simple concatenation)
- continuous: Direct concatenation (keyframe extracted from previous)
- fade: Fade through black
- dissolve: Cross dissolve/xfade
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Optional, Any


class VideoMerger:
    """FFmpeg-based video merging utility."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """
        Initialize VideoMerger.

        Args:
            ffmpeg_path: Path to ffmpeg executable
            ffprobe_path: Path to ffprobe executable
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def _run_command(self, cmd: List[str], description: str = "") -> bool:
        """
        Run a command and return success status.

        Args:
            cmd: Command as list of strings
            description: Description for logging

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 min timeout for video operations
            )

            if result.returncode == 0:
                return True
            else:
                print(f"    [FAIL] {description}: {result.stderr[:500]}")
                return False

        except subprocess.TimeoutExpired:
            print(f"    [FAIL] {description}: Timeout after 10 minutes")
            return False
        except Exception as e:
            print(f"    [FAIL] {description}: {e}")
            return False

    def get_video_duration(self, video_path: str) -> float:
        """
        Get duration of a video file in seconds.

        Args:
            video_path: Path to video file

        Returns:
            Duration in seconds, or 0.0 if failed
        """
        cmd = [
            self.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass

        return 0.0

    def concatenate(self, video_paths: List[str], output_path: str) -> bool:
        """
        Concatenate videos with no transition (for segments within scene).

        Uses FFmpeg concat demuxer for lossless concatenation when possible.

        Args:
            video_paths: List of video file paths to concatenate
            output_path: Output video path

        Returns:
            True if successful, False otherwise
        """
        if not video_paths:
            print("    [FAIL] No videos to concatenate")
            return False

        if len(video_paths) == 1:
            # Single video, just copy
            import shutil
            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(video_paths[0], output_path)
                return True
            except Exception as e:
                print(f"    [FAIL] Copy failed: {e}")
                return False

        # Create concat file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video_path in video_paths:
                # Escape single quotes and backslashes for FFmpeg
                escaped_path = video_path.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",  # Copy without re-encoding
                output_path
            ]

            success = self._run_command(cmd, "concatenate videos")
            return success

        finally:
            # Clean up temp file
            try:
                os.unlink(concat_file)
            except Exception:
                pass

    def merge_with_transition(
        self,
        video1_path: str,
        video2_path: str,
        output_path: str,
        transition: str = "cut",
        duration: float = 0.5
    ) -> bool:
        """
        Merge two videos with a transition effect.

        Args:
            video1_path: First video path
            video2_path: Second video path
            output_path: Output video path
            transition: Transition type (cut, continuous, fade, dissolve)
            duration: Transition duration in seconds (for fade/dissolve)

        Returns:
            True if successful, False otherwise
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if transition in ["cut", "continuous"]:
            # Simple concatenation
            return self.concatenate([video1_path, video2_path], output_path)

        elif transition == "fade":
            # Fade out video1, fade in video2 (through black)
            return self._apply_fade_transition(
                video1_path, video2_path, output_path, duration
            )

        elif transition == "dissolve":
            # Cross dissolve using xfade
            return self._apply_xfade_transition(
                video1_path, video2_path, output_path, duration
            )

        else:
            print(f"    [WARN] Unknown transition '{transition}', using cut")
            return self.concatenate([video1_path, video2_path], output_path)

    def _apply_fade_transition(
        self,
        video1_path: str,
        video2_path: str,
        output_path: str,
        duration: float
    ) -> bool:
        """
        Apply fade through black transition.

        Args:
            video1_path: First video path
            video2_path: Second video path
            output_path: Output video path
            duration: Fade duration in seconds

        Returns:
            True if successful, False otherwise
        """
        duration1 = self.get_video_duration(video1_path)
        if duration1 <= 0:
            print("    [FAIL] Could not get video1 duration")
            return False

        fade_out_start = max(0, duration1 - duration)

        # Build filter complex for fade through black
        filter_complex = (
            f"[0:v]fade=t=out:st={fade_out_start}:d={duration}[v0];"
            f"[1:v]fade=t=in:st=0:d={duration}[v1];"
            f"[v0][v1]concat=n=2:v=1:a=0[outv]"
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            output_path
        ]

        return self._run_command(cmd, "fade transition")

    def _apply_xfade_transition(
        self,
        video1_path: str,
        video2_path: str,
        output_path: str,
        duration: float
    ) -> bool:
        """
        Apply cross dissolve transition using xfade filter.

        Args:
            video1_path: First video path
            video2_path: Second video path
            output_path: Output video path
            duration: Dissolve duration in seconds

        Returns:
            True if successful, False otherwise
        """
        duration1 = self.get_video_duration(video1_path)
        if duration1 <= 0:
            print("    [FAIL] Could not get video1 duration")
            return False

        offset = max(0, duration1 - duration)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex",
            f"xfade=transition=fade:duration={duration}:offset={offset}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            output_path
        ]

        return self._run_command(cmd, "dissolve transition")

    def merge_all_scenes(
        self,
        scene_configs: List[Dict[str, Any]],
        output_path: str
    ) -> bool:
        """
        Merge all scene videos with their specified transitions.

        Args:
            scene_configs: List of dicts with 'video' path and 'transition' config
                Example: [
                    {"video": "scene-01/merged.mp4", "transition": None},
                    {"video": "scene-02/merged.mp4", "transition": {"type": "cut"}},
                    {"video": "scene-03/merged.mp4", "transition": {"type": "fade", "duration": 0.5}}
                ]
            output_path: Final output video path

        Returns:
            True if successful, False otherwise
        """
        if not scene_configs:
            print("    [FAIL] No scenes to merge")
            return False

        if len(scene_configs) == 1:
            # Single scene, just copy
            import shutil
            try:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(scene_configs[0]["video"], output_path)
                print(f"    [OK] Single scene copied to {Path(output_path).name}")
                return True
            except Exception as e:
                print(f"    [FAIL] Copy failed: {e}")
                return False

        # Check if all transitions are simple concatenation
        all_simple = all(
            self._is_simple_transition(sc.get("transition"))
            for sc in scene_configs[1:]  # Skip first scene (no transition)
        )

        if all_simple:
            # Use fast concatenation
            video_paths = [sc["video"] for sc in scene_configs]
            return self.concatenate(video_paths, output_path)

        # Need to apply transitions sequentially
        return self._merge_with_transitions(scene_configs, output_path)

    def _is_simple_transition(self, transition: Optional[Dict]) -> bool:
        """Check if transition is simple concatenation."""
        if transition is None:
            return True
        t_type = transition.get("type", "cut")
        return t_type in ["cut", "continuous"]

    def _merge_with_transitions(
        self,
        scene_configs: List[Dict[str, Any]],
        output_path: str
    ) -> bool:
        """
        Merge scenes with complex transitions.

        Processes transitions sequentially, creating intermediate files.

        Args:
            scene_configs: List of scene configurations
            output_path: Final output path

        Returns:
            True if successful, False otherwise
        """
        temp_files = []
        current_video = scene_configs[0]["video"]

        try:
            for i, scene_config in enumerate(scene_configs[1:], start=1):
                next_video = scene_config["video"]
                transition = scene_config.get("transition")

                # Determine transition parameters
                if transition is None:
                    t_type = "cut"
                    t_duration = 0
                else:
                    t_type = transition.get("type", "cut")
                    t_duration = transition.get("duration", 0.5)

                # Create output path (intermediate or final)
                if i == len(scene_configs) - 1:
                    # Last merge, output to final path
                    merge_output = output_path
                else:
                    # Intermediate merge
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix='.mp4', delete=False
                    )
                    temp_file.close()
                    merge_output = temp_file.name
                    temp_files.append(merge_output)

                print(f"    Merging scene {i} with '{t_type}' transition...")
                success = self.merge_with_transition(
                    current_video,
                    next_video,
                    merge_output,
                    transition=t_type,
                    duration=t_duration
                )

                if not success:
                    print(f"    [FAIL] Failed to merge scene {i}")
                    return False

                current_video = merge_output

            print(f"    [OK] Final video merged: {Path(output_path).name}")
            return True

        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass


def main():
    """Test video merger functionality."""
    import argparse

    parser = argparse.ArgumentParser(description="Video merger utility")
    parser.add_argument("--concat", nargs="+", help="Videos to concatenate")
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--transition", choices=["cut", "fade", "dissolve"],
                        default="cut", help="Transition type (for 2 videos)")
    parser.add_argument("--duration", type=float, default=0.5,
                        help="Transition duration in seconds")

    args = parser.parse_args()

    merger = VideoMerger()

    if args.concat:
        if len(args.concat) == 2 and args.transition != "cut":
            success = merger.merge_with_transition(
                args.concat[0],
                args.concat[1],
                args.output,
                transition=args.transition,
                duration=args.duration
            )
        else:
            success = merger.concatenate(args.concat, args.output)

        if success:
            print(f"Output: {args.output}")
        else:
            print("Merge failed")
            exit(1)


if __name__ == "__main__":
    main()
