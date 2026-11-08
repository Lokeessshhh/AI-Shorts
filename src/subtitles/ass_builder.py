import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
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


GREEN_KEYWORDS = {"MONEY", "CASH", "POWER", "WIN", "PROFIT", "SUCCESS", "MILLIONS", "BILLIONS", "SAVES", "SAVING", "GOLD", "BITCOIN", "RICH"}
CYAN_KEYWORDS = {"CODE", "DATA", "ROBOT", "AI", "COMPUTER", "NETWORK", "SERVERS", "SERVER", "TOKENS", "TECH", "SPACE", "ROCKET", "STAR"}
RED_KEYWORDS = {"FAKE", "TRAP", "DANGER", "SECRET", "LOSE", "FAIL", "WARNING", "CRACK", "CRACKS", "FIRE", "HEAT", "BLOOD", "DEAD", "KILL"}

# Inline Unicode Emojis mapped to key concepts (renders directly inside subtitle text before the word)
INLINE_KEYWORD_EMOJIS: Dict[str, str] = {
    # Tech, AI & Startups
    "AI": "🤖",
    "ROBOT": "🤖",
    "ROBOTS": "🤖",
    "CHATGPT": "🤖",
    "OPENAI": "🤖",
    "GPT": "🤖",
    "TECH": "💻",
    "TECHNOLOGY": "💻",
    "COMPUTER": "💻",
    "CODE": "💻",
    "CODING": "💻",
    "PROGRAM": "💻",
    "SOFTWARE": "💻",
    "LAUNCH": "🚀",
    "LAUNCHED": "🚀",
    "LAUNCHING": "🚀",
    "ROCKET": "🚀",
    "STARTUP": "🚀",
    "STARTUPS": "🚀",
    "FOUNDER": "🚀",
    "SCALE": "📈",
    "SCALING": "📈",
    "GROWTH": "📈",
    "MARKET": "📈",
    "BIGGER": "📈",
    "BIGGEST": "📈",
    # Mindset, Ideas & Status
    "IDEA": "💡",
    "IDEAS": "💡",
    "THINK": "💡",
    "THOUGHT": "💡",
    "SMART": "💡",
    "INTELLIGENCE": "💡",
    "SUPERINTELLIGENCE": "🧠",
    "BRAIN": "🧠",
    "MIND": "🧠",
    "MINDSET": "🧠",
    "PSYCHOLOGY": "🧠",
    "POWER": "⚡",
    "SUPERPOWER": "⚡",
    "STATUS": "⚡",
    "ENERGY": "⚡",
    "FAST": "⚡",
    "WIN": "🏆",
    "WINNING": "🏆",
    "WON": "🏆",
    "BEST": "🏆",
    "SUCCESS": "🏆",
    # Fame, Freedom & People
    "FAME": "⭐",
    "FAMOUS": "⭐",
    "STAR": "⭐",
    "CELEBRITY": "⭐",
    "FREEDOM": "🕊️",
    "FREE": "🕊️",
    "LIFE": "🌱",
    "WORLD": "🌍",
    "GLOBAL": "🌍",
    "HUMAN": "👤",
    "HUMANS": "👤",
    "HUMANITY": "👥",
    "PEOPLE": "👥",
    "TEAM": "👥",
    # Countries & Culture
    "INDIA": "🇮🇳",
    "INDIAN": "🇮🇳",
    "AMERICA": "🇺🇸",
    "US": "🇺🇸",
    "USA": "🇺🇸",
    # Money, Wealth & Equity
    "MONEY": "💰",
    "EQUITY": "💰",
    "CASH": "💰",
    "DOLLAR": "💵",
    "DOLLARS": "💵",
    "RICH": "💰",
    "BILLION": "💰",
    "BILLIONAIRE": "💰",
    "MILLION": "💰",
    # Emotions, Warnings & Shock
    "FIRE": "🔥",
    "BURNING": "🔥",
    "HOT": "🔥",
    "SHOCK": "💥",
    "SHOCKING": "💥",
    "CRAZY": "🤯",
    "INSANE": "🤯",
    "DEAD": "💀",
    "DIED": "💀",
    "DEATH": "💀",
    "KILL": "💀",
    "KILLED": "💀",
    "DANGER": "⚠️",
    "RISK": "⚠️",
    "WARNING": "⚠️",
    "SECRET": "🔒",
    "TRUTH": "🔍",
    "LOOK": "👀",
    "SEE": "👀",
    "WATCH": "👀",
    "LOVE": "❤️",
    "HEART": "❤️",
}


class ASSSubtitleBuilder:
    def __init__(
        self,
        font_name: str = "Arial Black",
        font_size: int = 70,
        primary_color: str = "&H00FFFFFF",      # Crisp White (BGR format in ASS)
        default_highlight: str = "&H0000FFFF",  # Electric Yellow/Gold
        outline_color: str = "&H00000000",      # Pure Black
        outline_width: int = 5,
        shadow: int = 2,
        alignment: int = 2,                     # 2 = Bottom-Center
        margin_v: int = 420,                    # Above platform UI buttons
        max_words_per_line: int = 3,            # 3 words for high retention
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

    def _get_highlight_color(self, word: str) -> str:
        clean = re.sub(r"[^\w]", "", word).upper()
        if clean in GREEN_KEYWORDS:
            return "&H0000FF00"  # Neon Green
        if clean in CYAN_KEYWORDS:
            return "&H00FFFF00"  # Neon Cyan
        if clean in RED_KEYWORDS:
            return "&H003333FF"  # Neon Red/Coral
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
        self, words: List[WordTimestamp], output_path: Path
    ) -> Tuple[Path, List[EmojiEvent]]:
        """Compile word timestamps into clean ASS subtitles with multi-color pops and extract universal 3D color emoji events."""
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,{self.font_name},{self.font_size},{self.primary_color},&H000000FF,{self.outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,{self.outline_width},{self.shadow},{self.alignment},40,40,{self.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogues = []
        emoji_events: List[EmojiEvent] = []

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

        # For each chunk, create dialogue entries where active word pops with dynamic color
        # and inline emoji is attached directly before the keyword where it belongs
        raw_dialogues = []
        for chunk in chunks:
            # Check if any word in this chunk has a keyword emoji (at most one per chunk)
            emoji_word_idx = None
            chosen_emoji = None
            for idx, w in enumerate(chunk):
                cw = re.sub(r"[^\w]", "", w.word)
                if cw in INLINE_KEYWORD_EMOJIS:
                    emoji_word_idx = idx
                    chosen_emoji = INLINE_KEYWORD_EMOJIS[cw]
                    break

            for active_idx, target_word in enumerate(chunk):
                formatted_words = []
                for i, w in enumerate(chunk):
                    clean_w = re.sub(r"[^\w]", "", w.word)
                    display_word = w.word
                    # Place emoji inline just before the word where it belongs
                    if i == emoji_word_idx:
                        display_word = f"{chosen_emoji} {w.word}"

                    if i == active_idx:
                        color = self._get_highlight_color(clean_w)
                        formatted_words.append(
                            f"{{\\c{color}&\\fscx108\\fscy108}}{display_word}{{\\c{self.primary_color}&\\fscx100\\fscy100}}"
                        )
                    else:
                        formatted_words.append(display_word)

                line_text = " ".join(formatted_words)
                raw_dialogues.append({
                    "start": target_word.start,
                    "end": target_word.end,
                    "text": line_text,
                })

        # STRICT ZERO-OVERLAP TIMING PASS:
        # Guarantees that at any point in time, AT MOST ONE dialogue is active on screen.
        for i in range(len(raw_dialogues)):
            curr = raw_dialogues[i]
            if i + 1 < len(raw_dialogues):
                nxt = raw_dialogues[i + 1]
                # Ensure monotonic start times
                if nxt["start"] <= curr["start"]:
                    nxt["start"] = curr["start"] + 0.08

                # End of current MUST not exceed start of next
                if curr["end"] > nxt["start"]:
                    curr["end"] = nxt["start"]
                elif (nxt["start"] - curr["end"]) > 0.45:
                    # Natural conversational pause: let subtitle disappear after brief hold
                    curr["end"] = min(curr["end"] + 0.15, nxt["start"])
                else:
                    curr["end"] = nxt["start"]
            else:
                curr["end"] = curr["end"] + 0.25

            # Guarantee positive duration
            if curr["end"] <= curr["start"]:
                curr["end"] = curr["start"] + 0.08

        for d in raw_dialogues:
            start_str = self._format_time(d["start"])
            end_str = self._format_time(d["end"])
            dialogues.append(
                f"Dialogue: 0,{start_str},{end_str},Hormozi,,0,0,0,,{d['text']}"
            )

        full_content = header + "\n".join(dialogues) + "\n"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        return output_path, emoji_events
