"""Mode 3 Video & Audio Ingestion Engine.
Handles downloading YouTube videos via yt-dlp or ingesting local video files,
extracting video metadata, caching, and exporting lightweight 16kHz mono WAV for Whisper.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import imageio_ffmpeg
import yt_dlp

from ..config import config


class VideoDownloader:
    """Downloader and audio extractor for long-form video inputs."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or config.clipper_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = self._locate_ffmpeg()

    def _locate_ffmpeg(self) -> str:
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()

    def is_url(self, source: str) -> bool:
        """Check if the source string is a web URL."""
        source_clean = source.strip()
        return bool(re.match(r"^https?://[^\s]+$", source_clean, re.IGNORECASE))

    def get_info(self, source: str) -> Dict[str, Any]:
        """Fetch video metadata without necessarily downloading."""
        if self.is_url(source):
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "ffmpeg_location": self.ffmpeg_path,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source, download=False)
                return {
                    "id": info.get("id", "web_video"),
                    "title": info.get("title", "Untitled Video"),
                    "duration": float(info.get("duration", 0)),
                    "uploader": info.get("uploader", "Unknown"),
                    "view_count": info.get("view_count", 0),
                    "is_local": False,
                    "url": source,
                }
        else:
            local_path = Path(source).resolve()
            if not local_path.exists():
                raise FileNotFoundError(f"Local video file not found: {local_path}")
            
            # Use ffprobe to query duration
            duration = self._probe_duration(local_path)
            return {
                "id": local_path.stem,
                "title": local_path.stem.replace("_", " ").title(),
                "duration": duration,
                "uploader": "Local File",
                "view_count": 0,
                "is_local": True,
                "path": str(local_path),
            }

    def _probe_duration(self, file_path: Path) -> float:
        """Query duration of a local video file using ffmpeg/ffprobe."""
        cmd = [
            self.ffmpeg_path,
            "-i", str(file_path),
        ]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                # Duration: 00:05:23.12, start: ...
                parts = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = parts.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
        return 0.0

    def download_or_ingest(
        self,
        source: str,
        progress_hook: Optional[Any] = None,
    ) -> Tuple[Path, Path, Dict[str, Any]]:
        """
        Download YouTube video or ingest local video file.
        Returns:
            Tuple[Path (video_path), Path (audio_wav_path), Dict (metadata)]
        """
        if self.is_url(source):
            info = self.get_info(source)
            video_id = info["id"]
            save_dir = self.cache_dir / video_id
            save_dir.mkdir(parents=True, exist_ok=True)

            video_file = save_dir / f"{video_id}.mp4"
            audio_file = save_dir / f"{video_id}_16k.wav"

            # Check if cached files already exist
            if video_file.exists() and video_file.stat().st_size > 1024 * 1024:
                print(f"[Clipper] Found cached video: {video_file.name}")
            else:
                print(f"[Clipper] Downloading video: {info['title']} ({video_id})...")
                has_subs = any(save_dir.glob("*.json3"))
                ydl_opts = {
                    # Best video up to 1080p (prefer direct https) + best audio, muxed to mp4
                    "format": "bestvideo[height<=1080][ext=mp4][protocol^=http]+bestaudio[ext=m4a][protocol^=http]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080] / best[height<=1080]/best",
                    "outtmpl": str(save_dir / f"{video_id}.%(ext)s"),
                    "merge_output_format": "mp4",
                    "ffmpeg_location": self.ffmpeg_path,
                    "writeautomaticsub": not has_subs,
                    "subtitleslangs": ["en-orig", "en"],
                    "subtitlesformat": "json3",
                    "quiet": False,
                    "no_warnings": True,
                }
                if progress_hook:
                    ydl_opts["progress_hooks"] = [progress_hook]

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([source])
                except Exception as e:
                    if not video_file.exists():
                        print(f"[Clipper] Warning: initial download encountered ({e}), retrying video-only...")
                        ydl_opts["writeautomaticsub"] = False
                        ydl_opts.pop("subtitleslangs", None)
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([source])

                # Ensure filename is exactly video_id.mp4
                if not video_file.exists():
                    found_mp4s = list(save_dir.glob("*.mp4"))
                    if found_mp4s:
                        found_mp4s[0].rename(video_file)

            if not video_file.exists():
                raise RuntimeError(f"Video download failed; {video_file} not found.")

            # Extract 16kHz mono WAV for Whisper
            if not audio_file.exists() or audio_file.stat().st_size == 0:
                self.extract_whisper_audio(video_file, audio_file)

            return video_file, audio_file, info

        else:
            local_path = Path(source).resolve()
            if not local_path.exists():
                raise FileNotFoundError(f"Local file does not exist: {local_path}")

            info = self.get_info(source)
            safe_id = re.sub(r"[^\w\-]", "_", local_path.stem)
            save_dir = self.cache_dir / safe_id
            save_dir.mkdir(parents=True, exist_ok=True)

            audio_file = save_dir / f"{safe_id}_16k.wav"
            if not audio_file.exists() or audio_file.stat().st_size == 0:
                self.extract_whisper_audio(local_path, audio_file)

            return local_path, audio_file, info

    def extract_whisper_audio(self, video_path: Path, output_wav: Path) -> Path:
        """
        Extract clean 16kHz mono WAV audio from video using FFmpeg.
        Whisper models perform fastest and most accurately on 16kHz mono PCM.
        """
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        print(f"[Clipper] Extracting 16kHz mono audio -> {output_wav.name}...")
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-loglevel", "error",
            "-i", str(video_path),
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output_wav),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")
        return output_wav
