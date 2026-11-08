"""Instagram Reels Publisher via instagrapi.
Uploads vertical MP4 clips directly as Instagram Reels using saved session cookies.
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from instagrapi import Client


class InstagramUploader:
    """Uploads videos to Instagram Reels using persistent session authentication."""

    def __init__(self, session_path: Optional[Path] = None):
        root_dir = Path(__file__).resolve().parent.parent.parent
        self.session_path = session_path or (root_dir / "credentials" / "instagram_session.json")
        self._client: Optional[Client] = None

    def is_authenticated(self) -> bool:
        """Check if Instagram session cookie exists."""
        return self.session_path.exists()

    def get_client(self) -> Client:
        """Load client and restore authenticated session."""
        if not self.is_authenticated():
            raise FileNotFoundError(
                f"Instagram session not found at {self.session_path}. Run 'python -m src.publisher.auth_instagram' first."
            )

        if self._client is None:
            cl = Client()
            cl.delay_range = [2, 5]
            cl.load_settings(self.session_path)
            self._client = cl

        return self._client

    def parse_metadata_file(self, meta_path: Path) -> str:
        """Parse Instagram caption (title, hook, body, and hashtags) from metadata file."""
        if not meta_path.exists():
            return "Check out this Reel! 🔥 #shorts #viral #reels"

        text = meta_path.read_text(encoding="utf-8")

        # Title
        m_title = re.search(r"(?:CLIP )?TITLE:\s*\n([^\n]+)", text)
        title = m_title.group(1).strip() if m_title else ""

        # Hook
        m_hook = re.search(r'HOOK(?:\s*\([^)]*\))?:\s*\n"?([^"\n]+)"?', text)
        hook = m_hook.group(1).strip() if m_hook else ""

        # Description
        m_desc = re.search(r"DESCRIPTION:\s*\n(.*?)(?=\nHASHTAGS:|\nPINNED COMMENT:|$)", text, re.DOTALL)
        desc = m_desc.group(1).strip() if m_desc else ""

        # Hashtags
        m_tags = re.search(r"HASHTAGS:\s*\n([^\n]+)", text)
        tags_str = m_tags.group(1).strip() if m_tags else "#reels #viral #explore"
        if "#reels" not in tags_str:
            tags_str = f"{tags_str} #reels"

        caption_parts = []
        if title:
            caption_parts.append(f"✨ {title}\n")
        if hook:
            caption_parts.append(f'"{hook}"\n')
        if desc and desc != hook:
            caption_parts.append(f"{desc}\n")
        caption_parts.append("Drop your thoughts in the comments below! 👇\n")
        caption_parts.append(tags_str)

        return "\n".join(caption_parts)

    def upload_reel(
        self,
        video_path: Path,
        caption: str,
    ) -> Dict[str, Any]:
        """Upload video file as an Instagram Reel."""
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cl = self.get_client()

        print(f"\n[Instagram] Uploading Reel: {video_path.name}...")
        print(f"  * Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")

        # Explicitly generate a thumbnail image to avoid Linux / MoviePy dependencies
        thumb_path = video_path.with_suffix(".thumb.jpg")
        try:
            import subprocess, shutil
            import imageio_ffmpeg
            ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [
                    ffmpeg_exe, "-y", "-loglevel", "error",
                    "-ss", "00:00:01",
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-q:v", "2",
                    str(thumb_path)
                ],
                check=True,
                capture_output=True,
            )
        except Exception as e:
            print(f"  * [Warning] FFmpeg thumbnail generation skipped: {e}")

        try:
            media = cl.clip_upload(
                path=str(video_path),
                caption=caption,
                thumbnail=str(thumb_path) if thumb_path.exists() else None,
            )
        finally:
            if thumb_path.exists():
                thumb_path.unlink(missing_ok=True)

        media_code = getattr(media, "code", str(getattr(media, "pk", "")))
        reel_url = f"https://www.instagram.com/reel/{media_code}/"
        print(f"[Instagram/SUCCESS] Published Reel: {reel_url}")

        return {
            "platform": "instagram",
            "media_id": str(getattr(media, "pk", "")),
            "media_code": media_code,
            "url": reel_url,
            "caption": caption[:100],
        }

    def upload_from_metadata(
        self,
        video_path: Path,
        metadata_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Convenience method to upload video by reading copy from its metadata .txt file."""
        if metadata_path and metadata_path.exists():
            caption = self.parse_metadata_file(metadata_path)
        else:
            caption = f"✨ {video_path.stem.replace('_', ' ').title()}\n\n#reels #viral #trending"

        return self.upload_reel(video_path=video_path, caption=caption)
