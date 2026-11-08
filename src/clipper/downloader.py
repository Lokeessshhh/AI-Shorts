"""Mode 3 Video & Audio Ingestion Engine.
Handles zero-video transcription, selective range slicing via yt-dlp,
cookie support for bot challenge avoidance, and local video ingestion.
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
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

    def _get_cookie_file(self) -> Optional[Path]:
        """Check if cookies.txt exists in root or is provided in env var YOUTUBE_COOKIES."""
        cookie_path = config.root_dir / "cookies.txt"
        if cookie_path.exists():
            return cookie_path

        env_cookies = os.environ.get("YOUTUBE_COOKIES", "").strip()
        if env_cookies:
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(env_cookies)
            return cookie_path

        return None

    def is_url(self, source: str) -> bool:
        """Check if the source string is a web URL."""
        source_clean = source.strip()
        return bool(re.match(r"^https?://[^\s]+$", source_clean, re.IGNORECASE))

    def extract_video_id(self, source: str) -> str:
        """Extract YouTube video ID from URL or return string as-is."""
        m = re.search(r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})", source)
        if m:
            return m.group(1)
        return source.strip()

    def get_info(self, source: str) -> Dict[str, Any]:
        """Fetch video metadata without downloading video stream bytes."""
        if self.is_url(source):
            ydl_opts: Dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "ffmpeg_location": self.ffmpeg_path,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"]
                    }
                },
            }
            cookie_file = self._get_cookie_file()
            if cookie_file:
                ydl_opts["cookiefile"] = str(cookie_file)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(source, download=False)
                    return {
                        "id": info.get("id", self.extract_video_id(source)),
                        "title": info.get("title", "Untitled Video"),
                        "duration": float(info.get("duration") or 0.0),
                        "uploader": info.get("uploader", info.get("channel", "Unknown")),
                        "view_count": info.get("view_count", 0),
                        "is_local": False,
                        "url": source,
                    }
            except Exception as e:
                print(f"[Clipper] get_info warning ({e}), falling back to standard extraction...")
                ydl_opts["extract_flat"] = False
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(source, download=False)
                    return {
                        "id": info.get("id", self.extract_video_id(source)),
                        "title": info.get("title", "Untitled Video"),
                        "duration": float(info.get("duration") or 0.0),
                        "uploader": info.get("uploader", info.get("channel", "Unknown")),
                        "view_count": info.get("view_count", 0),
                        "is_local": False,
                        "url": source,
                    }
        else:
            local_path = Path(source).resolve()
            if not local_path.exists():
                raise FileNotFoundError(f"Local video file not found: {local_path}")

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
        cmd = [self.ffmpeg_path, "-i", str(file_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        for line in res.stderr.splitlines():
            if "Duration:" in line:
                parts = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = parts.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
        return 0.0

    def get_transcript_and_meta(
        self,
        source: str,
        transcriber: Optional[Any] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Zero-Video Transcription:
        Fetches word-level transcript in <1 second without downloading video bytes via youtube-transcript-api.
        Falls back to audio-only stream download + Whisper if captions are missing.
        """
        meta = self.get_info(source)
        video_id = meta["id"]

        raw_snippets = None
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            if hasattr(api, "fetch"):
                fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
                raw_snippets = [
                    {"text": s.text, "start": float(s.start), "duration": float(s.duration)}
                    for s in fetched
                ]
            elif hasattr(YouTubeTranscriptApi, "get_transcript"):
                raw_snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
        except Exception as e:
            print(f"[Clipper] Direct caption fetch skipped ({e}), attempting list_transcripts...")
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                if hasattr(YouTubeTranscriptApi, "list_transcripts"):
                    tlist = YouTubeTranscriptApi.list_transcripts(video_id)
                    t = None
                    try:
                        t = tlist.find_transcript(["en", "en-US", "en-GB"])
                    except Exception:
                        try:
                            t = tlist.find_generated_transcript(["en"])
                        except Exception:
                            pass
                    if t:
                        fetched = t.fetch()
                        raw_snippets = [
                            {"text": s.get("text", s.text if hasattr(s, "text") else ""),
                             "start": float(s.get("start", s.start if hasattr(s, "start") else 0)),
                             "duration": float(s.get("duration", s.duration if hasattr(s, "duration") else 1))}
                            for s in fetched
                        ]
            except Exception as e2:
                print(f"[Clipper] youtube-transcript-api unavailable: {e2}")

        if raw_snippets:
            all_words: List[Dict[str, Any]] = []
            segments: List[Dict[str, Any]] = []
            formatted_blocks: List[str] = []
            seg_id = 0

            for snip in raw_snippets:
                text = snip["text"].strip().replace("\n", " ")
                if not text or text.startswith("["):
                    continue
                words = text.split()
                if not words:
                    continue
                start = snip["start"]
                dur = max(0.2, snip["duration"])
                w_dur = dur / len(words)

                seg_words = []
                for i, w in enumerate(words):
                    w_start = round(start + i * w_dur, 3)
                    w_end = round(w_start + w_dur, 3)
                    w_obj = {"word": w, "start": w_start, "end": w_end, "probability": 1.0}
                    seg_words.append(w_obj)
                    all_words.append(w_obj)

                segments.append({
                    "id": seg_id,
                    "start": round(start, 3),
                    "end": round(start + dur, 3),
                    "text": text,
                    "words": seg_words,
                })
                formatted_blocks.append(f"[{round(start, 1)}s -> {round(start + dur, 1)}s] {text}")
                seg_id += 1

            transcript_data = {
                "total_words": len(all_words),
                "segments": segments,
                "words": all_words,
                "formatted_text": "\n".join(formatted_blocks),
            }
            print(f"[Clipper] Zero-Video Transcript retrieved: {len(all_words)} words in <1s!")
            return meta, transcript_data

        # Fallback: Audio-Only stream download + local/API Whisper
        print("[Clipper] No cloud captions found. Sourcing audio track only (lightweight)...")
        audio_file = self.download_audio_only(source)
        if transcriber is None:
            from .transcriber import LongFormTranscriber
            transcriber = LongFormTranscriber()

        cache_json = audio_file.parent / "transcript.json"
        transcript_data = transcriber.transcribe(audio_file, cache_json_path=cache_json)
        return meta, transcript_data

    def download_audio_only(self, source: str) -> Path:
        """Download lightweight audio stream only (no video) for speech-to-text fallback."""
        meta = self.get_info(source)
        video_id = meta["id"]
        save_dir = self.cache_dir / video_id
        save_dir.mkdir(parents=True, exist_ok=True)
        audio_file = save_dir / f"{video_id}_16k.wav"

        if audio_file.exists() and audio_file.stat().st_size > 10000:
            return audio_file

        raw_audio = save_dir / f"{video_id}_audio.m4a"
        print(f"[Clipper] Sourcing audio-only track: {meta['title']} ({video_id})...")

        ydl_opts: Dict[str, Any] = {
            "format": "ba/bestaudio",
            "outtmpl": str(raw_audio),
            "ffmpeg_location": self.ffmpeg_path,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },
        }
        cookie_file = self._get_cookie_file()
        if cookie_file:
            ydl_opts["cookiefile"] = str(cookie_file)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source])

        # Convert to 16kHz mono WAV for Whisper
        if raw_audio.exists():
            self.extract_whisper_audio(raw_audio, audio_file)
            raw_audio.unlink(missing_ok=True)

        if not audio_file.exists():
            raise RuntimeError(f"Audio-only stream download failed for {source}")

        return audio_file

    def download_slice(
        self,
        source: str,
        start_time: float,
        end_time: float,
        output_path: Path,
    ) -> Path:
        """
        Selective Range Slicing:
        Instructs yt-dlp to stream and download ONLY the 30-60s slice of video directly.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        duration_s = end_time - start_time
        print(f"[Clipper] Selective Range Slicing: {start_time:.1f}s -> {end_time:.1f}s (~{duration_s:.1f}s clip)...")

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--download-sections", f"*{start_time:.2f}-{end_time:.2f}",
            "--force-keyframes-at-cuts",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
        ]
        cookie_file = self._get_cookie_file()
        if cookie_file:
            cmd.extend(["--cookies", str(cookie_file)])

        cmd.append(source)

        res = subprocess.run(cmd, capture_output=True, text=True)

        if not output_path.exists():
            matches = list(output_path.parent.glob(f"{output_path.stem}*.mp4"))
            if matches:
                matches[0].rename(output_path)

        if not output_path.exists():
            raise RuntimeError(f"yt-dlp slice download failed: {res.stderr or res.stdout}")

        print(f"[Clipper] Slice downloaded in seconds -> {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return output_path

    def download_or_ingest(
        self,
        source: str,
        progress_hook: Optional[Any] = None,
    ) -> Tuple[Path, Path, Dict[str, Any]]:
        """Download full video (used for local files or full archive caching)."""
        if self.is_url(source):
            info = self.get_info(source)
            video_id = info["id"]
            save_dir = self.cache_dir / video_id
            save_dir.mkdir(parents=True, exist_ok=True)

            video_file = save_dir / f"{video_id}.mp4"
            audio_file = save_dir / f"{video_id}_16k.wav"

            if video_file.exists() and video_file.stat().st_size > 1024 * 1024:
                print(f"[Clipper] Found cached video: {video_file.name}")
            else:
                print(f"[Clipper] Downloading video: {info['title']} ({video_id})...")
                ydl_opts: Dict[str, Any] = {
                    "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
                    "outtmpl": str(save_dir / f"{video_id}.%(ext)s"),
                    "merge_output_format": "mp4",
                    "ffmpeg_location": self.ffmpeg_path,
                    "quiet": False,
                    "no_warnings": True,
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["android", "web"]
                        }
                    },
                }
                cookie_file = self._get_cookie_file()
                if cookie_file:
                    ydl_opts["cookiefile"] = str(cookie_file)
                if progress_hook:
                    ydl_opts["progress_hooks"] = [progress_hook]

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([source])

                if not video_file.exists():
                    found_mp4s = list(save_dir.glob("*.mp4"))
                    if found_mp4s:
                        found_mp4s[0].rename(video_file)

            if not video_file.exists():
                raise RuntimeError(f"Video download failed; {video_file} not found.")

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
        """Extract clean 16kHz mono WAV audio from video using FFmpeg."""
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
