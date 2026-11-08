"""Mode 2 Real Stock Image Fetcher.
Replaces AI generation with instant, crisp, high-resolution real-world stock media:
1. DuckDuckGo Image Search (ddgs / duckduckgo_search)
2. Wikimedia Commons high-resolution photography search fallback
3. Pexels API fallback
4. High-aesthetic procedural fallback
Zero AI hallucination, sub-second fetching, perfectly grounded visual metaphors.
"""

import io
import os
import re
import urllib.parse
from pathlib import Path
from typing import Optional, List
import requests
from PIL import Image, ImageDraw, ImageFont

from ..config import config


class WebImageFetcher:
    """Fetches real-world stock photos and icons matching spoken dialogue concepts."""

    def __init__(self):
        self.cache_dir = config.temp_dir / "image_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def fetch_image(self, query: str, output_path: Path) -> Path:
        """
        Search for real, crisp photos matching the query using DuckDuckGo,
        with Wikimedia Commons and Pexels fallbacks.
        """
        if output_path.exists() and output_path.stat().st_size > 5000:
            return output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)
        clean_query = query.strip()
        print(f"[WebImageFetcher] Sourcing real stock photo for: '{clean_query}'...")

        # 1. DuckDuckGo Image Search (via ddgs / duckduckgo_search)
        ddg_results = self._search_duckduckgo(clean_query)
        for img_url in ddg_results:
            if self._download_and_validate(img_url, output_path):
                print(f"[WebImageFetcher] Saved DuckDuckGo stock photo -> {output_path.name}")
                return output_path

        # 2. Wikimedia Commons Photography Search Fallback
        wiki_results = self._search_wikimedia(clean_query)
        for img_url in wiki_results:
            if self._download_and_validate(img_url, output_path):
                print(f"[WebImageFetcher] Saved Wikimedia stock photo -> {output_path.name}")
                return output_path

        # 3. Pexels API Fallback
        pexels_img = self._fetch_pexels_fallback(clean_query, output_path)
        if pexels_img and output_path.exists():
            return output_path

        # 4. Clean Procedural Fallback
        print(f"[WebImageFetcher] Using procedural concept graphic -> {output_path.name}")
        self._generate_procedural_fallback(clean_query, output_path)
        return output_path

    def _search_duckduckgo(self, query: str) -> List[str]:
        """Query DuckDuckGo for top 3 high quality image URLs."""
        search_terms = f"{query} high quality photo"
        results = []

        # Try ddgs first
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                res = list(ddgs.images(keywords=search_terms, max_results=3))
                for r in res:
                    u = r.get("image")
                    if u and u.startswith("http"):
                        results.append(u)
            if results:
                return results
        except Exception:
            pass

        # Try duckduckgo_search
        try:
            from duckduckgo_search import DDGS as OldDDGS
            with OldDDGS() as ddgs:
                res = list(ddgs.images(keywords=search_terms, max_results=3))
                for r in res:
                    u = r.get("image")
                    if u and u.startswith("http"):
                        results.append(u)
        except Exception as e:
            print(f"[WebImageFetcher] DDG search notice: {e}")

        return results

    def _search_wikimedia(self, query: str) -> List[str]:
        """Query Wikimedia Commons for public domain stock photos."""
        encoded = urllib.parse.quote(query)
        url = (
            f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
            f"&gsrnamespace=6&gsrsearch={encoded}+filetype:bitmap"
            f"&gsrlimit=3&prop=imageinfo&iiprop=url|mime&format=json"
        )
        try:
            res = self.session.get(url, timeout=8).json()
            pages = res.get("query", {}).get("pages", {})
            urls = []
            for pid, p in pages.items():
                for info in p.get("imageinfo", []):
                    mime = info.get("mime", "")
                    img_url = info.get("url")
                    if img_url and ("jpeg" in mime or "png" in mime or "webp" in mime):
                        urls.append(img_url)
            return urls
        except Exception:
            return []

    def _download_and_validate(self, url: str, output_path: Path) -> bool:
        """Download URL and verify it can be decoded by Pillow."""
        try:
            res = self.session.get(url, timeout=6)
            if res.status_code == 200 and len(res.content) > 4000:
                img = Image.open(io.BytesIO(res.content)).convert("RGBA")
                if img.width >= 200 and img.height >= 200:
                    img.save(str(output_path), "PNG")
                    return True
        except Exception:
            pass
        return False

    def _fetch_pexels_fallback(self, query: str, output_path: Path) -> Optional[Path]:
        """Fetch real photo from Pexels API if API key is present."""
        if not config.pexels_api_key:
            return None
        try:
            from ..visuals.pexels import PexelsClient
            client = PexelsClient()
            photos = client.search_photos(query, orientation="landscape", per_page=1)
            if photos:
                client.download_photo(photos[0], output_path)
                return output_path
        except Exception as e:
            print(f"[WebImageFetcher] Pexels fallback skipped: {e}")
        return None

    def _generate_procedural_fallback(self, query: str, output_path: Path, width: int = 720, height: int = 520) -> Path:
        """Generate sleek dark cyber graphic if offline."""
        canvas = Image.new("RGBA", (width, height), (15, 23, 42, 255))
        draw = ImageDraw.Draw(canvas)

        # Gradient
        for y in range(height):
            ratio = y / height
            draw.line([(0, y), (width, y)], fill=(int(15 + 10 * ratio), int(23 + 20 * ratio), int(42 + 30 * ratio), 255))

        # Glowing accent badge
        cx, cy = width // 2, height // 2
        draw.rounded_rectangle([cx - 140, cy - 60, cx + 140, cy + 60], radius=18, fill=(30, 41, 59, 230), outline=(56, 189, 248, 220), width=3)

        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 28)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), query.title(), font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((width - tw) // 2, cy - 16), query.title(), font=font, fill=(248, 250, 252, 255))

        canvas.save(output_path, "PNG")
        return output_path
