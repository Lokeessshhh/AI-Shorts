"""Universal Encyclopedic Concept Image Fetcher with MD5 disk caching.
Cascades:
1. Wikipedia REST API Canonical Article Hero Image (pristine high-resolution photography)
2. Wikimedia Commons Media Deep Search (105M+ public domain educational & hardware media)
3. DuckDuckGo Image Web Search
4. Procedural fallback (safety guard)
"""

import os
import re
import hashlib
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests
from PIL import Image, ImageDraw, ImageFont

from ..config import config


class ConceptImageFetcher:
    """Universal, zero-dependency encyclopedic image fetcher with MD5 disk caching."""

    def __init__(self):
        self.cache_dir = config.assets_dir / "cache" / "concepts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": "CoolShortsBot/2.0 (https://myshortsapp.org; developer@myshortsapp.org)",
            "Referer": "https://commons.wikimedia.org/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        }

    def fetch(self, concept_query: str) -> Path:
        """Fetch image for any arbitrary concept string. Uses disk cache if present."""
        clean_name = concept_query.strip()
        file_hash = hashlib.md5(clean_name.lower().encode("utf-8")).hexdigest()[:12]
        cached_file = self.cache_dir / f"concept_{file_hash}.png"

        if cached_file.exists() and cached_file.stat().st_size > 4000:
            return cached_file

        print(f"[ConceptFetcher] Sourcing encyclopedic image for: '{clean_name}'...")

        # 1. Tier 1: Wikipedia Canonical Article Image
        try:
            url = self._from_wikipedia(clean_name)
            if url and self._download(url, cached_file, min_dim=220):
                print(f"[ConceptFetcher] Saved Wikipedia image -> {cached_file.name}")
                return cached_file
        except Exception as e:
            print(f"[ConceptFetcher] Wikipedia Tier 1 notice: {e}")

        # 2. Tier 2: Wikimedia Commons Media Search
        try:
            url = self._from_wikimedia_commons(clean_name)
            if url and self._download(url, cached_file, min_dim=220):
                print(f"[ConceptFetcher] Saved Wikimedia Commons image -> {cached_file.name}")
                return cached_file
        except Exception as e:
            print(f"[ConceptFetcher] Wikimedia Tier 2 notice: {e}")

        # 3. Tier 3: DuckDuckGo Web Search Fallback
        try:
            url = self._from_duckduckgo(clean_name)
            if url and self._download(url, cached_file, min_dim=200):
                print(f"[ConceptFetcher] Saved DuckDuckGo image -> {cached_file.name}")
                return cached_file
        except Exception as e:
            print(f"[ConceptFetcher] DuckDuckGo Tier 3 notice: {e}")

        # 4. Tier 4: Procedural Graphic Safety Fallback
        print(f"[ConceptFetcher] Generating procedural concept graphic -> {cached_file.name}")
        self._generate_procedural_fallback(clean_name, cached_file)
        return cached_file

    def _from_wikipedia(self, query: str) -> Optional[str]:
        """Queries Wikipedia REST API for canonical article high-res original/thumb."""
        clean_title = query.replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_title)}"
        try:
            r = requests.get(url, headers=self.headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                orig = data.get("originalimage", {}).get("source")
                if orig:
                    return orig
                thumb = data.get("thumbnail", {}).get("source")
                if thumb:
                    return re.sub(r"/\d+px-", "/1000px-", thumb)
            elif r.status_code == 404:
                # Search Wikipedia to resolve the canonical article title
                resolved_title = self._resolve_wikipedia_title(query)
                if resolved_title and resolved_title.lower() != clean_title.lower():
                    clean_res = resolved_title.replace(" ", "_")
                    sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_res)}"
                    r2 = requests.get(sum_url, headers=self.headers, timeout=6)
                    if r2.status_code == 200:
                        d2 = r2.json()
                        orig2 = d2.get("originalimage", {}).get("source")
                        if orig2:
                            return orig2
                        thumb2 = d2.get("thumbnail", {}).get("source")
                        if thumb2:
                            return re.sub(r"/\d+px-", "/1000px-", thumb2)
        except Exception:
            pass
        return None

    def _resolve_wikipedia_title(self, query: str) -> Optional[str]:
        """Search Wikipedia API to resolve a plain query into a canonical article title."""
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": "",
            "format": "json",
            "srlimit": 1,
        }
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=5)
            if r.status_code == 200:
                items = r.json().get("query", {}).get("search", [])
                if items and items[0].get("title"):
                    return items[0]["title"]
        except Exception:
            pass
        return None

    def _from_wikimedia_commons(self, query: str) -> Optional[str]:
        """Searches 105M Wikimedia Commons educational & hardware media."""
        clean_q = re.sub(r"[_\(\)]", " ", query).strip()
        url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,  # File namespace
            "gsrsearch": f"{clean_q} filetype:bitmap",
            "gsrlimit": 4,
            "prop": "imageinfo",
            "iiprop": "url|size",
        }
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=6)
            if r.status_code == 200:
                pages = r.json().get("query", {}).get("pages", {})
                for _, info in pages.items():
                    imgs = info.get("imageinfo", [])
                    if imgs and imgs[0].get("url"):
                        u = imgs[0]["url"]
                        w = imgs[0].get("width", 0)
                        h = imgs[0].get("height", 0)
                        if (w >= 300 or h >= 300) and not u.lower().endswith((".svg", ".tif", ".webm", ".ogv")):
                            return u
        except Exception:
            pass
        return None

    def _from_duckduckgo(self, query: str) -> Optional[str]:
        """Searches DuckDuckGo for high-resolution photo."""
        clean_q = re.sub(r"[_\(\)]", " ", query).strip()
        search_terms = f"{clean_q} high quality photo"

        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                res = list(ddgs.images(keywords=search_terms, max_results=3))
                for r in res:
                    u = r.get("image")
                    if u and u.startswith("http"):
                        return u
        except Exception:
            pass

        try:
            from duckduckgo_search import DDGS as OldDDGS
            with OldDDGS() as ddgs:
                res = list(ddgs.images(keywords=search_terms, max_results=3))
                for r in res:
                    u = r.get("image")
                    if u and u.startswith("http"):
                        return u
        except Exception:
            pass

        return None

    def _download(self, url: str, target_path: Path, min_dim: int = 150) -> bool:
        """Download raw image, validate size, convert to RGBA PNG and save."""
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200 and len(r.content) > 3000:
                img = Image.open(BytesIO(r.content))
                if img.width < min_dim and img.height < min_dim:
                    return False
                img = img.convert("RGBA")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(str(target_path), "PNG")
                return True
        except Exception:
            pass
        return False

    def _generate_procedural_fallback(self, label: str, output_path: Path) -> Path:
        """Procedural dark tech card placeholder."""
        img = Image.new("RGBA", (720, 520), (14, 18, 27, 255))
        draw = ImageDraw.Draw(img)

        # Tech grid
        for x in range(0, 720, 40):
            draw.line([(x, 0), (x, 520)], fill=(28, 38, 56, 120), width=1)
        for y in range(0, 520, 40):
            draw.line([(0, y), (720, y)], fill=(28, 38, 56, 120), width=1)

        draw.rounded_rectangle([120, 140, 600, 380], radius=18, fill=(20, 26, 40, 230), outline=(56, 189, 248, 200), width=2)
        font_large = ImageFont.load_default()
        clean_text = label.replace("_", " ").title()
        draw.text((360, 230), clean_text, font=font_large, fill=(240, 249, 255, 255), anchor="mm")
        draw.text((360, 280), "ENCYCLOPEDIC CONCEPT", font=font_large, fill=(56, 189, 248, 220), anchor="mm")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), "PNG")
        return output_path
