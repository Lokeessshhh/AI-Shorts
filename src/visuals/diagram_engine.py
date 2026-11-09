"""Bright, Clean Editorial Infographic & Procedural Visual Engine.
Renders high-retention, publication-ready visual explanations on 1080x1920 (9:16) canvases.

Supports arbitrary visual topologies without rigid card/flowchart limitations:
- Radial cycles & feedback loops (Perverse Incentive Traps, Predator-Prey, Cyclical Loops)
- Chronological timelines & milestone chains (Historical Evolutions, Investigation Sequences)
- Mind maps & hub-and-spoke relationship models (Central Phenomena + Radiating Drivers)
- Branching decision & causal trees (Choices -> Split Consequences)
- Layered systemic & architectural stacks (Tiered Explanations)
- Quantitative multi-bar data visualizations (Comparative Metrics)
- Side-by-side contrasting matrices (Expectation vs Reality)
- Causal Domino chains (Multi-step Cause-and-Effect Sequences)
- Universal declarative node/edge graphs

Design Principles:
- Bright editorial aesthetic: Warm cream/off-white (#FBF9F5) paper canvas, subtle architectural grid.
- High-contrast typography: Mobile-first 9:16 safe area (Y: 340 to 1420), large readable text.
- Zero black canvases, zero dark grids, zero dim void backgrounds.
- Zero hardcoding: fully schema-driven by DynamicVisualSpec.
"""

import math
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from ..config import config
from .card_engine import VisualCardEngine
from ..llm.prompts import DynamicVisualSpec, VisualNode, VisualEdge


class DiagramEngine:
    """Universal Dynamic Visual & Infographic Engine for Bright Editorial 1080x1920 video."""

    BRIGHT_ACCENTS = {
        "blue": {"primary": (29, 100, 242), "glow": (40, 120, 255, 35), "sub": (75, 85, 105), "badge_bg": (230, 240, 255), "card_border": (210, 222, 240)},
        "crimson": {"primary": (217, 37, 52), "glow": (240, 60, 75, 35), "sub": (85, 75, 80), "badge_bg": (255, 235, 238), "card_border": (245, 210, 215)},
        "emerald": {"primary": (13, 138, 78), "glow": (25, 175, 105, 35), "sub": (70, 85, 75), "badge_bg": (232, 250, 240), "card_border": (205, 235, 220)},
        "amber": {"primary": (217, 119, 6), "glow": (245, 145, 25, 35), "sub": (85, 80, 70), "badge_bg": (255, 244, 225), "card_border": (245, 225, 200)},
        "purple": {"primary": (124, 58, 237), "glow": (145, 80, 250, 35), "sub": (80, 75, 90), "badge_bg": (245, 238, 255), "card_border": (230, 215, 250)},
        "gold": {"primary": (195, 125, 10), "glow": (240, 160, 30, 35), "sub": (80, 80, 75), "badge_bg": (255, 246, 228), "card_border": (240, 228, 205)},
        "teal": {"primary": (13, 148, 136), "glow": (20, 185, 170, 35), "sub": (70, 85, 85), "badge_bg": (230, 250, 248), "card_border": (200, 235, 232)},
    }

    STATUS_COLORS = {
        "neutral": {"fill": (255, 255, 255, 250), "border": (220, 226, 235), "badge_bg": (241, 245, 249), "badge_text": (71, 85, 105)},
        "positive": {"fill": (255, 255, 255, 250), "border": (187, 247, 208), "badge_bg": (220, 252, 231), "badge_text": (22, 101, 52)},
        "negative": {"fill": (255, 255, 255, 250), "border": (254, 202, 202), "badge_bg": (254, 226, 226), "badge_text": (185, 28, 28)},
        "warning": {"fill": (255, 255, 255, 250), "border": (254, 215, 170), "badge_bg": (254, 237, 213), "badge_text": (194, 65, 12)},
        "accent": {"fill": (255, 255, 255, 250), "border": (191, 219, 254), "badge_bg": (224, 238, 255), "badge_text": (29, 78, 216)},
    }

    def __init__(self, card_engine: Optional[VisualCardEngine] = None):
        self.card_engine = card_engine or VisualCardEngine()
        self.fonts_dir = config.fonts_dir

    def _get_font(self, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        font_name = "Poppins-Bold.ttf" if bold else "Poppins-Regular.ttf"
        font_file = self.fonts_dir / font_name
        if font_file.exists():
            try:
                return ImageFont.truetype(str(font_file), size)
            except Exception:
                pass
        return ImageFont.load_default()

    def create_bright_editorial_background(
        self,
        width: int = 1080,
        height: int = 1920,
        accent: str = "blue",
    ) -> Image.Image:
        """Creates a bright, clean, premium editorial studio canvas."""
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        # 1. Base light editorial studio gradient
        base = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        draw_base = ImageDraw.Draw(base)
        for y in range(height):
            ratio = y / height
            r = int(251 - ratio * 10)
            g = int(250 - ratio * 7)
            b = int(247 - ratio * 3)
            draw_base.line([(0, y), (width, y)], fill=(r, g, b, 255))

        # 2. Subtle architectural grid overlay
        grid_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        grid_draw = ImageDraw.Draw(grid_overlay)
        grid_step = 72
        grid_color = (218, 223, 232, 65)

        for x in range(0, width, grid_step):
            grid_draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, grid_step):
            grid_draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Crosshairs at grid intersections
        for x in range(grid_step * 2, width - grid_step, grid_step * 3):
            for y in range(grid_step * 3, height - grid_step * 3, grid_step * 4):
                grid_draw.line([(x - 5, y), (x + 5, y)], fill=(185, 195, 210, 85), width=1)
                grid_draw.line([(x, y - 5), (x, y + 5)], fill=(185, 195, 210, 85), width=1)

        base = Image.alpha_composite(base, grid_overlay)

        # 3. Soft warm radial accent glow in upper-middle region
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        center_x = width // 2
        center_y = int(height * 0.44)
        glow_draw.ellipse(
            [center_x - 440, center_y - 340, center_x + 440, center_y + 340],
            fill=palette["glow"],
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=150))
        base = Image.alpha_composite(base, glow)

        # 4. Subtle perimeter border line
        border_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(border_overlay)
        b_draw.rounded_rectangle([36, 36, width - 36, height - 36], radius=24, outline=(210, 218, 230, 80), width=1)
        base = Image.alpha_composite(base, border_overlay)

        return base

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        headline: str,
        subheadline: Optional[str],
        accent: str = "blue",
        start_y: int = 340,
    ) -> int:
        """Renders standard editorial header and returns the bottom Y coordinate."""
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])
        font_head = self._get_font(42, bold=True)
        font_sub = self._get_font(23, bold=False)

        clean_head = (headline or "KEY EXPLANATION").upper()
        draw.text((540, start_y), clean_head, fill=(18, 24, 38), font=font_head, anchor="mm")

        if subheadline:
            draw.text((540, start_y + 44), subheadline, fill=palette["sub"], font=font_sub, anchor="mm")
            rule_y = start_y + 80
        else:
            rule_y = start_y + 55

        draw.line([(120, rule_y), (960, rule_y)], fill=(220, 226, 238), width=2)
        draw.line([(440, rule_y), (640, rule_y)], fill=palette["primary"], width=3)
        return rule_y + 25

    def _draw_takeaway(
        self,
        draw: ImageDraw.ImageDraw,
        takeaway: Optional[str],
        accent: str = "blue",
        y: int = 1380,
    ):
        """Renders prominent bottom takeaway banner."""
        if not takeaway:
            return
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])
        font_takeaway = self._get_font(21, bold=True)
        draw.rounded_rectangle([90, y, 990, y + 68], radius=16, fill=(255, 255, 255, 250), outline=palette["primary"], width=2)
        draw.rounded_rectangle([104, y + 14, 260, y + 54], radius=8, fill=palette["primary"])
        draw.text((182, y + 34), "KEY PAYOFF", fill=(255, 255, 255), font=self._get_font(18, bold=True), anchor="mm")
        draw.text((280, y + 34), takeaway[:55], fill=(20, 26, 38), font=font_takeaway, anchor="lm")

    def _draw_arrow(
        self,
        draw: ImageDraw.ImageDraw,
        start_xy: Tuple[float, float],
        end_xy: Tuple[float, float],
        color: Tuple[int, int, int] = (100, 116, 139),
        width: int = 3,
        arrow_size: int = 14,
    ):
        """Draws a directed connection line with a crisp arrowhead."""
        x1, y1 = start_xy
        x2, y2 = end_xy
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
        angle = math.atan2(y2 - y1, x2 - x1)
        p1 = (x2 - arrow_size * math.cos(angle - math.pi / 6), y2 - arrow_size * math.sin(angle - math.pi / 6))
        p2 = (x2 - arrow_size * math.cos(angle + math.pi / 6), y2 - arrow_size * math.sin(angle + math.pi / 6))
        draw.polygon([(x2, y2), p1, p2], fill=color)

    def _draw_multiline_centered(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        left: int,
        top: int,
        max_width: int,
        font: ImageFont.FreeTypeFont,
        fill: Tuple[int, int, int],
        line_height: int = 30,
        max_lines: int = 3,
    ):
        """Clean multiline word wrapper centered within bounding width."""
        words = text.split()
        lines = []
        cur_line = []
        for w in words:
            test_line = " ".join(cur_line + [w])
            bbox = font.getbbox(test_line)
            if (bbox[2] - bbox[0]) <= max_width:
                cur_line.append(w)
            else:
                if cur_line:
                    lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))

        for i, line in enumerate(lines[:max_lines]):
            draw.text((left + max_width // 2, top + (i * line_height)), line, fill=fill, font=font, anchor="mm")

    # -------------------------------------------------------------------------
    # DISPATCHER: Dynamic Dispatch based on LLM's Chosen Topology
    # -------------------------------------------------------------------------
    def render_from_spec(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Dynamically interprets and renders unconstrained visual specifications."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        v_format = (spec.visual_format or spec.layout_type or "auto").lower()
        l_type = (spec.layout_type or "auto").lower()

        # 1. Cyclical Feedback Loop / Radial Cycle
        if "radial" in l_type or "cycle" in v_format or "loop" in v_format or "feedback" in v_format:
            return self.render_radial_cycle(spec, output_path)

        # 2. Chronological Milestones / Timeline
        elif "timeline" in l_type or "timeline" in v_format or "milestone" in v_format or "history" in v_format:
            return self.render_timeline_milestones(spec, output_path)

        # 3. Mind Map / Central Hub & Spokes
        elif "mind" in l_type or "mind" in v_format or "hub" in v_format or "spoke" in v_format or "concept_map" in v_format:
            return self.render_mind_map(spec, output_path)

        # 4. Branching Tree / Decision Forks
        elif "branch" in l_type or "tree" in v_format or "decision" in v_format or "fork" in v_format:
            return self.render_branching_tree(spec, output_path)

        # 5. Layered Architecture / Hierarchical Stack
        elif "layer" in l_type or "layer" in v_format or "stack" in v_format or "tier" in v_format:
            return self.render_layered_stack(spec, output_path)

        # 6. Quantitative Data Visualization / Comparative Bars
        elif "stat" in l_type or "stat" in v_format or "bar" in v_format or "data" in v_format or "metric" in v_format:
            return self.render_data_bars(spec, output_path)

        # 7. Dual Comparison / Contrast Split
        elif "comparison" in l_type or "comparison" in v_format or "contrast" in v_format or "split" in v_format:
            return self.render_comparison_split(spec, output_path)

        # 8. Causal Domino Sequence / Process Flow
        elif "causal" in l_type or "chain" in v_format or "process" in v_format or "flow" in v_format:
            return self.render_causal_chain(spec, output_path)

        # Universal fallback: If custom nodes exist, render dynamically; else comparison split
        if spec.nodes and len(spec.nodes) >= 3:
            return self.render_radial_cycle(spec, output_path)
        return self.render_comparison_split(spec, output_path)

    # -------------------------------------------------------------------------
    # 1. RADIAL CYCLE & FEEDBACK LOOP
    # -------------------------------------------------------------------------
    def render_radial_cycle(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders circular feedback loops with directional loop arrows and central hub."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        # Convert steps to nodes if nodes list is empty
        nodes = spec.nodes
        if not nodes and spec.steps:
            nodes = [
                VisualNode(id=f"n{i}", label=step, badge=f"STAGE {i+1}", status="neutral")
                for i, step in enumerate(spec.steps[:4])
            ]
        if not nodes:
            nodes = [
                VisualNode(id="n1", label="Policy Catalyst", badge="CATALYST", status="neutral"),
                VisualNode(id="n2", label="Market Response", badge="INCENTIVE", status="warning"),
                VisualNode(id="n3", label="Unintended Loop", badge="EXPLOIT", status="negative"),
                VisualNode(id="n4", label="Worse Outcome", badge="PAYOFF", status="negative"),
            ]

        n_count = min(5, len(nodes))
        center_x = 540
        center_y = content_top + 460
        radius_x = 320
        radius_y = 280

        # Center Hub Badge
        hub_w, hub_h = 240, 100
        draw.rounded_rectangle(
            [center_x - hub_w // 2, center_y - hub_h // 2, center_x + hub_w // 2, center_y + hub_h // 2],
            radius=20,
            fill=(255, 255, 255, 250),
            outline=palette["primary"],
            width=2,
        )
        draw.text((center_x, center_y - 14), "FEEDBACK LOOP", fill=palette["primary"], font=self._get_font(18, bold=True), anchor="mm")
        draw.text((center_x, center_y + 16), "SELF-REINFORCING", fill=(71, 85, 105), font=self._get_font(16, bold=False), anchor="mm")

        # Calculate node coordinates around ellipse
        card_w = 320
        card_h = 130
        node_coords = []
        for i in range(n_count):
            angle = -math.pi / 2 + i * (2 * math.pi / n_count)
            nx = center_x + radius_x * math.cos(angle)
            ny = center_y + radius_y * math.sin(angle)
            node_coords.append((nx, ny, nodes[i]))

        # Draw connecting curved arrows between nodes
        for i in range(n_count):
            x1, y1, _ = node_coords[i]
            next_idx = (i + 1) % n_count
            x2, y2, _ = node_coords[next_idx]

            # Vector towards next node
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                sx = x1 + (dx / dist) * (card_w // 2 + 10)
                sy = y1 + (dy / dist) * (card_h // 2 + 10)
                ex = x2 - (dx / dist) * (card_w // 2 + 15)
                ey = y2 - (dy / dist) * (card_h // 2 + 15)
                self._draw_arrow(draw, (sx, sy), (ex, ey), color=palette["primary"], width=3, arrow_size=15)

        # Draw node cards on top
        font_node_title = self._get_font(21, bold=True)
        font_badge = self._get_font(15, bold=True)
        font_detail = self._get_font(16, bold=False)

        for nx, ny, node in node_coords:
            left = int(nx - card_w // 2)
            top = int(ny - card_h // 2)
            st_color = self.STATUS_COLORS.get(node.status or "neutral", self.STATUS_COLORS["neutral"])

            # Card container with soft shadow
            draw.rounded_rectangle([left, top, left + card_w, top + card_h], radius=18, fill=st_color["fill"], outline=st_color["border"], width=2)

            # Badge pill
            badge_txt = (node.badge or f"NODE").upper()
            badge_w = min(140, len(badge_txt) * 11 + 20)
            draw.rounded_rectangle([left + 16, top + 14, left + 16 + badge_w, top + 42], radius=8, fill=st_color["badge_bg"])
            draw.text((left + 16 + badge_w // 2, top + 28), badge_txt, fill=st_color["badge_text"], font=font_badge, anchor="mm")

            # Value callout if provided
            if node.value:
                draw.text((left + card_w - 20, top + 28), node.value, fill=palette["primary"], font=self._get_font(18, bold=True), anchor="rm")

            # Title & detail
            draw.text((left + card_w // 2, top + 64), node.label[:26], fill=(18, 24, 38), font=font_node_title, anchor="mm")
            if node.detail:
                draw.text((left + card_w // 2, top + 98), node.detail[:34], fill=(100, 116, 139), font=font_detail, anchor="mm")

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 2. CHRONOLOGICAL TIMELINE & MILESTONE CHAIN
    # -------------------------------------------------------------------------
    def render_timeline_milestones(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders vertical chronological milestone chain with dates and callouts."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        nodes = spec.nodes or [
            VisualNode(id="t1", label="Initial Catalyst", badge="PHASE 1", value="1953", detail="The triggering incident occurs."),
            VisualNode(id="t2", label="Baffling Anomaly", badge="PHASE 2", value="INVESTIGATION", detail="Engineers confront unexplained failure."),
            VisualNode(id="t3", label="Root Discovery", badge="PHASE 3", value="BREAKTHROUGH", detail="Micro-tears reveal corner pressure physics."),
            VisualNode(id="t4", label="Permanent Standard", badge="PAYOFF", value="MODERN ERA", detail="Every commercial aircraft adopts rounded windows."),
        ]
        n_count = min(4, len(nodes))

        # Vertical spine at X = 200
        spine_x = 200
        spine_top = content_top + 40
        spine_bottom = spine_top + (n_count - 1) * 220 + 80
        draw.line([(spine_x, spine_top), (spine_x, spine_bottom)], fill=(203, 213, 225), width=4)

        card_w = 690
        card_h = 160

        for i, node in enumerate(nodes[:n_count]):
            node_y = spine_top + i * 220

            # Spine marker circle
            draw.ellipse([spine_x - 18, node_y + 40 - 18, spine_x + 18, node_y + 40 + 18], fill=palette["primary"], outline=(255, 255, 255), width=3)

            # Milestone date pill on spine
            val_txt = node.value or f"0{i+1}"
            draw.text((spine_x - 30, node_y + 40), val_txt, fill=palette["primary"], font=self._get_font(20, bold=True), anchor="rm")

            # Milestone content card on right
            cx = spine_x + 50
            cy = node_y
            st = self.STATUS_COLORS.get(node.status or "neutral", self.STATUS_COLORS["neutral"])
            draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=18, fill=st["fill"], outline=st["border"], width=2)

            # Badge pill
            badge_txt = (node.badge or f"STAGE {i+1}").upper()
            draw.rounded_rectangle([cx + 20, cy + 18, cx + 180, cy + 50], radius=8, fill=st["badge_bg"])
            draw.text((cx + 100, cy + 34), badge_txt, fill=st["badge_text"], font=self._get_font(16, bold=True), anchor="mm")

            # Title & detail
            draw.text((cx + 20, cy + 80), node.label[:36], fill=(18, 24, 38), font=self._get_font(24, bold=True), anchor="lm")
            if node.detail:
                draw.text((cx + 20, cy + 120), node.detail[:52], fill=(100, 116, 139), font=self._get_font(18, bold=False), anchor="lm")

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 3. MIND MAP / CENTRAL HUB & RADIATING SPOKES
    # -------------------------------------------------------------------------
    def render_mind_map(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders central concept hub with radiating connected spoke nodes."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        nodes = spec.nodes or [
            VisualNode(id="s1", label="Cognitive Load", detail="Brain avoids complex decision"),
            VisualNode(id="s2", label="Default Bias", detail="Path of least resistance wins"),
            VisualNode(id="s3", label="Social Proof", detail="Conforming to crowd behavior"),
            VisualNode(id="s4", label="Choice Fatigue", detail="Too many options paralyze action"),
        ]

        center_x = 540
        center_y = content_top + 460

        # Central Hub Card
        hub_w = 420
        hub_h = 160
        draw.rounded_rectangle(
            [center_x - hub_w // 2, center_y - hub_h // 2, center_x + hub_w // 2, center_y + hub_h // 2],
            radius=24,
            fill=(255, 255, 255, 250),
            outline=palette["primary"],
            width=3,
        )
        draw.rounded_rectangle([center_x - 90, center_y - hub_h // 2 + 16, center_x + 90, center_y - hub_h // 2 + 48], radius=8, fill=palette["badge_bg"])
        draw.text((center_x, center_y - hub_h // 2 + 32), "CORE MECHANISM", fill=palette["primary"], font=self._get_font(16, bold=True), anchor="mm")
        draw.text((center_x, center_y + 12), (spec.headline or "CENTRAL CONCEPT")[:28], fill=(18, 24, 38), font=self._get_font(26, bold=True), anchor="mm")

        # Satellite spoke cards (4 directions)
        spoke_w = 380
        spoke_h = 140
        spoke_positions = [
            (center_x, center_y - 320),  # Top
            (center_x, center_y + 320),  # Bottom
            (center_x - 290, center_y),  # Left
            (center_x + 290, center_y),  # Right
        ]

        for i, node in enumerate(nodes[:4]):
            sx, sy = spoke_positions[i]
            # Radiating connection line
            draw.line([(center_x, center_y), (sx, sy)], fill=palette["card_border"], width=3)

            # Spoke Card
            left = int(sx - spoke_w // 2)
            top = int(sy - spoke_h // 2)
            st = self.STATUS_COLORS.get(node.status or "neutral", self.STATUS_COLORS["neutral"])
            draw.rounded_rectangle([left, top, left + spoke_w, top + spoke_h], radius=18, fill=st["fill"], outline=st["border"], width=2)

            badge_txt = (node.badge or f"FACTOR {i+1}").upper()
            draw.text((left + 20, top + 34), badge_txt, fill=palette["primary"], font=self._get_font(15, bold=True), anchor="lm")
            draw.text((left + 20, top + 74), node.label[:26], fill=(18, 24, 38), font=self._get_font(22, bold=True), anchor="lm")
            if node.detail:
                draw.text((left + 20, top + 108), node.detail[:36], fill=(100, 116, 139), font=self._get_font(17, bold=False), anchor="lm")

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 4. BRANCHING TREE / DECISION FORKS
    # -------------------------------------------------------------------------
    def render_branching_tree(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders decision tree: Root Decision -> Diverging Paths -> Outcomes."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        # Root Node at top
        root_w = 560
        root_h = 130
        root_x = 540
        root_y = content_top + 80

        draw.rounded_rectangle(
            [root_x - root_w // 2, root_y, root_x + root_w // 2, root_y + root_h],
            radius=20,
            fill=(255, 255, 255, 250),
            outline=palette["primary"],
            width=3,
        )
        draw.text((root_x, root_y + 36), "INITIAL DECISION / POLICY", fill=palette["primary"], font=self._get_font(16, bold=True), anchor="mm")
        root_label = (spec.nodes[0].label if spec.nodes else "Cash Bounty for Dead Cobras")[:38]
        draw.text((root_x, root_y + 82), root_label, fill=(18, 24, 38), font=self._get_font(26, bold=True), anchor="mm")

        # Two branches splitting down
        fork_y = root_y + root_h + 80
        draw.line([(root_x, root_y + root_h), (root_x, fork_y)], fill=(148, 163, 184), width=3)
        draw.line([(280, fork_y), (800, fork_y)], fill=(148, 163, 184), width=3)
        draw.line([(280, fork_y), (280, fork_y + 60)], fill=(148, 163, 184), width=3)
        draw.line([(800, fork_y), (800, fork_y + 60)], fill=(148, 163, 184), width=3)

        # Branch Left Card: Intended Outcome
        l_x = 70
        l_top = fork_y + 60
        col_w = 440
        col_h = 420

        draw.rounded_rectangle([l_x, l_top, l_x + col_w, l_top + col_h], radius=20, fill=(255, 255, 255, 250), outline=(187, 247, 208), width=2)
        draw.rounded_rectangle([l_x + 24, l_top + 24, l_x + col_w - 24, l_top + 64], radius=10, fill=(220, 252, 231))
        draw.text((l_x + col_w // 2, l_top + 44), "INTENDED PATH", fill=(22, 101, 52), font=self._get_font(18, bold=True), anchor="mm")
        l_text = (spec.left_detail or "People catch wild cobras -> population drops to zero.")[:70]
        self._draw_multiline_centered(draw, l_text, l_x + 24, l_top + 140, col_w - 48, self._get_font(22, bold=False), (51, 65, 85))

        # Branch Right Card: Perverse Reality
        r_x = 570
        draw.rounded_rectangle([r_x, l_top, r_x + col_w, l_top + col_h], radius=20, fill=(255, 255, 255, 250), outline=(254, 202, 202), width=2)
        draw.rounded_rectangle([r_x + 24, l_top + 24, r_x + col_w - 24, l_top + 64], radius=10, fill=(254, 226, 226))
        draw.text((r_x + col_w // 2, l_top + 44), "PERVERSE EXPLOIT", fill=(185, 28, 28), font=self._get_font(18, bold=True), anchor="mm")
        r_text = (spec.right_detail or "Citizens breed secret snakes for cash -> population skyrockets.")[:70]
        self._draw_multiline_centered(draw, r_text, r_x + 24, l_top + 140, col_w - 48, self._get_font(22, bold=False), (51, 65, 85))

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 5. LAYERED SYSTEMIC & ARCHITECTURAL STACK
    # -------------------------------------------------------------------------
    def render_layered_stack(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders stacked horizontal tiers: Surface Symptom -> Institutional -> Core Mechanism."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        nodes = spec.nodes or [
            VisualNode(id="l1", label="Surface Symptom", badge="LEVEL 1: VISIBLE", detail="Bizarre behavior or sudden failure observed by the public."),
            VisualNode(id="l2", label="Incentive Architecture", badge="LEVEL 2: SYSTEM", detail="The rules and financial rewards shaping human action."),
            VisualNode(id="l3", label="Fundamental Driver", badge="LEVEL 3: ROOT", detail="Evolutionary psychology, physics, or game theory."),
        ]

        n_count = min(4, len(nodes))
        tier_w = 900
        tier_h = 190
        start_y = content_top + 40
        gap = 40

        for i, node in enumerate(nodes[:n_count]):
            ty = start_y + i * (tier_h + gap)
            tx = (1080 - tier_w) // 2

            st = self.STATUS_COLORS.get(node.status or "neutral", self.STATUS_COLORS["neutral"])
            draw.rounded_rectangle([tx, ty, tx + tier_w, ty + tier_h], radius=20, fill=st["fill"], outline=palette["primary"] if i == n_count - 1 else st["border"], width=3 if i == n_count - 1 else 2)

            badge_txt = (node.badge or f"LAYER {i+1}").upper()
            draw.rounded_rectangle([tx + 28, ty + 24, tx + 240, ty + 60], radius=8, fill=palette["badge_bg"] if i == n_count - 1 else st["badge_bg"])
            draw.text((tx + 134, ty + 42), badge_txt, fill=palette["primary"] if i == n_count - 1 else st["badge_text"], font=self._get_font(16, bold=True), anchor="mm")

            draw.text((tx + 28, ty + 100), node.label[:42], fill=(18, 24, 38), font=self._get_font(26, bold=True), anchor="lm")
            if node.detail:
                draw.text((tx + 28, ty + 144), node.detail[:64], fill=(100, 116, 139), font=self._get_font(19, bold=False), anchor="lm")

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 6. QUANTITATIVE DATA VISUALIZATION / COMPARATIVE BARS
    # -------------------------------------------------------------------------
    def render_data_bars(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders quantitative comparative bars with large percentage callouts."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        nodes = spec.nodes or [
            VisualNode(id="b1", label="Standard Industry Loss", value="80%", badge="HARDWARE", detail="Handles sold below cost to lock consumers in"),
            VisualNode(id="b2", label="Refill Profit Margin", value="400%", badge="BLADES", detail="Replacement cartridges yield pure monopoly margins"),
            VisualNode(id="b3", label="Annual Consumer Spend", value="$120", badge="TOTAL", detail="Every year for 50 cents worth of raw steel"),
        ]

        bar_box_w = 900
        start_y = content_top + 40

        for i, node in enumerate(nodes[:3]):
            by = start_y + i * 240
            bx = (1080 - bar_box_w) // 2

            draw.rounded_rectangle([bx, by, bx + bar_box_w, by + 210], radius=20, fill=(255, 255, 255, 250), outline=(226, 232, 240), width=2)

            # Metric Value Callout (Big Bold KPI)
            val_txt = node.value or "100%"
            draw.text((bx + 40, by + 60), val_txt, fill=palette["primary"], font=self._get_font(48, bold=True), anchor="lm")

            # Title
            draw.text((bx + 320, by + 45), node.label[:34], fill=(18, 24, 38), font=self._get_font(26, bold=True), anchor="lm")
            if node.detail:
                draw.text((bx + 320, by + 85), node.detail[:48], fill=(100, 116, 139), font=self._get_font(19, bold=False), anchor="lm")

            # Visual Progress Bar
            bar_track_w = bar_box_w - 80
            draw.rounded_rectangle([bx + 40, by + 140, bx + 40 + bar_track_w, by + 168], radius=8, fill=(241, 245, 249))
            fill_pct = 0.85 if i == 0 else (1.0 if i == 1 else 0.65)
            draw.rounded_rectangle([bx + 40, by + 140, bx + 40 + int(bar_track_w * fill_pct), by + 168], radius=8, fill=palette["primary"])

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 7. DUAL COMPARISON & CONTRAST SPLIT
    # -------------------------------------------------------------------------
    def render_comparison_split(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders editorial dual-column comparison on a clean light canvas."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        card_top = content_top + 40
        card_h = 600
        col_w = 440
        left_x = 75
        right_x = 565

        # LEFT CARD (Intention / Assumption)
        draw.rounded_rectangle([left_x, card_top, left_x + col_w, card_top + card_h], radius=24, fill=(255, 255, 255, 250), outline=(254, 202, 202), width=2)
        l_badge = (spec.left_badge or "WHAT WE ASSUME").upper()
        draw.rounded_rectangle([left_x + 28, card_top + 28, left_x + col_w - 28, card_top + 68], radius=12, fill=(254, 226, 226))
        draw.text((left_x + col_w // 2, card_top + 48), l_badge, fill=(185, 28, 28), font=self._get_font(18, bold=True), anchor="mm")

        l_title = spec.left_title or "Initial Plan"
        draw.text((left_x + col_w // 2, card_top + 115), l_title[:24], fill=(18, 24, 38), font=self._get_font(26, bold=True), anchor="mm")
        l_detail = spec.left_detail or "A straightforward linear outcome where people behave as intended."
        self._draw_multiline_centered(draw, l_detail, left_x + 28, card_top + 200, col_w - 56, self._get_font(22, bold=False), (71, 85, 105))

        # RIGHT CARD (Reality / Underlying Truth)
        draw.rounded_rectangle([right_x, card_top, right_x + col_w, card_top + card_h], radius=24, fill=(255, 255, 255, 250), outline=(187, 247, 208), width=2)
        r_badge = (spec.right_badge or "THE HIDDEN REALITY").upper()
        draw.rounded_rectangle([right_x + 28, card_top + 28, right_x + col_w - 28, card_top + 68], radius=12, fill=(220, 252, 231))
        draw.text((right_x + col_w // 2, card_top + 48), r_badge, fill=(22, 101, 52), font=self._get_font(18, bold=True), anchor="mm")

        r_title = spec.right_title or "Perverse Reality"
        draw.text((right_x + col_w // 2, card_top + 115), r_title[:24], fill=(18, 24, 38), font=self._get_font(26, bold=True), anchor="mm")
        r_detail = spec.right_detail or "Second-order effects alter behavior, leading to the opposite result."
        self._draw_multiline_centered(draw, r_detail, right_x + 28, card_top + 200, col_w - 56, self._get_font(22, bold=False), (71, 85, 105))

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 8. CAUSAL CHAIN / HORIZONTAL PROCESS FLOW
    # -------------------------------------------------------------------------
    def render_causal_chain(
        self,
        spec: DynamicVisualSpec,
        output_path: Path,
    ) -> Path:
        """Renders multi-step causal Domino flow with vertical sequence and connectors."""
        accent = spec.theme_accent or "blue"
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)
        palette = self.BRIGHT_ACCENTS.get(accent, self.BRIGHT_ACCENTS["blue"])

        content_top = self._draw_header(draw, spec.headline, spec.subheadline, accent)

        steps = spec.steps or [node.label for node in spec.nodes] if spec.nodes else [
            "Policy Announced", "Incentive Exploited", "Policy Cancelled", "Catastrophic Infestation"
        ]
        s_count = min(4, len(steps))

        box_w = 880
        box_h = 130
        start_y = content_top + 50
        gap = 48

        for i, step_text in enumerate(steps[:s_count]):
            by = start_y + i * (box_h + gap)
            bx = (1080 - box_w) // 2

            is_last = (i == s_count - 1)
            draw.rounded_rectangle(
                [bx, by, bx + box_w, by + box_h],
                radius=18,
                fill=(255, 255, 255, 250),
                outline=palette["primary"] if is_last else (226, 232, 240),
                width=3 if is_last else 2,
            )

            # Step number circle
            circle_x = bx + 50
            circle_y = by + box_h // 2
            draw.ellipse([circle_x - 24, circle_y - 24, circle_x + 24, circle_y + 24], fill=palette["primary"] if is_last else (241, 245, 249))
            draw.text((circle_x, circle_y), f"0{i+1}", fill=(255, 255, 255) if is_last else (71, 85, 105), font=self._get_font(20, bold=True), anchor="mm")

            draw.text((bx + 110, circle_y), step_text[:45], fill=(18, 24, 38), font=self._get_font(25, bold=True), anchor="lm")

            # Connector downward arrow between boxes
            if i < s_count - 1:
                arrow_top = by + box_h
                arrow_bottom = arrow_top + gap
                self._draw_arrow(draw, (circle_x, arrow_top), (circle_x, arrow_bottom), color=palette["primary"], width=3, arrow_size=12)

        self._draw_takeaway(draw, spec.takeaway, accent, y=1400)
        canvas.convert("RGB").save(output_path, "PNG")
        return output_path

    # -------------------------------------------------------------------------
    # 9. BRIGHT LARGE-FORMAT CONCEPT MEDIA COMPOSITION (980x1180 BORDERLESS CARD)
    # -------------------------------------------------------------------------
    def compose_concept_on_bright_canvas(
        self,
        raw_concept_image: Path,
        output_canvas_path: Path,
        headline: Optional[str] = None,
        badge_text: Optional[str] = None,
        accent: str = "blue",
    ) -> Path:
        """Frames an authentic documentary photograph as an enlarged borderless floating visual."""
        output_canvas_path.parent.mkdir(parents=True, exist_ok=True)
        canvas = self.create_bright_editorial_background(accent=accent)
        draw = ImageDraw.Draw(canvas)

        temp_styled = config.temp_dir / f"styled_concept_{raw_concept_image.stem}.png"
        self.card_engine.render_card(
            image_input=raw_concept_image,
            output_png=temp_styled,
            card_width=980,
            card_height=1180,
            corner_radius=24,
            shadow_blur=32,
            shadow_alpha=120,
        )

        card_img = Image.open(temp_styled).convert("RGBA")
        card_x = (1080 - card_img.width) // 2
        card_y = 380

        canvas.paste(card_img, (card_x, card_y), mask=card_img)

        if badge_text:
            font_badge = self._get_font(21, bold=True)
            pill_y = card_y - 68
            clean_badge = badge_text.strip().upper()[:36]
            draw.rounded_rectangle([290, pill_y, 790, pill_y + 48], radius=14, fill=(15, 23, 42, 245), outline=(75, 85, 105), width=1)
            draw.text((540, pill_y + 24), clean_badge, fill=(255, 255, 255), font=font_badge, anchor="mm")

        canvas.convert("RGB").save(output_canvas_path, "PNG")
        return output_canvas_path
