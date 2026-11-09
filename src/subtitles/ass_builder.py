"""Kinetic Typography and Production Caption Studio.
Generates mobile-first, high-retention Advanced SubStation Alpha (.ass) subtitles:
- 88pt Bold condensed typography with 6px deep black stroke and crisp drop shadow.
- Real kinetic spring pop physics: instant 122% scale pop with overshoot settle (\t transforms).
- Dynamic semantic color mapping: numbers/data (cyan), danger/crisis (coral), wealth (gold), insight (royal blue).
- Strict 1 to 3 words per line RSVP chunking.
- Monotonic zero-overlap timing synchronization with Whisper word alignments.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
from src.config import config
from .emoji_manager import EmojiManager


@dataclass
class WordTimestamp:
    word: str
    start: float  # in seconds
    end: float    # in seconds


@dataclass
class EmojiEvent:
    file_path: Path
    start: float
    end: float
    word: str


# Semantic keyword categories for dynamic color accents (BGR in ASS format)
# Cyan: &HFFF000& (#00F0FF) - Numbers, tech, data, physics, metrics
# Gold: &H00D7FF& (#FFD700) - Wealth, currency, rewards, winning
# Coral Red: &H3333FF& (#FF3333) - Disasters, crashes, deaths, traps, failures
# Royal Amethyst: &HF88C81& (#818CF8) - Scientific breakthroughs, laws, secrets, discoveries
# Electric Canary: &H00E5FF& (#FFE500) - General high-retention active pop

CYAN_KEYWORDS: Set[str] = {
    "CODE", "DATA", "ROBOT", "AI", "COMPUTER", "NETWORK", "SERVERS", "SERVER",
    "TOKENS", "TECH", "SPACE", "ROCKET", "PRESSURE", "PHYSICS", "STRESS", "CORNER",
    "CORNERS", "SQUARE", "ROUNDED", "WINDOW", "WINDOWS", "MICRO", "FRACTURE",
    "ENGINEERING", "TEST", "TANK", "WATER", "CABIN", "ALTITUDE", "JET", "JETS", "AIRCRAFT"
}

GOLD_KEYWORDS: Set[str] = {
    "MONEY", "CASH", "POWER", "WIN", "PROFIT", "SUCCESS", "MILLIONS", "BILLIONS",
    "SAVES", "SAVING", "GOLD", "BITCOIN", "RICH", "BOUNTY", "BOUNTIES", "PAYOUT",
    "PAYOUTS", "REWARD", "DOLLAR", "DOLLARS", "WEALTH", "PRICE", "COST", "MARGIN", "PROFITABLE"
}

RED_KEYWORDS: Set[str] = {
    "FAKE", "TRAP", "DANGER", "SECRET", "LOSE", "FAIL", "WARNING", "CRACK", "CRACKS",
    "FIRE", "HEAT", "BLOOD", "DEAD", "KILL", "DEATH", "EXPLODED", "EXPLODE",
    "DISINTEGRATED", "DISASTER", "FATAL", "CHAOS", "POISON", "SNAKE", "SNAKES",
    "COBRA", "COBRAS", "INFESTATION", "CATASTROPHE", "CRASH", "CRASHED", "CRASHES"
}

INSIGHT_KEYWORDS: Set[str] = {
    "TRUTH", "REVEALED", "DISCOVERY", "BREAKTHROUGH", "SECRET", "SOLVED", "PUZZLE",
    "PARADOX", "LAW", "PRINCIPLE", "CAUSE", "REASON", "FOUND", "ANSWER", "KEY", "EXPLAINED"
}


class ASSSubtitleBuilder:
    def __init__(
        self,
        font_name: str = "Arial Black",
        font_size: int = 86,
        primary_color: str = "&H00FFFFFF",      # Crisp White
        default_highlight: str = "&H00E5FF",    # Electric Canary Yellow (#FFE500 in BGR)
        outline_color: str = "&H00000000",      # Pure Deep Black
        outline_width: int = 6,                 # 6px stroke for high contrast
        shadow: int = 3,                        # Directional 3px shadow
        alignment: int = 2,                     # 2 = Bottom-Center (scales symmetrically)
        margin_v: int = 430,                    # Safe area above platform UI buttons
        max_words_per_line: int = 3,            # Strict 1-3 words RSVP chunking
    ):
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.default_highlight = default_highlight
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.shadow = shadow
        self.alignment = alignment
        self.margin_v = margin_v
        self.max_words_per_line = max_words_per_line
        self.emoji_mgr = EmojiManager()

    def _get_highlight_color(self, word: str, custom_emphasis: Optional[Set[str]] = None) -> str:
        """Determines semantic highlight color based on LLM emphasis, numbers, and categories."""
        clean = re.sub(r"[^\w]", "", word).upper()

        # 1. Any word containing digits (numbers, years, percentages, dollar amounts)
        if re.search(r"\d", word):
            return "&HFFF000&"  # Electric Cyan

        # 2. Custom emphasis passed from LLM script director
        if custom_emphasis and clean in custom_emphasis:
            return "&HFFF000&"  # Electric Cyan for high-priority turning points

        # 3. Categorical semantic mapping
        if clean in RED_KEYWORDS:
            return "&H3333FF&"  # Coral Red (#FF3333)
        if clean in GOLD_KEYWORDS:
            return "&H00D7FF&"  # Vivid Gold (#FFD700)
        if clean in CYAN_KEYWORDS:
            return "&HFFF000&"  # Electric Cyan (#00F0FF)
        if clean in INSIGHT_KEYWORDS:
            return "&HF88C81&"  # Royal Amethyst (#818CF8)

        return self.default_highlight

    def _format_time(self, seconds: float) -> str:
        """Format seconds into ASS timestamp format: H:MM:SS.cs"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int(round((seconds - int(seconds)) * 100))
        if centisecs >= 100:
            centisecs = 99
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def build_ass(
        self,
        words: List[WordTimestamp],
        output_path: Path,
        header_hook: Optional[str] = None,
        emphasis_keywords: Optional[List[str]] = None,
        credit_attribution: Optional[str] = None,
    ) -> Tuple[Path, List[EmojiEvent]]:
        """Compile word timestamps into kinetic typography ASS subtitles with real spring pop physics."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        emphasis_set = {re.sub(r"[^\w]", "", k).upper() for k in (emphasis_keywords or [])}

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KineticMain,{self.font_name},{self.font_size},{self.primary_color},&H000000FF,{self.outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,{self.outline_width},{self.shadow},{self.alignment},40,40,{self.margin_v},1
Style: HeaderHook,{self.font_name},58,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,6,0,8,40,40,320,1
Style: CreditBadge,{self.font_name},30,&H00E0E0E0,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,3,0,9,40,40,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogues = []
        if credit_attribution:
            clean_credit = re.sub(r"[^\w\s@.]", "", credit_attribution).strip()
            if clean_credit:
                dialogues.append(
                    f"Dialogue: 0,0:00:00.00,0:01:30.00,CreditBadge,,0,0,0,,{{\\fad(300,300)}}Credit: @{clean_credit}"
                )
        if header_hook:
            clean_hook = header_hook.strip().upper()
            dialogues.append(
                f"Dialogue: 1,0:00:00.00,0:00:02.40,HeaderHook,,0,0,0,,{{\\fad(100,180)}}{clean_hook}"
            )
        emoji_events: List[EmojiEvent] = []

        # 1. Chunk words into short 1-3 word lines (RSVP pacing)
        chunks: List[List[WordTimestamp]] = []
        current_chunk: List[WordTimestamp] = []

        for w in words:
            clean_word = w.word.strip().upper()
            if not clean_word:
                continue

            current_chunk.append(WordTimestamp(word=clean_word, start=w.start, end=w.end))
            if len(current_chunk) >= self.max_words_per_line:
                chunks.append(current_chunk)
                current_chunk = []

        if current_chunk:
            chunks.append(current_chunk)

        # 2. Build kinetic pop animation for each active word in each chunk
        raw_dialogues = []
        for chunk in chunks:
            for active_idx, target_word in enumerate(chunk):
                formatted_words = []
                for i, w in enumerate(chunk):
                    clean_w = re.sub(r"[^\w]", "", w.word)
                    display_word = w.word

                    if i == active_idx:
                        color = self._get_highlight_color(clean_w, emphasis_set)
                        # Real kinetic spring pop: instant 122% scale, snaps to 100% at 90ms, slight bounce to 106% at 160ms, settles at 100%
                        pop_tag = (
                            f"{{\\c{color}&"
                            f"\\fscx122\\fscy122"
                            f"\\t(0,90,\\fscx100\\fscy100)"
                            f"\\t(90,160,\\fscx106\\fscy106)"
                            f"\\t(160,220,\\fscx100\\fscy100)}}"
                            f"{display_word}"
                            f"{{\\c{self.primary_color}&\\fscx100\\fscy100}}"
                        )
                        formatted_words.append(pop_tag)
                    else:
                        formatted_words.append(display_word)

                line_text = " ".join(formatted_words)
                raw_dialogues.append({
                    "start": target_word.start,
                    "end": target_word.end,
                    "text": line_text,
                })

        # 3. Strict zero-overlap timing pass (ensures monotonic timeline and zero flickering)
        for i in range(len(raw_dialogues)):
            curr = raw_dialogues[i]
            if i + 1 < len(raw_dialogues):
                nxt = raw_dialogues[i + 1]
                if nxt["start"] <= curr["start"]:
                    nxt["start"] = curr["start"] + 0.08

                if curr["end"] > nxt["start"]:
                    curr["end"] = nxt["start"]
                elif (nxt["start"] - curr["end"]) > 0.40:
                    curr["end"] = min(curr["end"] + 0.15, nxt["start"])
                else:
                    curr["end"] = nxt["start"]
            else:
                curr["end"] = curr["end"] + 0.25

            if curr["end"] <= curr["start"]:
                curr["end"] = curr["start"] + 0.08

        for d in raw_dialogues:
            start_str = self._format_time(d["start"])
            end_str = self._format_time(d["end"])
            dialogues.append(
                f"Dialogue: 0,{start_str},{end_str},KineticMain,,0,0,0,,{d['text']}"
            )

        full_content = header + "\n".join(dialogues) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        return output_path, emoji_events
