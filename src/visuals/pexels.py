import os
import re
import shutil
import hashlib
import requests
import threading
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Set, Dict
from ..config import config


@dataclass
class VideoClipAsset:
    scene_id: int
    file_path: Path
    duration: float
    keyword: str


SYNONYM_FALLBACKS: Dict[str, List[str]] = {
    "brain": ["neurons", "thinking", "microscope", "puzzle", "head", "abstract", "technology"],
    "baby": ["toddler", "child", "family", "crying", "crib", "people"],
    "money": ["cash", "coins", "wallet", "bank", "gold", "wealth", "luxury"],
    "airplane": ["flight", "runway", "sky", "clouds", "pilot", "cockpit", "travel"],
    "casino": ["poker", "roulette", "chips", "cards", "dice", "las vegas"],
    "clock": ["time", "hourglass", "watch", "sun", "pendulum", "calendar"],
    "computer": ["laptop", "keyboard", "code", "screen", "office", "typing"],
    "space": ["galaxy", "stars", "planet", "rocket", "astronaut", "universe"],
    "data": ["server", "network", "code", "digital", "matrix", "wires"],
    "sun": ["sunlight", "heat", "desert", "sky", "summer", "light"],
    "bird": ["eagle", "flying", "sky", "wings", "feathers", "nature"],
    "people": ["crowd", "person", "man", "woman", "face", "lifestyle"],
    "city": ["buildings", "traffic", "street", "metropolis", "architecture"],
    "nature": ["forest", "trees", "water", "mountain", "ocean", "river"],
    "fire": ["flame", "smoke", "burning", "sparks", "heat", "explosion"],
    "water": ["ocean", "waves", "sea", "river", "splash", "underwater"],
    "code": ["programming", "developer", "matrix", "hacker", "terminal", "screen"],
    "robot": ["ai", "android", "cyberpunk", "cyborg", "machine", "futuristic"],
    "pattern": ["abstract", "geometry", "fractal", "lines", "structure"],
    "sleep": ["bed", "night", "stars", "pillow", "darkness", "dream"],
}


class PexelsVisualFetcher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.pexels_api_key
        self.base_url = "https://api.pexels.com/v1/videos/search"
        self.headers = {
            "Authorization": self.api_key,
            "User-Agent": "AI-Shorts-Agent/1.0",
        } if self.api_key else {}
        self.cache_dir = config.broll_dir / "keyword_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session_used_files: Set[str] = set()
        self.session_used_urls: Set[str] = set()
        self.lock = threading.Lock()

    def reset_session(self):
        """Reset the deduplication pool at the start of every new video generation."""
        with self.lock:
            self.session_used_files.clear()
            self.session_used_urls.clear()

    def _extract_video_id(self, url: str) -> str:
        """Extract a unique alphanumeric ID from a video URL."""
        match = re.search(r"/videos/(\d+)/", url)
        if match:
            return match.group(1)
        return hashlib.md5(url.encode()).hexdigest()[:8]

    def _search_pexels(self, keyword: str) -> List[str]:
        """Search Pexels for portrait video links (returns multiple candidates)."""
        if not self.api_key:
            return []

        params = {
            "query": keyword,
            "orientation": "portrait",
            "per_page": 15,
        }

        try:
            resp = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=15,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            videos = data.get("videos", [])
            urls = []
            for video in videos:
                files = video.get("video_files", [])
                vertical_files = [
                    f for f in files
                    if f.get("height", 0) >= f.get("width", 0) and f.get("link")
                ]
                if vertical_files:
                    best = max(vertical_files, key=lambda x: x.get("height", 0))
                    urls.append(best["link"])
                elif files and files[0].get("link"):
                    urls.append(files[0]["link"])

            return urls
        except Exception:
            return []

    def _search_mixkit(self, keyword: str) -> List[str]:
        """Search Mixkit public stock videos and return multiple high-quality MP4 URLs."""
        clean_kw = re.sub(r"[^\w\s-]", "", keyword).strip().lower()
        if not clean_kw:
            return []

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://mixkit.co/free-stock-video/{clean_kw}/"
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200:
                return []

            mp4s = re.findall(r'https://assets\.mixkit\.co/videos/(\d+)/\1-720\.mp4', r.text)
            if not mp4s:
                mp4s = re.findall(r'https://assets\.mixkit\.co/videos/(\d+)/\1-1080\.mp4', r.text)
            if not mp4s:
                mp4s = re.findall(r'https://assets\.mixkit\.co/videos/(\d+)/', r.text)

            unique_ids = list(dict.fromkeys(mp4s))
            return [f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4" for vid in unique_ids]
        except Exception:
            return []

    def _get_local_broll_clip(self, scene_id: int) -> Optional[Path]:
        """Fallback to local assets/broll starter clips that have not been used in this session."""
        broll_clips = sorted(list(config.broll_dir.glob("clip_*.mp4")))
        if not broll_clips:
            return None

        unused = [c for c in broll_clips if c.name not in self.session_used_files]
        if unused:
            return unused[0]

        return broll_clips[(scene_id - 1) % len(broll_clips)]

    def fetch_clip_for_scene(
        self,
        scene_id: int,
        keywords: List[str],
        duration: float,
    ) -> VideoClipAsset:
        """Download or retrieve a strictly unique vertical video clip for this scene."""
        output_file = config.temp_dir / f"scene_{scene_id}.mp4"

        with self.lock:
            # Build search terms: primary keywords + fallback synonyms
            search_terms = []
            for kw in keywords:
                clean = re.sub(r"[^\w-]", "", kw.lower())
                if clean and clean not in search_terms:
                    search_terms.append(clean)
                for syn in SYNONYM_FALLBACKS.get(clean, []):
                    if syn not in search_terms:
                        search_terms.append(syn)

            # 1. Check local keyword cache for an UNUSED clip matching any search term
            for term in search_terms:
                candidates = sorted(list(self.cache_dir.glob(f"{term}*.mp4")))
                for cand in candidates:
                    if cand.exists() and cand.stat().st_size > 100000:
                        if cand.name not in self.session_used_files:
                            self.session_used_files.add(cand.name)
                            shutil.copy2(cand, output_file)
                            return VideoClipAsset(
                                scene_id=scene_id,
                                file_path=output_file,
                                duration=duration,
                                keyword=term,
                            )

            # 2. Try online search (Pexels / Mixkit) for an unused candidate URL
            for term in search_terms:
                urls = []
                if self.api_key:
                    urls.extend(self._search_pexels(term))
                urls.extend(self._search_mixkit(term))

                for url in urls:
                    vid_id = self._extract_video_id(url)
                    cache_key = f"{term}_{vid_id}.mp4"
                    if vid_id in self.session_used_urls or cache_key in self.session_used_files:
                        continue

                    # Download candidate
                    try:
                        resp = requests.get(url, stream=True, timeout=25)
                        if resp.status_code == 200:
                            cached_clip = self.cache_dir / cache_key
                            with open(cached_clip, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=16384):
                                    f.write(chunk)

                            self.session_used_urls.add(vid_id)
                            self.session_used_files.add(cache_key)
                            shutil.copy2(cached_clip, output_file)
                            return VideoClipAsset(
                                scene_id=scene_id,
                                file_path=output_file,
                                duration=duration,
                                keyword=term,
                            )
                    except Exception:
                        continue

            # 3. Use local high-res vertical B-roll vault with deduplication
            local_clip = self._get_local_broll_clip(scene_id)
            if local_clip and local_clip.exists():
                self.session_used_files.add(local_clip.name)
                shutil.copy2(local_clip, output_file)
                return VideoClipAsset(
                    scene_id=scene_id,
                    file_path=output_file,
                    duration=duration,
                    keyword=keywords[0] if keywords else "broll",
                )

            # 4. Emergency generator
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe, "-y", "-f", "lavfi",
                "-i", "color=c=0x111122:size=1080x1920:rate=30",
                "-t", str(duration), "-pix_fmt", "yuv420p",
                str(output_file)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return VideoClipAsset(
                scene_id=scene_id,
                file_path=output_file,
                duration=duration,
                keyword="fallback",
            )
