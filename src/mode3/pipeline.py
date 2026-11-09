"""Mode 3: ChatGPT Conversation Shorts Pipeline.
Coordinates topic generation, dual-agent comedy scriptwriting,
timeline synchronization, UI sound design, and headless video rendering.
"""

import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..config import config
from .comedy_brain import ComedyBrain
from .chat_template import ChatTemplateBuilder
from .sound_designer import SoundDesigner
from .video_recorder import VideoRecorder


class Mode3Pipeline:
    """Full execution pipeline for Mode 3 ChatGPT conversations."""

    def __init__(self):
        self.brain = ComedyBrain()
        self.template_builder = ChatTemplateBuilder(width=config.video_width, height=config.video_height)
        self.sound_designer = SoundDesigner()
        self.recorder = VideoRecorder(width=config.video_width, height=config.video_height)

    def run(
        self,
        topic: Optional[str] = None,
        output_dir: Optional[Path] = None,
        bgm_path: Optional[Path] = None,
        dialogue_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute full end-to-end Mode 3 generation."""
        out_dir = output_dir or (config.output_dir / "mode3_chatgpt")
        out_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = config.root_dir / "temp" / f"mode3_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 60)
        print("[START] AI Shorts Mode 3: ChatGPT Conversation Engine")
        print("=" * 60)

        # 1. Comedy Script Generation
        if dialogue_override:
            print("[Mode3/1] Using custom comedy dialogue override...")
            conv_data = dialogue_override
        else:
            print("[Mode3/1] Synthesizing sharp, hilarious dual-agent dialogue...")
            conv_data = self.brain.generate_conversation(topic)
        title = conv_data.get("title", "ChatGPT Conversation")
        slug = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "_")[:45]
        session_id = int(time.time())

        video_path = out_dir / f"mode3_{slug}_{session_id}.mp4"
        meta_path = out_dir / f"mode3_{slug}_{session_id}_metadata.txt"

        print(f"  * Title: '{title}'")
        print(f"  * Category: {conv_data.get('category', 'Humor')}")
        print(f"  * Hook: \"{conv_data.get('hook', '')}\"")

        # 2. Dual Voice TTS Synthesis (User Speaking & ChatGPT Replying)
        print("[Mode3/2] Synthesizing dual character voices (Human User & ChatGPT AI)...")
        self.sound_designer.synthesize_dialogue_speech(conv_data, temp_dir)
        for idx, t in enumerate(conv_data.get("turns", [])):
            print(f"  * Turn {idx+1} [{t['speaker'].upper()}]: {t.get('audio_duration', 0):.2f}s | \"{t['text'][:55]}...\"")

        # 3. Timeline & Event Computation (Synchronized to Voice Durations)
        print("[Mode3/3] Computing millisecond animation timeline locked to speech...")
        events, total_duration = self.template_builder.compute_timeline(conv_data)
        print(f"  * Total Duration: {total_duration:.1f}s across {len(events)} animation events")

        # 4. Master Audio Construction (Speech + Typing Clicks + Send Whoosh + AI Chimes + Ambient)
        print("[Mode3/4] Mixing broadcast master soundtrack with physical typing clicks and chimes...")
        audio_path = temp_dir / "master_soundtrack.wav"
        self.sound_designer.build_master_audio(
            conversation=conv_data,
            event_timeline=events,
            total_duration=total_duration,
            output_wav=audio_path,
            bgm_path=bgm_path,
        )

        # 5. Pixel-Perfect HTML Interface Generation (Auto-expanding Input & 100% ChatGPT Replica)
        print("[Mode3/5] Building authentic ChatGPT dark-mode DOM...")
        html_content = self.template_builder.render_html(conv_data, events, total_duration)

        # 6. Headless Vertical 9:16 Video Recording
        print("[Mode3/6] Recording high-fidelity vertical video with Playwright...")
        self.recorder.record_html_to_video(
            html_content=html_content,
            audio_path=audio_path,
            output_mp4=video_path,
            temp_dir=temp_dir,
            total_duration=total_duration,
        )

        # 7. Generate Ready-to-Publish Metadata
        self._save_metadata(meta_path, conv_data, video_path)

        # Cleanup temporary files
        audio_path.unlink(missing_ok=True)

        print("=" * 60)
        print(f"[SUCCESS] Mode 3 Short Generated Successfully!")
        print(f"  * Video:    {video_path}")
        print(f"  * Metadata: {meta_path}")
        print(f"  * Duration: {total_duration:.1f}s")
        print("=" * 60)

        return {
            "title": title,
            "video_path": video_path,
            "metadata_path": meta_path,
            "duration": total_duration,
            "status": "SUCCESS",
            "topic": topic or title,
            "conversation": conv_data,
        }

    def _save_metadata(self, meta_path: Path, conv_data: Dict[str, Any], video_path: Path):
        """Save ready-to-copy social metadata."""
        title = conv_data.get("title", "When You Ask ChatGPT The Truth")
        hook = conv_data.get("hook", "")
        category = conv_data.get("category", "Tech Humor")
        content = f"""=== YOUTUBE SHORTS / INSTAGRAM REELS / TIKTOK METADATA ===

CLIP TITLE:
{title} #Shorts

CATEGORY:
{category}

HOOK (First 3 Seconds):
"{hook}"

CAPTION / DESCRIPTION:
{hook}

When you ask ChatGPT a real question and it drops the brutal truth. 😂👇
Drop your funniest ChatGPT prompts in the comments!

HASHTAGS:
#chatgpt #ai #techhumor #programming #developer #shorts #viral #funny

PINNED COMMENT:
Did ChatGPT go too far? Drop your thoughts below! 👇
"""
        meta_path.write_text(content, encoding="utf-8")
