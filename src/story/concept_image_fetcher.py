"""Multi-Source Encyclopedic Image Engine for Mode 2 Shorts.
Sources:
1. Wikipedia REST API & Canonical Article Hero Image (100% authentic, curated canonical photos)
2. Wikimedia Commons Deep Search (105M+ public domain educational & hardware media)
3. DuckDuckGo Images (web real-stock fallback)
4. Procedural fallback (offline safety guard)
"""

import os
import re
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests
from PIL import Image, ImageDraw, ImageFont

from ..config import config


class ConceptImageFetcher:
    """Fetches exact-match, high-resolution encyclopedic images for any concept or metaphor."""

    def __init__(self):
        self.cache_dir = config.temp_dir / "concept_images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": "CoolShortsBot/1.0 (https://myshortsapp.org; developer@myshortsapp.org)",
            "Referer": "https://commons.wikimedia.org/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        }

    def fetch_concept(self, concept_name: str, output_path: Path) -> Path:
        """Cascade: Wikipedia Summary -> Wikimedia Commons -> DuckDuckGo -> Procedural Fallback."""
        if output_path.exists() and output_path.stat().st_size > 4000:
            return output_path

        clean_concept = concept_name.strip()
        print(f"[ConceptImageFetcher] Sourcing encyclopedic image for: '{clean_concept}'...")

        # 1. Tier 1: Wikipedia Canonical Hero Image
        try:
            wiki_url = self._get_wikipedia_hero_image(clean_concept)
            if wiki_url and self._download_and_save(wiki_url, output_path, min_dim=250):
                print(f"[ConceptImageFetcher] Saved Wikipedia canonical image -> {output_path.name}")
                return output_path
        except Exception as e:
            print(f"[ConceptImageFetcher] Tier 1 notice: {e}")

        # 2. Tier 2: Wikimedia Commons Deep Search
        try:
            commons_url = self._search_wikimedia_commons(clean_concept)
            if commons_url and self._download_and_save(commons_url, output_path, min_dim=250):
                print(f"[ConceptImageFetcher] Saved Wikimedia Commons image -> {output_path.name}")
                return output_path
        except Exception as e:
            print(f"[ConceptImageFetcher] Tier 2 notice: {e}")

        # 3. Tier 3: DuckDuckGo Fallback
        try:
            ddg_url = self._search_duckduckgo(clean_concept)
            if ddg_url and self._download_and_save(ddg_url, output_path, min_dim=200):
                print(f"[ConceptImageFetcher] Saved DuckDuckGo image -> {output_path.name}")
                return output_path
        except Exception as e:
            print(f"[ConceptImageFetcher] Tier 3 notice: {e}")

        # 4. Tier 4: Procedural Graphic Safety Fallback
        print(f"[ConceptImageFetcher] Using procedural concept graphic fallback -> {output_path.name}")
        self._generate_procedural_fallback(clean_concept, output_path)
        return output_path

    def _get_wikipedia_hero_image(self, title: str) -> Optional[str]:
        """Queries Wikipedia REST API for the canonical high-res article image."""
        clean_title = title.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_title)}"

        try:
            r = requests.get(url, headers=self.headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                # Prefer full original image
                orig = data.get("originalimage", {}).get("source")
                if orig:
                    return orig
                thumb = data.get("thumbnail", {}).get("source")
                if thumb:
                    # Upgrade thumbnail size to 1000px if possible
                    high_res = re.sub(r"/\d+px-", "/1000px-", thumb)
                    return high_res
            elif r.status_code == 404:
                # If exact title not found, search Wikipedia to resolve canonical article title
                resolved_title = self._resolve_wikipedia_title(title)
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
        except Exception as e:
            print(f"[ConceptImageFetcher] Wikipedia REST query notice: {e}")
        return None

    def _resolve_wikipedia_title(self, query: str) -> Optional[str]:
        """Search Wikipedia API to resolve a plain query into the canonical page title."""
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

    def _search_wikimedia_commons(self, query: str) -> Optional[str]:
        """Searches Wikimedia Commons educational & hardware media (105M+ files)."""
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
        except Exception as e:
            print(f"[ConceptImageFetcher] Wikimedia Commons query notice: {e}")
        return None

    def _search_duckduckgo(self, query: str) -> Optional[str]:
        """Searches DuckDuckGo for high-resolution transparent PNG or authentic photo."""
        clean_q = re.sub(r"[_\(\)]", " ", query).strip()
        search_terms = f"{clean_q} high resolution photo"

        # Try ddgs
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.images(keywords=search_terms, max_results=3))
                for res in results:
                    u = res.get("image")
                    if u and u.startswith("http"):
                        return u
        except Exception:
            pass

        # Try duckduckgo_search
        try:
            from duckduckgo_search import DDGS as OldDDGS
            with OldDDGS() as ddgs:
                results = list(ddgs.images(keywords=search_terms, max_results=3))
                for res in results:
                    u = res.get("image")
                    if u and u.startswith("http"):
                        return u
        except Exception as e:
            print(f"[ConceptImageFetcher] DuckDuckGo search notice: {e}")

        return None

    def _download_and_save(self, url: str, output_path: Path, min_dim: int = 150) -> bool:
        """Download raw image bytes, validate dimensions, convert to RGBA PNG and save."""
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200 and len(r.content) > 3000:
                img = Image.open(BytesIO(r.content))
                # Validate minimum size to avoid tiny icon thumbnails
                if img.width < min_dim and img.height < min_dim:
                    return False
                img = img.convert("RGBA")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(str(output_path), "PNG")
                return True
        except Exception as e:
            print(f"[ConceptImageFetcher] Download notice for {url[:50]}: {e}")
        return False

    def _generate_procedural_fallback(self, label: str, output_path: Path) -> Path:
        """Procedural high-tech concept placeholder card if completely offline."""
        img = Image.new("RGBA", (720, 520), (14, 18, 27, 255))
        draw = ImageDraw.Draw(img)

        # Subtle dark tech grid
        for x in range(0, 720, 40):
            draw.line([(x, 0), (x, 520)], fill=(28, 38, 56, 120), width=1)
        for y in range(0, 520, 40):
            draw.line([(0, y), (720, y)], fill=(28, 38, 56, 120), width=1)

        # Center highlight box
        draw.rounded_rectangle([120, 140, 600, 380], radius=18, fill=(20, 26, 40, 230), outline=(56, 189, 248, 200), width=2)

        font_large = ImageFont.load_default()
        clean_text = label.replace("_", " ").title()
        draw.text((360, 230), clean_text, font=font_large, fill=(240, 249, 255, 255), anchor="mm")
        draw.text((360, 280), "ENCYCLOPEDIC CONCEPT", font=font_large, fill=(56, 189, 248, 220), anchor="mm")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), "PNG")
        return output_path
