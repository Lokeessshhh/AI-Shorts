"""Mode 3: Playwright Headless Video Recorder.
Records the dynamic ChatGPT HTML conversation in native 1080x1920 vertical resolution,
and muxes with synchronized sound effects and background music via FFmpeg.
"""

import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright

from ..config import config


class VideoRecorder:
    """Headless browser video recorder for Mode 3 ChatGPT conversations."""

    def __init__(self, width: int = 1080, height: int = 1920):
        self.width = width
        self.height = height
        self.ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"

    def record_html_to_video(
        self,
        html_content: str,
        audio_path: Path,
        output_mp4: Path,
        temp_dir: Path,
        total_duration: float,
    ) -> Path:
        """
        Loads HTML into headless Chromium/Edge with record_video enabled,
        waits for completion signal window.__CHAT_FINISHED__, and muxes with audio.
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_mp4.parent.mkdir(parents=True, exist_ok=True)

        html_file = temp_dir / "chat_scene.html"
        html_file.write_text(html_content, encoding="utf-8")

        raw_video_dir = temp_dir / "raw_record"
        raw_video_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Mode3/Recorder] Launching headless browser for {self.width}x{self.height} vertical capture...")

        with sync_playwright() as p:
            # Try msedge first, fallback to standard chromium
            browser = None
            try:
                browser = p.chromium.launch(channel="msedge", headless=True)
            except Exception:
                browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                viewport={"width": self.width, "height": self.height},
                record_video_dir=str(raw_video_dir),
                record_video_size={"width": self.width, "height": self.height},
                device_scale_factor=1,
            )

            page = context.new_page()
            url = f"file:///{str(html_file.resolve()).replace('\\', '/')}"
            page.goto(url)

            print(f"[Mode3/Recorder] Recording conversation playback (approx {total_duration:.1f}s)...")
            timeout_ms = int((total_duration + 15) * 1000)
            try:
                page.wait_for_function("window.__CHAT_FINISHED__ === true", timeout=timeout_ms)
            except Exception as e:
                print(f"[Mode3/Recorder] Warning: Playback wait ended with: {e}")

            time.sleep(0.6)
            page.close()
            context.close()
            browser.close()

        # Locate recorded video file
        recorded_files = list(raw_video_dir.glob("*.webm")) + list(raw_video_dir.glob("*.mp4"))
        if not recorded_files:
            raise RuntimeError(f"[Mode3/Recorder] No recorded video file found in {raw_video_dir}")

        raw_video = recorded_files[0]
        print(f"[Mode3/Recorder] Captured raw video ({raw_video.stat().st_size / 1024 / 1024:.2f} MB). Muxing with SFX...")

        # Final FFmpeg encode: H.264 high quality 60fps vertical MP4 with synchronized audio
        cmd = [
            self.ffmpeg_path, "-y", "-loglevel", "error",
            "-i", str(raw_video),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_mp4),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"[Mode3/Recorder] FFmpeg muxing failed: {res.stderr}")

        # Cleanup raw recordings
        shutil.rmtree(raw_video_dir, ignore_errors=True)
        html_file.unlink(missing_ok=True)

        print(f"[Mode3/Recorder] Successfully rendered final Short -> {output_mp4.name} ({output_mp4.stat().st_size / 1024 / 1024:.2f} MB)")
        return output_mp4
