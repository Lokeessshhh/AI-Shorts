import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from root directory
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


@dataclass
class Settings:
    # API Keys & Models
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    openrouter_model: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_MODEL", "openai/gpt-4o-mini"
        )
    )
    pexels_api_key: str = field(
        default_factory=lambda: os.getenv("PEXELS_API_KEY", "")
    )

    # Audio & Voice Defaults
    default_voice: str = field(
        default_factory=lambda: os.getenv(
            "DEFAULT_VOICE", "en-US-AndrewNeural"
        )
    )
    bgm_volume: float = 0.15  # -16dB ducking relative to voice
    voice_volume: float = 1.0

    # Video Dimensions (Shorts / Reels 9:16)
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    target_video_duration: float = 30.0  # Exactly 30 seconds only

    # Directories
    root_dir: Path = ROOT_DIR
    output_dir: Path = ROOT_DIR / "output"
    temp_dir: Path = ROOT_DIR / "temp"
    assets_dir: Path = ROOT_DIR / "assets"
    bgm_dir: Path = ROOT_DIR / "assets" / "bgm"
    fonts_dir: Path = ROOT_DIR / "assets" / "fonts"
    broll_dir: Path = ROOT_DIR / "assets" / "broll"
    clipper_dir: Path = ROOT_DIR / "assets" / "clipper_cache"
    gameplay_dir: Path = ROOT_DIR / "assets" / "gameplay"
    sfx_dir: Path = ROOT_DIR / "assets" / "sfx"

    # Mode 3 Clipper Defaults
    clipper_default_clips: int = 3
    clipper_min_duration: float = 30.0
    clipper_max_duration: float = 60.0

    def __post_init__(self):
        # Ensure directories exist
        for d in [
            self.output_dir,
            self.temp_dir,
            self.assets_dir,
            self.bgm_dir,
            self.fonts_dir,
            self.broll_dir,
            self.clipper_dir,
            self.gameplay_dir,
            self.sfx_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


config = Settings()
