"""Universal FFmpeg Timeline & Overlay Filtergraph Builder.
Compiles dynamic multi-visual overlay chains and audio SFX sync for any arbitrary list of timed cards.
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple


class OverlayTimelineBuilder:
    """Compiles FFmpeg video overlay filter chains and synchronized SFX delays."""

    def __init__(self, canvas_width: int = 1080, canvas_height: int = 1920):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

    def build_video_chain(
        self,
        base_video_label: str,
        cards: List[Dict[str, Any]],
        start_input_idx: int,
        card_y: int = 190,
    ) -> Tuple[List[str], str]:
        """
        Builds FFmpeg overlay filter lines for consecutive cards.
        Cards are centered horizontally: X = (canvas_width - card_width) / 2.
        """
        filter_lines = []
        curr_label = base_video_label

        for i, card in enumerate(cards):
            input_idx = start_input_idx + i
            next_label = f"v_card_cut_{i}"
            start_t = card["start"]
            end_t = card["end"]

            filter_lines.append(
                f"[{curr_label}][{input_idx}:v]overlay="
                f"x=(W-w)/2:y={card_y}:"
                f"enable='between(t,{start_t:.3f},{end_t:.3f})'[{next_label}]"
            )
            curr_label = next_label

        return filter_lines, curr_label

    def build_audio_sfx_chain(
        self,
        cards: List[Dict[str, Any]],
        pop_sfx_path: Path,
        start_input_idx: int,
        volume: float = 0.28,
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Builds audio input declarations, adelay filters, and mix labels
        to trigger pop.wav at each card start timestamp.
        """
        inputs = []
        filter_lines = []
        mix_labels = []

        if not pop_sfx_path.exists() or not cards:
            return inputs, filter_lines, mix_labels

        for i, card in enumerate(cards):
            delay_ms = max(0, int(card["start"] * 1000))
            input_idx = start_input_idx + i
            label = f"sfx_pop_{i}"

            inputs.extend(["-i", str(pop_sfx_path)])
            filter_lines.append(
                f"[{input_idx}:a]volume={volume:.2f},adelay={delay_ms}|{delay_ms}[{label}]"
            )
            mix_labels.append(f"[{label}]")

        return inputs, filter_lines, mix_labels
