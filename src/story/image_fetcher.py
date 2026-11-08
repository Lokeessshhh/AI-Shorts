"""Mode 2 Concept Visual Image Fetcher.
Fetches high-quality 3D isometric Pixar-style illustration images for visual cards:
1. Pollinations AI Flux endpoint (free, fast, high aesthetic)
2. Pexels API Fallback
3. High-quality procedural graphic fallback
"""

import urllib.parse
from pathlib import Path
from typing import Optional
import requests
from PIL import Image, ImageDraw, ImageFont

from ..config import config


class ConceptImageFetcher:
    """Fetches or generates 3D concept metaphor visuals."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def fetch_concept_image(self, prompt: str, output_path: Path) -> Path:
        """
        Fetch concept image using Pollinations AI Flux model,
        falling back to Pexels or procedural generator if unreachable.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        encoded_prompt = urllib.parse.quote(prompt.strip())

        endpoints = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=512&model=flux&nologo=true",
            f"https://gen.pollinations.ai/image/{encoded_prompt}?width=768&height=512&model=flux&nologo=true",
        ]

        print(f"[ConceptImage] Generating concept visual: '{prompt[:65]}...'")

        # 1. Try Pollinations AI Flux
        for url in endpoints:
            try:
                res = self.session.get(url, timeout=20)
                if res.status_code == 200 and len(res.content) > 5000:
                    with open(output_path, "wb") as f:
                        f.write(res.content)
                    print(f"[ConceptImage] Successfully saved AI Flux image -> {output_path.name}")
                    return output_path
            except Exception as e:
                print(f"[ConceptImage] Endpoint notice ({url[:35]}...): {e}")

        # 2. Try Pexels API fallback if key available
        if config.pexels_api_key:
            try:
                from ..visuals.pexels import PexelsClient
                client = PexelsClient()
                # Clean prompt for stock query
                clean_q = prompt.replace("3D isometric Pixar style illustration of", "").replace("clean studio lighting, dark minimalist background, 8k", "").strip()
                photos = client.search_photos(clean_q, orientation="landscape", per_page=1)
                if photos:
                    client.download_photo(photos[0], output_path)
                    print(f"[ConceptImage] Sourced fallback image from Pexels -> {output_path.name}")
                    return output_path
            except Exception as e:
                print(f"[ConceptImage] Pexels fallback skipped: {e}")

        # 3. Procedural Fallback Graphic
        print(f"[ConceptImage] Generating procedural concept graphic fallback -> {output_path.name}")
        self._generate_procedural_fallback(prompt, output_path)
        return output_path

    def _generate_procedural_fallback(self, prompt: str, output_path: Path, width: int = 768, height: int = 512) -> Path:
        """Generate a sleek cyber-gradient card with tech icons if network is offline."""
        canvas = Image.new("RGBA", (width, height), (15, 23, 42, 255))
        draw = ImageDraw.Draw(canvas)

        # Subtle dark blue/cyan gradient effect
        for y in range(height):
            ratio = y / height
            r = int(15 * (1 - ratio) + 8 * ratio)
            g = int(23 * (1 - ratio) + 47 * ratio)
            b = int(42 * (1 - ratio) + 73 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # Cyber grid
        for x in range(0, width, 48):
            draw.line([(x, 0), (x, height)], fill=(56, 189, 248, 25), width=1)
        for y in range(0, height, 48):
            draw.line([(0, y), (width, y)], fill=(56, 189, 248, 25), width=1)

        # Center glowing icon circle
        cx, cy = width // 2, height // 2 - 20
        draw.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=(30, 41, 59, 230), outline=(56, 189, 248, 220), width=4)
        draw.ellipse([cx - 55, cy - 55, cx + 55, cy + 55], outline=(217, 119, 86, 180), width=2)

        # Text label
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
            font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
        except Exception:
            font = ImageFont.load_default()
            font_sub = font

        # Summary text from prompt
        summary = prompt.replace("3D isometric Pixar style illustration of", "").replace("clean studio lighting, dark minimalist background, 8k", "").strip()[:40]
        bbox = draw.textbbox((0, 0), summary, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((width - tw) // 2, cy + 95), summary, font=font, fill=(248, 250, 252, 255))

        canvas.save(output_path, "PNG")
        return output_path
