"""YouTube Shorts Publisher via YouTube Data API v3.
Handles resumable video uploads, metadata parsing, and token auto-refresh.
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class YouTubeUploader:
    """Uploads videos to YouTube Shorts using OAuth 2.0 refreshable credentials."""

    def __init__(self, token_path: Optional[Path] = None):
        root_dir = Path(__file__).resolve().parent.parent.parent
        self.token_path = token_path or (root_dir / "credentials" / "youtube_token.json")
        self.client_secret_path = root_dir / "credentials" / "client_secret.json"
        self._service = None

    def is_authenticated(self) -> bool:
        """Check if YouTube credentials exist."""
        return self.token_path.exists()

    def get_service(self):
        """Load and return authenticated YouTube Resource, refreshing token if expired."""
        if not self.is_authenticated():
            raise FileNotFoundError(
                f"YouTube token not found at {self.token_path}. Run 'python -m src.publisher.auth_youtube' first."
            )

        if self._service is None:
            creds = Credentials.from_authorized_user_file(str(self.token_path))
            if creds and creds.expired and creds.refresh_token:
                print("[YouTube] Access token expired, refreshing...")
                creds.refresh(Request())
                with open(self.token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

            self._service = build("youtube", "v3", credentials=creds)

        return self._service

    def parse_metadata_file(self, meta_path: Path) -> Dict[str, Any]:
        """Parse YouTube title, description, and hashtags from metadata text file."""
        if not meta_path.exists():
            return {}

        text = meta_path.read_text(encoding="utf-8")

        # Title
        m_title = re.search(r"(?:CLIP )?TITLE:\s*\n([^\n]+)", text)
        title = m_title.group(1).strip() if m_title else "AI Short"

        # Hook / Description
        m_hook = re.search(r'HOOK(?:\s*\([^)]*\))?:\s*\n"?([^"\n]+)"?', text)
        hook = m_hook.group(1).strip() if m_hook else ""

        m_desc = re.search(r"DESCRIPTION:\s*\n(.*?)(?=\nHASHTAGS:|\nPINNED COMMENT:|$)", text, re.DOTALL)
        desc_body = m_desc.group(1).strip() if m_desc else hook

        # Hashtags
        m_tags = re.search(r"HASHTAGS:\s*\n([^\n]+)", text)
        tags_str = m_tags.group(1).strip() if m_tags else "#shorts #viral #tech"
        tags = [t.lstrip("#") for t in tags_str.split() if t.startswith("#")]

        return {
            "title": title,
            "description": f"{desc_body}\n\n{tags_str}\n\n#Shorts",
            "tags": tags,
        }

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category_id: str = "28",  # 28: Science & Technology, 27: Education
        privacy_status: str = "public",  # public, unlisted, private
    ) -> Dict[str, Any]:
        """
        Upload vertical MP4 to YouTube Shorts.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        youtube = self.get_service()

        # YouTube Shorts requires #Shorts in title or description
        clean_title = title.strip()
        if "#Shorts" not in clean_title and "#shorts" not in clean_title:
            if len(clean_title) <= 90:
                clean_title = f"{clean_title} #Shorts"
            else:
                clean_title = f"{clean_title[:90]} #Shorts"

        clean_tags = list(tags or [])
        if "shorts" not in [t.lower() for t in clean_tags]:
            clean_tags.append("shorts")

        body = {
            "snippet": {
                "title": clean_title[:100],
                "description": description or f"{clean_title}\n\n#Shorts",
                "tags": clean_tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        print(f"\n[YouTube] Uploading '{clean_title}' ({privacy_status})...")
        print(f"  * File: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            chunksize=1024 * 1024 * 8,  # 8MB chunks
            resumable=True,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"  * Upload progress: {progress}%")

        video_id = response.get("id")
        short_url = f"https://youtube.com/shorts/{video_id}"
        print(f"[YouTube/SUCCESS] Published Short: {short_url}")

        return {
            "platform": "youtube",
            "video_id": video_id,
            "url": short_url,
            "title": clean_title,
            "privacy_status": privacy_status,
        }

    def upload_from_metadata(
        self,
        video_path: Path,
        metadata_path: Optional[Path] = None,
        privacy_status: str = "public",
    ) -> Dict[str, Any]:
        """Convenience method to upload video by reading copy from its metadata .txt file."""
        if metadata_path and metadata_path.exists():
            meta = self.parse_metadata_file(metadata_path)
            title = meta.get("title", video_path.stem)
            description = meta.get("description", "")
            tags = meta.get("tags", [])
        else:
            title = video_path.stem.replace("_", " ").title()
            description = f"{title}\n\n#Shorts"
            tags = ["shorts", "viral"]

        return self.upload_short(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
        )
