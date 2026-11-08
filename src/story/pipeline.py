"""Mode 2 Master Pipeline Coordinator.
Orchestrates 4-act Reddit story ingestion / AI generation, Pillow dark-mode card rendering,
multi-voice character dialogue synthesis, Whisper word timestamping, gameplay slicing,
Studio BGM integration with dynamic sidechain ducking, and master FFmpeg assembly.
"""

import time
import re
import random
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..config import config
from ..voice.tts import TTSEngine
from ..subtitles.whisper_stt import WhisperTranscriber
from .story_fetcher import StoryFetcher
from .card_renderer import RedditCardRenderer
from .gameplay_manager import GameplayManager
from .editor import StoryEditor


def slugify(text: str) -> str:
    """Convert text into a safe filename slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "_", text)[:40]


class Mode2StoryPipeline:
    """End-to-End Pipeline for Mode 2: Reddit Stories & Gameplay Shorts."""

    def __init__(
        self,
        story_fetcher: Optional[StoryFetcher] = None,
        card_renderer: Optional[RedditCardRenderer] = None,
        gameplay_manager: Optional[GameplayManager] = None,
        voice_engine: Optional[TTSEngine] = None,
        transcriber: Optional[WhisperTranscriber] = None,
        editor: Optional[StoryEditor] = None,
    ):
        self.story_fetcher = story_fetcher or StoryFetcher()
        self.card_renderer = card_renderer or RedditCardRenderer()
        self.gameplay_manager = gameplay_manager or GameplayManager()
        self.voice_engine = voice_engine or TTSEngine()
        self.transcriber = transcriber or WhisperTranscriber()
        self.editor = editor or StoryEditor()

    def run(
        self,
        reddit_url: Optional[str] = None,
        subreddit: Optional[str] = None,
        topic: Optional[str] = None,
        gameplay_style: str = "minecraft",
        voice: Optional[str] = None,
        layout: str = "floating_card",
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Execute full Mode 2 workflow.
        Layout options: 'floating_card' (Modern SOTA) or 'split_screen' (Classic 50/50).
        """
        output_dir = output_dir or config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        session_id = int(time.time())

        clean_layout = layout.lower().strip() if layout else "floating_card"
        if clean_layout not in ["floating_card", "split_screen"]:
            clean_layout = "floating_card"

        print("=" * 60)
        print("[START] AI Shorts Mode 2: Ultimate Reddit Story Generator")
        print(f"[LAYOUT] {clean_layout.upper()}")
        print(f"[GAMEPLAY] {gameplay_style}")
        print("=" * 60)

        # Step 1: Ingest or Generate 4-Act Story
        print("\n[1/5] Sourcing 4-act viral story...")
        if reddit_url:
            story = self.story_fetcher.fetch_from_reddit_url(reddit_url)
        elif subreddit:
            story = self.story_fetcher.fetch_from_subreddit(subreddit)
        else:
            story = self.story_fetcher.generate_ai_story(topic)

        print(f"  * Subreddit: {story['subreddit']}")
        print(f"  * Title: {story['title']}")
        print(f"  * Author: {story['author']} (Upvotes: {story['score']})")
        print(f"  * BGM Mood: {story.get('bgm_mood', 'dark_suspense')}")

        temp_dir = config.temp_dir / f"story_{session_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Step 2: Multi-Voice Dialogue / Neural Voiceover Synthesis
        chosen_voice = voice or "en-US-ChristopherNeural"
        dialogue_segments = story.get("dialogue_segments", [])

        print(f"\n[2/5] Synthesizing neural voiceover...")
        if dialogue_segments and len(dialogue_segments) > 1:
            print(f"  * Multi-Voice Dialogue ({len(dialogue_segments)} segments): Narrator + Characters")
            tts_res = self.voice_engine.synthesize_dialogue(
                segments=dialogue_segments,
                output_filename=f"story_{session_id}/story_voice.mp3",
                narrator_voice=chosen_voice,
                female_voice="en-US-AvaNeural",
                male_voice="en-US-EricNeural",
                apply_studio_mastering=True,
            )
        else:
            print(f"  * Solo Voiceover ({chosen_voice})")
            self.voice_engine.voice = chosen_voice
            tts_res = self.voice_engine.synthesize(
                text=story["full_spoken_text"],
                output_filename=f"story_{session_id}/story_voice.mp3",
                target_duration=None,
                apply_studio_mastering=True,
            )
        voice_mp3 = tts_res.audio_path

        # Step 3: Whisper Word-Level Alignment
        print("\n[3/5] Transcribing word timestamps with faster-whisper...")
        word_data = self.transcriber.transcribe_words(voice_mp3)
        story_duration = word_data[-1].end if word_data else 45.0
        print(f"  * Spoken Duration: {story_duration:.2f} seconds ({len(word_data)} words)")

        word_dicts = [
            {"word": w.word, "start": w.start, "end": w.end}
            for w in word_data
        ]

        # Calculate approximate twist timestamp for SFX hit
        twist_time = story_duration * 0.55

        # Step 4: Synthesize Dark-Mode Cards via Pillow
        print("\n[4/5] Synthesizing Reddit UI cards via Pillow...")
        card_png = temp_dir / "reddit_card.png"
        header_pill_png = None
        comment_card_png = None

        if clean_layout == "floating_card":
            # Transparent floating card with drop shadow
            self.card_renderer.render_card(
                story=story,
                output_png=card_png,
                canvas_width=config.video_width,   # 1080
                canvas_height=800,
                card_width=980,
                transparent_bg=True,
            )
            # Minimal header pill
            header_pill_png = temp_dir / "header_pill.png"
            self.card_renderer.render_header_pill(story, header_pill_png)

            # Optional comment card
            if story.get("top_comment"):
                comment_card_png = temp_dir / "comment_card.png"
                self.card_renderer.render_comment_card(story["top_comment"], comment_card_png)
        else:
            # Solid split-screen card
            self.card_renderer.render_card(
                story=story,
                output_png=card_png,
                canvas_width=config.video_width,   # 1080
                canvas_height=960,                 # 50/50 split height
                card_width=980,
                transparent_bg=False,
            )

        # Step 5: Sourcing Studio BGM Track & Slicing Gameplay
        print("\n[5/5] Slicing gameplay & rendering master short...")
        bgm_mood = story.get("bgm_mood", "dark_suspense")
        mood_folder = config.bgm_dir / bgm_mood
        bgm_files = list(mood_folder.glob("*.mp3")) if mood_folder.exists() else []
        if not bgm_files:
            bgm_files = list(config.bgm_dir.rglob("*.mp3"))
        chosen_bgm = random.choice(bgm_files) if bgm_files else None
        if chosen_bgm:
            print(f"  * Assigned Studio BGM [{bgm_mood}]: {chosen_bgm.name}")

        gameplay_slice = temp_dir / "gameplay_slice.mp4"
        gp_height = 1920 if clean_layout == "floating_card" else 960
        self.gameplay_manager.get_gameplay_slice(
            target_duration=story_duration,
            output_mp4=gameplay_slice,
            style=gameplay_style,
            width=config.video_width,
            height=gp_height,
        )

        # Compose Master Short
        slug = slugify(story["title"])
        master_video = output_dir / f"story_{slug}_{session_id}.mp4"
        master_meta = output_dir / f"story_{slug}_{session_id}_metadata.txt"

        t_render_start = time.time()
        if clean_layout == "floating_card":
            self.editor.assemble_floating_card(
                card_png=card_png,
                gameplay_mp4=gameplay_slice,
                voice_audio=voice_mp3,
                word_timestamps=word_dicts,
                output_mp4=master_video,
                temp_dir=temp_dir,
                story_duration=story_duration,
                header_pill_png=header_pill_png,
                comment_card_png=comment_card_png,
                bgm_path=chosen_bgm,
                card_duration=3.8,
                twist_time=twist_time,
                enable_progress_bar=True,
                enable_micro_zoom=True,
            )
        else:
            self.editor.assemble_split_screen(
                card_png=card_png,
                gameplay_mp4=gameplay_slice,
                voice_audio=voice_mp3,
                word_timestamps=word_dicts,
                output_mp4=master_video,
                temp_dir=temp_dir,
                story_duration=story_duration,
                bgm_path=chosen_bgm,
                enable_progress_bar=True,
                enable_micro_zoom=True,
            )

        render_time = time.time() - t_render_start
        self._save_metadata(master_meta, story)

        print("\n" + "=" * 60)
        print(f"[SUCCESS] Master Reddit Story Short created in {render_time:.1f}s!")
        print(f"  * Master Video: {master_video}")
        print(f"  * Metadata: {master_meta}")
        print("=" * 60)

        return {
            "title": story["title"],
            "video_path": master_video,
            "metadata_path": master_meta,
            "duration": round(story_duration, 2),
            "render_time": round(render_time, 1),
            "layout": clean_layout,
            "hashtags": story.get("hashtags", []),
        }

    def _save_metadata(self, meta_path: Path, story: Dict[str, Any]) -> None:
        """Save ready-to-copy YouTube Shorts / TikTok / Reels metadata."""
        hashtags_str = " ".join(story.get("hashtags", ["#redditstories", "#aita", "#storytime", "#shorts"]))
        content = f"""=== YOUTUBE SHORTS / TIKTOK / REELS METADATA ===

TITLE:
{story['title']}

SUBREDDIT: {story['subreddit']} | UPVOTES: {story['score']}

HOOK:
"{story.get('spoken_hook', story['title'])}"

BGM MOOD:
{story.get('bgm_mood', 'dark_suspense')}

DESCRIPTION:
{story['title']}
What would you do in this situation? Let us know in the comments below! 👇

HASHTAGS:
{hashtags_str}

PINNED COMMENT:
Would you forgive them or cut all ties? Drop your thoughts below! 👇
"""
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(content)


def run_story_generator(
    reddit_url: Optional[str] = None,
    subreddit: Optional[str] = None,
    topic: Optional[str] = None,
    gameplay_style: str = "minecraft",
    voice: Optional[str] = None,
    layout: str = "floating_card",
) -> Dict[str, Any]:
    """Convenience entrypoint function for Mode 2."""
    pipeline = Mode2StoryPipeline()
    return pipeline.run(
        reddit_url=reddit_url,
        subreddit=subreddit,
        topic=topic,
        gameplay_style=gameplay_style,
        voice=voice,
        layout=layout,
    )
