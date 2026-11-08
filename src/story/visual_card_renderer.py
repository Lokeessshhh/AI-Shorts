"""Mode 2 Visual Pop-up Card Renderer.
Generates 3D Pixar/Metaphor visual cards for the top-middle canvas:
- 720x520 pixel container
- Rounded corners (radius 28px) with 4px cyan / frost-white glow border
- Sleek top pill badge for concept label
- Soft realistic drop shadow (blur radius 20px, offset Y=+12px, alpha 70%)
- Clean transparent RGBA output PNG
"""

import io
from pathlib import Path
from typing import Union, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


class VisualCardRenderer:
    """Renders contextual floating visual metaphor cards with drop shadows and badges."""

    def __init__(self):
        # Color palette
        self.BORDER_COLOR = (56, 189, 248, 240)    # Cyan / Frost White glow
        self.INNER_BORDER = (255, 255, 255, 160)   # White highlight
        self.PILL_BG = (15, 23, 42, 230)           # Dark slate translucent
        self.TEXT_COLOR = (248, 250, 252, 255)     # Bright white
        self.ACCENT_COLOR = (56, 189, 248, 255)    # Cyan accent

        self.font_badge = self._load_font(24)

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        paths = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in paths:
            if Path(p).exists():
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def render_card(
        self,
        image_input: Union[Path, str, bytes, Image.Image],
        badge_text: str,
        output_png: Path,
        card_width: int = 720,
        card_height: int = 520,
        corner_radius: int = 28,
    ) -> Path:
        """
        Synthesize a 720x520 floating visual card with rounded corners,
        top concept pill badge, and realistic soft drop shadow.
        """
        output_png.parent.mkdir(parents=True, exist_ok=True)

        # 1. Load Source Image
        if isinstance(image_input, Image.Image):
            src_img = image_input.convert("RGBA")
        elif isinstance(image_input, (bytes, bytearray)):
            src_img = Image.open(io.BytesIO(image_input)).convert("RGBA")
        else:
            src_img = Image.open(str(image_input)).convert("RGBA")

        # 2. Resize and Center-Crop to (card_width, card_height)
        cropped_img = ImageOps.fit(
            src_img,
            (card_width, card_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

        # 3. Create Rounded Corner Mask for the Card
        mask = Image.new("L", (card_width, card_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [0, 0, card_width, card_height],
            radius=corner_radius,
            fill=255,
        )

        # Apply rounded corner mask to the cropped image
        card_surface = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        card_surface.paste(cropped_img, (0, 0), mask=mask)

        # 4. Draw Elegant Glow Border on the Card
        border_draw = ImageDraw.Draw(card_surface)
        border_draw.rounded_rectangle(
            [2, 2, card_width - 2, card_height - 2],
            radius=corner_radius,
            outline=self.BORDER_COLOR,
            width=4,
        )
        border_draw.rounded_rectangle(
            [5, 5, card_width - 5, card_height - 5],
            radius=corner_radius - 2,
            outline=self.INNER_BORDER,
            width=1,
        )

        # 5. Render Top Concept Pill Badge
        # Calculate badge pill width based on text
        clean_text = f"✦ {badge_text.upper()}"
        bbox = border_draw.textbbox((0, 0), clean_text, font=self.font_badge)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        pill_w = max(220, text_w + 50)
        pill_h = 48
        pill_x = (card_width - pill_w) // 2
        pill_y = 18

        # Draw Pill Shadow & Box
        pill_canvas = Image.new("RGBA", (pill_w + 10, pill_h + 10), (0, 0, 0, 0))
        pill_draw = ImageDraw.Draw(pill_canvas)
        pill_draw.rounded_rectangle(
            [2, 3, pill_w + 2, pill_h + 3],
            radius=24,
            fill=(0, 0, 0, 160),
        )
        pill_draw.rounded_rectangle(
            [0, 0, pill_w, pill_h],
            radius=24,
            fill=self.PILL_BG,
            outline=self.ACCENT_COLOR,
            width=2,
        )
        # Center text inside pill
        tx = (pill_w - text_w) // 2
        ty = (pill_h - text_h) // 2 - 2
        pill_draw.text((tx, ty), clean_text, font=self.font_badge, fill=self.TEXT_COLOR)

        card_surface.paste(pill_canvas, (pill_x - 1, pill_y - 1), mask=pill_canvas)

        # 6. Generate Realistic Soft Drop Shadow on a Canvas
        # Target canvas size with padding for shadow
        pad_x = 50
        pad_y = 60
        canvas_w = card_width + (pad_x * 2)
        canvas_h = card_height + (pad_y * 2)

        shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)

        # Shadow rectangle offset Y=+12px, blur radius 20px, dark alpha 70% (~180/255)
        offset_y = 12
        shadow_box = [
            pad_x + 4,
            pad_y + offset_y,
            pad_x + card_width - 4,
            pad_y + card_height + offset_y,
        ]
        shadow_draw.rounded_rectangle(
            shadow_box,
            radius=corner_radius + 4,
            fill=(0, 0, 0, 180),
        )
        shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(radius=20))

        # Composite Card Surface over Shadow
        final_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        final_canvas.paste(shadow_blurred, (0, 0), mask=shadow_blurred)
        final_canvas.paste(card_surface, (pad_x, pad_y), mask=card_surface)

        final_canvas.save(output_png, "PNG")
        print(f"[VisualCard] Synthesized 3D visual card ({card_width}x{card_height}) -> {output_png.name}")
        return output_png
