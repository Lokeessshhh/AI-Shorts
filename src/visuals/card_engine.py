"""Universal Card Synthesizer Engine for Short-Form Video Production.
Transforms any concept image into an enlarged, borderless, label-free floating visual:
- Enlarged container: 900x620 (prominent, high visual retention)
- Borderless: Zero artificial outlines or boundary lines
- Label-free: Clean photography without distracting pill badges
- Rounded corners: Smooth radius (R=32px)
- Realistic soft drop shadow (blur 24px, offset Y=+12px, alpha 75%)
- Transparent RGBA PNG output
"""

import io
from pathlib import Path
from typing import Union, Optional
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


class VisualCardEngine:
    """Universal card renderer that formats raw images into enlarged, borderless floating visual cards."""

    def __init__(self):
        pass

    def render_card(
        self,
        image_input: Union[Path, str, bytes, Image.Image],
        badge_text: str = "",  # Kept for signature compatibility, unused per user design
        output_png: Optional[Path] = None,
        card_width: int = 900,
        card_height: int = 620,
        corner_radius: int = 32,
        shadow_blur: int = 24,
        shadow_offset_y: int = 12,
        shadow_alpha: int = 190,
    ) -> Path:
        """
        Synthesize an enlarged, borderless, label-free floating visual with rounded corners
        and a realistic soft drop shadow.
        """
        if output_png is None:
            raise ValueError("output_png path must be specified")

        output_png.parent.mkdir(parents=True, exist_ok=True)

        # 1. Load source image with resilience against corrupted or truncated downloads
        try:
            if isinstance(image_input, Image.Image):
                src_img = image_input.convert("RGBA")
            elif isinstance(image_input, (bytes, bytearray)):
                src_img = Image.open(io.BytesIO(image_input)).convert("RGBA")
            else:
                src_img = Image.open(str(image_input)).convert("RGBA")
        except Exception:
            src_img = Image.new("RGBA", (card_width, card_height), (242, 239, 233, 255))
            draw_fb = ImageDraw.Draw(src_img)
            draw_fb.rounded_rectangle([20, 20, card_width - 20, card_height - 20], radius=16, fill=(235, 230, 222, 255))

        # 2. Aspect-fit/crop image into enlarged card canvas
        cropped_img = ImageOps.fit(
            src_img,
            (card_width, card_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

        # 3. Create smooth rounded corner mask
        mask = Image.new("L", (card_width, card_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            [0, 0, card_width, card_height],
            radius=corner_radius,
            fill=255,
        )

        # Apply mask: clean, borderless, label-free surface
        card_surface = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        card_surface.paste(cropped_img, (0, 0), mask=mask)

        # 4. Generate realistic gaussian soft drop shadow
        canvas_w = card_width + (shadow_blur * 2)
        canvas_h = card_height + (shadow_blur * 2) + abs(shadow_offset_y)

        shadow_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        shadow_mask = Image.new("L", (canvas_w, canvas_h), 0)
        smask_draw = ImageDraw.Draw(shadow_mask)

        # Draw shadow rounded rectangle
        s_x1 = shadow_blur
        s_y1 = shadow_blur + shadow_offset_y
        s_x2 = s_x1 + card_width
        s_y2 = s_y1 + card_height
        smask_draw.rounded_rectangle(
            [s_x1, s_y1, s_x2, s_y2],
            radius=corner_radius,
            fill=shadow_alpha,
        )

        blurred_shadow = shadow_mask.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        shadow_color = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 255))
        shadow_canvas.paste(shadow_color, (0, 0), mask=blurred_shadow)

        # 5. Paste styled card on top of the drop shadow
        card_x = shadow_blur
        card_y = shadow_blur
        shadow_canvas.paste(card_surface, (card_x, card_y), mask=card_surface)

        # 6. Save output PNG
        shadow_canvas.save(str(output_png), "PNG")
        return output_png
