"""Mode 2 Dynamic Gameplay & Satisfying Background Manager.
Downloads randomized, royalty-free satisfying background videos on-the-fly at short creation time
(GTA Stunts, Subway Surfers, TrackMania, Minecraft, ASMR Sand, BeamNG, Marble Runs).
Zero permanent storage — downloads lightweight slice to temp and cleans up immediately after slicing.
"""

import os
import sys
import time
import random
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import imageio_ffmpeg
import yt_dlp

from ..config import config

# Rich variety of high-retention royalty-free satisfying background search pools
GAMEPLAY_CATEGORIES: Dict[str, Dict[str, str]] = {
    "subway": {
        "title": "Subway Surfers High Speed Run",
        "search_query": "subway surfers gameplay no commentary no copyright",
    },
    "gta": {
        "title": "GTA V Mega Ramp Stunt Races",
        "search_query": "gta 5 stunts mega ramp gameplay no copyright",
    },
    "minecraft": {
        "title": "Minecraft Speed Parkour",
        "search_query": "minecraft speed parkour gameplay no commentary no copyright",
    },
    "beamng": {
        "title": "BeamNG Drive Physics Stunts & Crashes",
        "search_query": "beamng drive physics stunts gameplay no commentary no copyright",
    },
    "trackmania": {
        "title": "TrackMania Obstacle Course",
        "search_query": "trackmania obstacle course gameplay no commentary no copyright",
    },
    "satisfying_asmr": {
        "title": "Satisfying Kinetic Sand & ASMR Cutting",
        "search_query": "satisfying kinetic sand soap asmr cutting no commentary no copyright",
    },
    "temple_run": {
        "title": "Temple Run 2 Speedrun",
        "search_query": "temple run 2 gameplay no commentary no copyright",
    },
    "marble_run": {
        "title": "Satisfying 3D Marble Run Physics",
        "search_query": "satisfying marble run physics 4k 60fps no commentary no copyright",
    },
}


class GameplayManager:
    """Manages on-the-fly streaming and slicing of satisfying backgrounds with zero disk bloat."""

    def __init__(self, gameplay_dir: Optional[Path] = None):
        self.temp_dir = config.temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = self._locate_ffmpeg()

    def _locate_ffmpeg(self) -> str:
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()

    def _probe_duration(self, video_path: Path) -> float:
        """Get duration of a video file in seconds."""
        cmd = [self.ffmpeg_path, "-i", str(video_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                parts = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = parts.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
        return 0.0

    def select_style(self, requested_style: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
        """Resolve requested style or pick a random high-retention theme."""
        req = (requested_style or "random").lower().strip()
        if req in GAMEPLAY_CATEGORIES:
            return req, GAMEPLAY_CATEGORIES[req]

        # Pick random style across all categories
        chosen_key = random.choice(list(GAMEPLAY_CATEGORIES.keys()))
        return chosen_key, GAMEPLAY_CATEGORIES[chosen_key]

    def download_dynamic_slice(
        self,
        style_key: str,
        style_info: Dict[str, str],
        target_duration: float,
        temp_dir: Path,
    ) -> Tuple[Path, str]:
        """
        Download a lightweight, randomized slice of background footage directly into temp.
        Uses yt-dlp dynamic search to find active, high-quality, royalty-free gameplay.
        Downloads only the required duration (+15s buffer), completing in seconds.
        """
        timestamp = int(time.time() * 1000)
        raw_download_path = temp_dir / f"dynamic_bg_{style_key}_{timestamp}.mp4"

        search_query = style_info.get("search_query")
        direct_url = style_info.get("url")

        target_url = direct_url
        video_title = style_info.get("title", style_key)
        video_duration = 600.0

        # Dynamic search if query provided
        if search_query:
            print(f"[Gameplay/Dynamic] Searching YouTube for fresh {style_info['title']}...")
            search_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web_creator"]
                    }
                },
            }
            try:
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    info = ydl.extract_info(f"ytsearch8:{search_query}", download=False)
                    entries = [
                        e for e in info.get("entries", [])
                        if (e.get("duration") or 0) >= (target_duration + 30)
                    ]
                    if not entries:
                        entries = info.get("entries", [])
                    if entries:
                        chosen_entry = random.choice(entries)
                        vid_id = chosen_entry.get("id")
                        target_url = f"https://www.youtube.com/watch?v={vid_id}"
                        video_title = chosen_entry.get("title", style_info["title"])
                        video_duration = float(chosen_entry.get("duration") or 600)
            except Exception as e:
                print(f"[Gameplay/Dynamic] Search failed ({e}), falling back to direct stream...")

        if not target_url:
            raise RuntimeError(f"No valid video URL resolved for style {style_key}")

        # Pick random start offset safely inside the video length
        max_start = max(10, int(min(video_duration - target_duration - 20, 300)))
        start_sec = random.randint(15, max_start)
        end_sec = start_sec + int(target_duration) + 15

        safe_title = video_title[:50].encode("ascii", "ignore").decode("ascii")
        print(f"[Gameplay/Dynamic] Selected: {safe_title} [{target_url}]")
        print(f"  * Slicing range: {start_sec}s -> {end_sec}s (~{end_sec - start_sec}s slice)")

        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]/best[height<=1080]/best",
            "outtmpl": str(raw_download_path),
            "merge_output_format": "mp4",
            "ffmpeg_location": self.ffmpeg_path,
            "download_ranges": yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            "force_keyframes_at_cuts": True,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web_creator"]
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target_url])

        if not raw_download_path.exists() or raw_download_path.stat().st_size < 100000:
            print("[Gameplay/Dynamic] Offset issue, retrying from start (0s)...")
            ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, int(target_duration) + 15)])
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([target_url])

        if not raw_download_path.exists():
            raise RuntimeError(f"Failed to stream dynamic background slice for {style_key}")

        return raw_download_path, video_title

    def get_gameplay_slice(
        self,
        target_duration: float,
        output_mp4: Path,
        style: str = "random",
        width: int = 1080,
        height: int = 1920,
    ) -> Path:
        """
        Download a random satisfying background on-the-fly, scale/crop to 9:16 vertical,
        and immediately delete the raw download to keep disk 100% clean.
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        chosen_style, style_info = self.select_style(style)

        # Attempt download with automatic category fallback on network / stream errors
        available_categories = list(GAMEPLAY_CATEGORIES.keys())
        random.shuffle(available_categories)
        if chosen_style in available_categories:
            available_categories.remove(chosen_style)
            available_categories.insert(0, chosen_style)

        raw_video = None
        for cat_key in available_categories:
            try:
                raw_video, actual_title = self.download_dynamic_slice(
                    style_key=cat_key,
                    style_info=GAMEPLAY_CATEGORIES[cat_key],
                    target_duration=target_duration,
                    temp_dir=output_mp4.parent,
                )
                chosen_style = cat_key
                break
            except Exception as e:
                print(f"[Gameplay/Dynamic] Category '{cat_key}' unavailable ({e}), trying alternate...")
                if raw_video and raw_video.exists():
                    raw_video.unlink(missing_ok=True)
                raw_video = None

        if not raw_video or not raw_video.exists():
            print("[Gameplay/Dynamic] YouTube streams unavailable on this runner, falling back to Pexels satisfying background...")
            try:
                from ..visuals.pexels import PexelsVisualFetcher
                pvf = PexelsVisualFetcher()
                pexels_query = random.choice(["satisfying motion", "kinetic sand", "neon abstract", "matrix tech"])
                pexels_clips = pvf.search_and_download(keywords=[pexels_query], target_duration=target_duration)
                if pexels_clips and pexels_clips[0].file_path.exists():
                    raw_video = pexels_clips[0].file_path
                    chosen_style = "satisfying_motion"
                    print(f"[Gameplay/Dynamic] Pexels satisfying background downloaded: {raw_video.name}")
            except Exception as pe:
                print(f"[Gameplay/Dynamic] Pexels fallback error: {pe}")

        if not raw_video or not raw_video.exists():
            raise RuntimeError("All dynamic gameplay sources failed to stream.")

        try:
            total_dur = self._probe_duration(raw_video)
            start_offset = 0.0
            if total_dur > target_duration + 2.0:
                max_offset = total_dur - target_duration
                start_offset = random.uniform(0.0, min(5.0, max_offset))

            print(
                f"[Gameplay/Dynamic] Conform & crop to {width}x{height} (Style: {chosen_style.upper()}): "
                f"{target_duration:.1f}s slice..."
            )

            vf_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},"
                f"fps=30,"
                f"eq=contrast=1.05:saturation=1.12"
            )

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-loglevel", "error",
                "-ss", f"{start_offset:.3f}",
                "-t", f"{target_duration:.3f}",
                "-i", str(raw_video),
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-an",  # Strip original gameplay sound for studio dialogue & BGM mixing
                str(output_mp4),
            ]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg background formatting failed: {res.stderr}")

            print(f"[Gameplay/Dynamic] Ready: {output_mp4.name} ({output_mp4.stat().st_size / 1024 / 1024:.1f} MB)")

        finally:
            # Immediately delete raw download file to maintain zero storage footprint
            if raw_video.exists():
                raw_video.unlink(missing_ok=True)
                print(f"[Gameplay/Dynamic] Cleaned up temporary download ({raw_video.name})")

        return output_mp4
