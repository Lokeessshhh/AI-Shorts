"""Mode 2 Dynamic Gameplay & Satisfying Background Manager.
Handles fetching and caching high-retention royalty-free background videos
(GTA Stunts, Subway Surfers, TrackMania, Minecraft, ASMR Sand, Marble Runs).
In cloud environments (GitHub Actions), queries direct CDN URLs (Mixkit/Pexels)
and caches in assets/gameplay/ — NEVER querying YouTube for gameplay loops.
"""

import os
import sys
import time
import random
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests
import imageio_ffmpeg
import yt_dlp

from ..config import config

# Direct CDN video sources for reliable, zero-bot-check streaming & caching
DIRECT_CDN_GAMEPLAY: Dict[str, Dict[str, Any]] = {
    "minecraft": {
        "title": "Minecraft Speed Parkour",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-gameplay-of-a-futuristic-racing-game-41484-large.mp4",
        ],
        "keywords": ["minecraft parkour", "video game gameplay", "pixel game"],
    },
    "subway": {
        "title": "Subway Surfers High Speed Run",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-gameplay-of-a-futuristic-racing-game-41484-large.mp4",
        ],
        "keywords": ["fast runner game", "subway surfers gameplay", "mobile game"],
    },
    "gta": {
        "title": "GTA V Mega Ramp Stunts",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-car-racing-on-a-curved-track-42006-large.mp4",
        ],
        "keywords": ["car stunts ramp", "racing car game", "action game"],
    },
    "satisfying_asmr": {
        "title": "Satisfying Kinetic Sand & ASMR Cutting",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-hands-cutting-colorful-soap-with-a-knife-43003-large.mp4",
        ],
        "keywords": ["satisfying kinetic sand", "soap cutting asmr", "satisfying colors"],
    },
    "trackmania": {
        "title": "TrackMania Obstacle Course",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-car-racing-on-a-curved-track-42006-large.mp4",
        ],
        "keywords": ["trackmania obstacle", "car speed run", "racing loop"],
    },
    "beamng": {
        "title": "BeamNG Drive Physics Stunts",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-car-racing-on-a-curved-track-42006-large.mp4",
        ],
        "keywords": ["car crash physics", "beamng drive", "car stunts"],
    },
    "temple_run": {
        "title": "Temple Run Speedrun",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-hands-holding-a-smartphone-playing-a-game-42998-large.mp4",
        ],
        "keywords": ["temple run gameplay", "running mobile game", "runner game"],
    },
    "marble_run": {
        "title": "Satisfying 3D Marble Run",
        "cdn_urls": [
            "https://assets.mixkit.co/videos/preview/mixkit-tunnel-of-futuristic-neon-lights-42987-large.mp4",
        ],
        "keywords": ["marble run 3d", "satisfying physics marble", "kinetic motion"],
    },
}

GAMEPLAY_CATEGORIES: Dict[str, Dict[str, str]] = {
    k: {
        "title": v["title"],
        "search_query": f"{k} gameplay no commentary no copyright",
    }
    for k, v in DIRECT_CDN_GAMEPLAY.items()
}


class GameplayManager:
    """Manages static CDN caching and dynamic streaming of satisfying background video loops."""

    def __init__(self, gameplay_dir: Optional[Path] = None):
        self.temp_dir = config.temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = gameplay_dir or (config.root_dir / "assets" / "gameplay")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = self._locate_ffmpeg()
        self.is_cloud = bool(os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"))

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

    def select_style(self, requested_style: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Resolve requested style or pick a random high-retention theme."""
        req = (requested_style or "random").lower().strip()
        if req in DIRECT_CDN_GAMEPLAY:
            return req, DIRECT_CDN_GAMEPLAY[req]

        chosen_key = random.choice(list(DIRECT_CDN_GAMEPLAY.keys()))
        return chosen_key, DIRECT_CDN_GAMEPLAY[chosen_key]

    def _download_cdn_video(self, url: str, dest_path: Path) -> bool:
        """Download video file from direct CDN URL using requests streaming."""
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[Gameplay/CDN] Streaming from CDN: {url}...")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            if dest_path.exists() and dest_path.stat().st_size > 50000:
                print(f"[Gameplay/CDN] Downloaded and cached: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.1f} MB)")
                return True
        except Exception as e:
            print(f"[Gameplay/CDN] Direct download error ({e}), trying next source...")
            if dest_path.exists():
                dest_path.unlink(missing_ok=True)
        return False

    def fetch_cdn_or_pexels_gameplay(self, style_key: str, target_duration: float) -> Path:
        """
        Fetch gameplay loop directly from static CDN URLs or Pexels API,
        and cache in assets/gameplay/ for permanent local reuse.
        Never queries YouTube.
        """
        cached_file = self.cache_dir / f"{style_key}.mp4"
        if cached_file.exists() and cached_file.stat().st_size > 100000:
            print(f"[Gameplay/Cache] Found cached gameplay loop: {cached_file.name}")
            return cached_file

        style_info = DIRECT_CDN_GAMEPLAY.get(style_key, {})

        # 1. Try Direct CDN URLs
        cdn_urls = style_info.get("cdn_urls", [])
        for u in cdn_urls:
            if self._download_cdn_video(u, cached_file):
                return cached_file

        # 2. Try Pexels Video API (royalty-free CDN)
        print(f"[Gameplay/CDN] Querying Pexels CDN for '{style_key}' footage...")
        try:
            from ..visuals.pexels import PexelsVisualFetcher
            pvf = PexelsVisualFetcher()
            keywords = style_info.get("keywords", [f"{style_key} gameplay", "satisfying"])
            clip_asset = pvf.fetch_clip_for_scene(
                scene_id=random.randint(1000, 9999),
                keywords=keywords,
                duration=max(target_duration, 45.0),
            )
            if clip_asset and clip_asset.file_path.exists():
                shutil.copy2(clip_asset.file_path, cached_file)
                print(f"[Gameplay/CDN] Pexels gameplay loop cached: {cached_file.name}")
                return cached_file
        except Exception as pe:
            print(f"[Gameplay/CDN] Pexels CDN query error: {pe}")

        # 3. Fallback: Any existing cached gameplay video in assets/gameplay/
        existing = list(self.cache_dir.glob("*.mp4"))
        if existing:
            chosen = random.choice(existing)
            print(f"[Gameplay/CDN] Reusing existing cached background: {chosen.name}")
            return chosen

        raise RuntimeError(f"Could not source static CDN gameplay video for {style_key}")

    def download_dynamic_slice_yt(
        self,
        style_key: str,
        style_info: Dict[str, Any],
        target_duration: float,
        temp_dir: Path,
    ) -> Tuple[Path, str]:
        """Download dynamic slice via yt-dlp search (strictly local residential only)."""
        timestamp = int(time.time() * 1000)
        raw_download_path = temp_dir / f"dynamic_bg_{style_key}_{timestamp}.mp4"
        search_query = style_info.get("search_query", f"{style_key} gameplay no copyright")

        print(f"[Gameplay/Dynamic] Searching YouTube for fresh {style_info.get('title', style_key)}...")
        search_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },
        }
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{search_query}", download=False)
            entries = [e for e in info.get("entries", []) if (e.get("duration") or 0) >= (target_duration + 30)]
            if not entries:
                entries = info.get("entries", [])
            if not entries:
                raise RuntimeError(f"No YouTube entries found for {search_query}")
            chosen = random.choice(entries)
            target_url = f"https://www.youtube.com/watch?v={chosen['id']}"
            video_title = chosen.get("title", style_key)
            video_duration = float(chosen.get("duration") or 600)

        max_start = max(10, int(min(video_duration - target_duration - 20, 300)))
        start_sec = random.randint(15, max_start)
        end_sec = start_sec + int(target_duration) + 15

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
                    "player_client": ["android", "web"]
                }
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target_url])

        if not raw_download_path.exists():
            raise RuntimeError(f"Failed to stream dynamic slice from {target_url}")

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
        Source gameplay background (direct static CDN in cloud, or cached local),
        conform & crop to 9:16 vertical video using FFmpeg.
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        chosen_style, style_info = self.select_style(style)

        raw_video = None
        is_temp_download = False

        # In cloud environments (or if YouTube query is avoided), use static CDN / cached loops
        if self.is_cloud or os.environ.get("USE_STATIC_CDN", "1") == "1":
            print(f"[Gameplay/Manager] Cloud or CDN mode active: Sourcing '{chosen_style}' via CDN / cache...")
            raw_video = self.fetch_cdn_or_pexels_gameplay(chosen_style, target_duration)
            is_temp_download = False
        else:
            # Local residential execution: try dynamic YouTube search first, fall back to CDN
            try:
                raw_video, actual_title = self.download_dynamic_slice_yt(
                    style_key=chosen_style,
                    style_info=style_info,
                    target_duration=target_duration,
                    temp_dir=output_mp4.parent,
                )
                is_temp_download = True
            except Exception as yte:
                print(f"[Gameplay/Dynamic] YouTube search failed ({yte}), falling back to direct CDN...")
                raw_video = self.fetch_cdn_or_pexels_gameplay(chosen_style, target_duration)
                is_temp_download = False

        if not raw_video or not raw_video.exists():
            raise RuntimeError(f"Failed to resolve gameplay video source for style {chosen_style}")

        try:
            total_dur = self._probe_duration(raw_video)
            start_offset = 0.0
            if total_dur > target_duration + 2.0:
                max_offset = total_dur - target_duration
                start_offset = random.uniform(0.0, min(5.0, max_offset))

            print(
                f"[Gameplay/Manager] Formatting to {width}x{height} (Style: {chosen_style.upper()}): "
                f"{target_duration:.1f}s slice from {raw_video.name}..."
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
                "-an",
                str(output_mp4),
            ]

            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg background formatting failed: {res.stderr}")

            print(f"[Gameplay/Manager] Ready: {output_mp4.name} ({output_mp4.stat().st_size / 1024 / 1024:.1f} MB)")

        finally:
            if is_temp_download and raw_video.exists():
                raw_video.unlink(missing_ok=True)

        return output_mp4
