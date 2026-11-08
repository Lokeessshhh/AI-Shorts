"""Mode 2: Developer vs Claude Conversational Shorts Engine (Encyclopedic Media Edition).
Layout:
- Background: Full-screen satisfying gameplay (Minecraft parkour, Subway, etc.)
- Top-Middle (X=180, Y=240, 720x520): Multi-Source Encyclopedic Image Carousel (Wikipedia + Wikimedia + DuckDuckGo)
- Bottom-Left: Chibi Iron Man at MacBook (User/Dev avatar)
- Bottom-Right: Claude 3.5 Sonnet circular avatar with glowing AI ring
- Center: High-retention Hormozi subtitles
- Dialogue: Technical concepts explained via dead-simple, mind-blowing everyday analogies
- Studio Sound Design: Dual neural voices, keyboard typing, AI chime, card pop SFX, sidechain ducked BGM
"""

import time
import json
import re
import random
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests

from ..config import config
from ..voice.tts import TTSEngine
from ..subtitles.whisper_stt import WhisperTranscriber
from ..subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp
from .speech_normalizer import normalize_for_speech
from .gameplay_manager import GameplayManager
from ..visuals.concept_fetcher import ConceptImageFetcher
from ..visuals.card_engine import VisualCardEngine
from ..visuals.overlay_timeline import OverlayTimelineBuilder


DEV_CLAUDE_SYSTEM_PROMPT = """You are an elite short-form scriptwriter creating viral educational shorts for TikTok, Reels, and YouTube Shorts.

The format is a sharp, witty conversation between:
1. "dev": A curious, energetic developer/user (represented by chibi Iron Man at an Apple MacBook in the bottom-left corner).
2. "claude": Claude 3.5 Sonnet (represented by the Anthropic Coral avatar in the bottom-right corner).

CORE REQUIREMENT:
The topic must be explained through a DEAD SIMPLE, VISUAL REAL-WORLD ANALOGY so that anyone (even an 11-year-old or non-coder) understands it instantly! Works for ANY technical, scientific, or everyday mystery topic.

PROVEN HIGH-RETENTION FORMULA:
- ACT I: The Everyday Mystery / Hook (0-3s): Dev asks a burning question that everyone wonders about.
- ACT II: The Mind-Blowing Analogy (3-18s): Claude breaks down the invisible mechanism using an everyday physical object.
- ACT III: The Tech Reality (18-28s): Connects the analogy back to the real mechanism.
- ACT IV: The Witty Reality Check / Punchline (28-36s): Dev has an "aha!" moment, and Claude drops a funny, sharp mic-drop punchline.

UNIVERSAL CONTEXTUAL VISUAL CONTRACT (MANDATORY):
For EVERY dialogue line, you MUST supply:
- "speaker": "dev" or "claude"
- "text": The spoken line.
- "visual_concept": The exact physical object, hardware part, machine, or concept for Wikipedia/Wikimedia search (e.g. "Binary_code", "Transistor", "Light_switch", "Integrated_circuit", "Roulette_wheel", "Casino", "Paper_shredder", "Black_hole").
- "badge": A clean 2 to 3 word concept pill label (e.g. "Binary Code", "Micro Switch", "Power Switch", "Microchip Gate", "Roulette Wheel", "Casino Floor").

CONSTRAINTS:
- 85 to 110 words total (target duration: 28 to 36 seconds).
- 4 to 6 alternating lines (starts with dev, ends with claude).
- Simple words, conversational, punchy, zero unexplained jargon.

OUTPUT FORMAT (JSON ONLY, NO PREAMBLE):
{
  "title": "Why computers use binary 1s and 0s",
  "hook": "Why don't computers just count from zero to ten like humans?",
  "dialogue": [
    {"speaker": "dev", "text": "Claude, if humans have ten fingers and count in base ten, why are computers obsessed with only ones and zeros?", "visual_concept": "Binary_code", "badge": "Binary Code"},
    {"speaker": "claude", "text": "Because computers aren't mathematicians. They are just billions of microscopic light switches called transistors.", "visual_concept": "Transistor", "badge": "Microscopic Switch"},
    {"speaker": "dev", "text": "Wait, so a one is just a switch turned on?", "visual_concept": "Light_switch", "badge": "Power Switch"},
    {"speaker": "claude", "text": "Exactly. Electricity is either flowing through the gate, which means one, or it's blocked, which means zero.", "visual_concept": "Integrated_circuit", "badge": "Microchip Gate"},
    {"speaker": "dev", "text": "Why couldn't they make ten different voltage levels for ten numbers?", "visual_concept": "Multimeter", "badge": "Voltage Levels"},
    {"speaker": "claude", "text": "Because electrical noise would turn your three into an eight and crash your game. Two states is bulletproof, Tony.", "visual_concept": "Central_processing_unit", "badge": "Processor Core"}
  ],
  "bgm_mood": "chill_lofi",
  "hashtags": ["#tech", "#computerscience", "#hardware", "#claude", "#coding", "#shorts"]
}
"""


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "_", text)[:40]


class DevClaudePipeline:
    """Master pipeline for Developer vs Claude shorts with Universal Contextual Visual Engine."""

    def __init__(self):
        self.api_key = config.openrouter_api_key
        self.model = config.openrouter_model or "openai/gpt-4o-mini"
        self.voice_engine = TTSEngine()
        self.transcriber = WhisperTranscriber()
        self.gameplay_manager = GameplayManager()
        self.card_engine = VisualCardEngine()
        self.concept_fetcher = ConceptImageFetcher()
        self.timeline_builder = OverlayTimelineBuilder(canvas_width=1080, canvas_height=1920)
        self.subtitle_builder = ASSSubtitleBuilder(
            font_size=62,
            margin_v=540,  # Positioned comfortably above bottom-left & bottom-right characters
            max_words_per_line=3,
        )

    def generate_dialogue(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Generate high-retention banter script with visual timeline via LLM."""
        user_prompt = "Write a viral 30-35s conversational short between a developer (Iron Man) and Claude 3.5 Sonnet with a 4 to 6 cut visual timeline."
        if topic and topic.strip():
            user_prompt += f" Premise: {topic.strip()}"
        else:
            sample_topics = [
                "What actually happens when you delete a file on your computer (table of contents analogy)",
                "What an API actually is (restaurant waiter analogy)",
                "Why RAM matters vs storage (desk workspace vs warehouse analogy)",
                "Why computers only understand 1s and 0s (billions of microscopic light switches)",
                "How Claude and AI actually think without memorizing answers (predicting the next puzzle piece)",
            ]
            user_prompt += f" Premise: {random.choice(sample_topics)}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/AI_Shorts",
            "X-Title": "AI Shorts Mode 2 Dev vs Claude",
            "Content-Type": "application/json",
        }

        model_queue = [self.model, "openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct"]
        parsed = None

        for m in model_queue:
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": DEV_CLAUDE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.72,
                "max_tokens": 2000,
            }
            try:
                res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
                if res.status_code == 200:
                    raw = res.json()["choices"][0]["message"]["content"]
                    cleaned = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
                    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE).strip()
                    parsed = json.loads(cleaned)
                    break
            except Exception:
                continue

        if not parsed or "dialogue" not in parsed:
            raise RuntimeError("Failed to generate dialogue script across all models.")

        return parsed

    def synthesize_conversation(
        self,
        dialogue: List[Dict[str, str]],
        temp_dir: Path,
        dev_voice: str = "en-US-ChristopherNeural",
        claude_voice: str = "en-GB-RyanNeural",
    ) -> Tuple[Path, List[Dict[str, Any]], float]:
        """Synthesize alternating neural voices and record exact turn boundaries."""
        import asyncio
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        temp_dir.mkdir(parents=True, exist_ok=True)
        turn_audio_paths = []
        turn_records = []
        current_time = 0.0

        print(f"[DevClaude/TTS] Synthesizing {len(dialogue)} dialogue turns...")

        for idx, turn in enumerate(dialogue):
            speaker = turn.get("speaker", "dev").lower()
            text = normalize_for_speech(turn.get("text", ""))
            v_name = claude_voice if "claude" in speaker else dev_voice

            turn_file = temp_dir / f"turn_{idx}_{speaker}.mp3"
            communicate = self.voice_engine._format_humanized_text(text)

            old_v = self.voice_engine.voice
            self.voice_engine.voice = v_name
            asyncio.run(self.voice_engine._synthesize_async(communicate, turn_file))
            self.voice_engine.voice = old_v

            turn_dur = self.voice_engine._get_audio_duration(turn_file)
            turn_audio_paths.append(turn_file)

            turn_records.append({
                "turn_index": idx,
                "speaker": speaker,
                "text": text,
                "start": round(current_time, 3),
                "end": round(current_time + turn_dur, 3),
                "duration": round(turn_dur, 3),
                "visual_concept": turn.get("visual_concept", ""),
                "badge": turn.get("badge", ""),
            })
            current_time += turn_dur + 0.10  # 100ms natural conversational breath

        concat_list_file = temp_dir / "concat_dialogue.txt"
        lines = [f"file '{str(p.resolve()).replace('\\', '/')}'" for p in turn_audio_paths]
        concat_list_file.write_text("\n".join(lines), encoding="utf-8")

        raw_master = temp_dir / "raw_conversation.mp3"
        master_voice = temp_dir / "master_conversation.mp3"

        cmd = [
            ffmpeg_exe, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(raw_master),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Apply studio mastering
        self.voice_engine._apply_studio_vocal_chain(raw_master, master_voice)
        total_duration = self.voice_engine._get_audio_duration(master_voice)

        print(f"[DevClaude/TTS] Conversation audio mastered: {total_duration:.2f}s")
        return master_voice, turn_records, total_duration

    def _find_phrase_start(self, trigger_phrase: str, word_data: List[WordTimestamp], fallback_time: float) -> float:
        """Find the exact start timestamp of a trigger phrase in Whisper word list."""
        clean_target_words = re.findall(r"\b\w+\b", trigger_phrase.lower())
        if not clean_target_words or not word_data:
            return fallback_time

        whisper_clean = [re.sub(r"[^\w]", "", w.word.lower()) for w in word_data]

        # 1. Exact phrase sequence search
        target_len = len(clean_target_words)
        for i in range(len(whisper_clean) - target_len + 1):
            if whisper_clean[i:i + target_len] == clean_target_words:
                return word_data[i].start

        # 2. Key word search (longest distinctive word in phrase)
        sorted_keys = sorted(clean_target_words, key=len, reverse=True)
        for key in sorted_keys:
            if len(key) >= 4:
                for i, w in enumerate(whisper_clean):
                    if key in w or w in key:
                        return word_data[i].start

        return fallback_time

    def assemble_short(
        self,
        gameplay_mp4: Path,
        master_voice: Path,
        turn_records: List[Dict[str, Any]],
        total_duration: float,
        output_mp4: Path,
        temp_dir: Path,
        visual_timeline: Optional[List[Dict[str, Any]]] = None,
        bgm_mood: str = "chill_lofi",
    ) -> Path:
        """Compose 1080x1920 video with gameplay, corner avatars, subtitles, and real-stock carousel."""
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        print(f"[DevClaude/Editor] Assembling Gameplay Master Short ({total_duration:.1f}s)...")

        # 1. Word alignment via Whisper
        word_data = self.transcriber.transcribe_words(master_voice)
        word_objs = [
            WordTimestamp(word=w.word, start=w.start, end=w.end)
            for w in word_data
        ]
        ass_path = temp_dir / "dialogue_subtitles.ass"
        self.subtitle_builder.margin_v = 620  # Positioned comfortably above enlarged bottom corner characters
        self.subtitle_builder.build_ass(word_objs, ass_path)
        safe_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")

        # 2. Source Frame Assets
        overlay_dev = Path("assets/characters/overlay_gameplay_dev.png").resolve()
        overlay_claude = Path("assets/characters/overlay_gameplay_claude.png").resolve()
        ding_wav = (config.sfx_dir / "ding.wav").resolve()
        thud_wav = (config.sfx_dir / "thud.wav").resolve()
        pop_wav = (config.sfx_dir / "pop.wav").resolve()

        # 3. Source BGM
        mood_folder = config.bgm_dir / bgm_mood
        bgm_candidates = list(mood_folder.glob("*.mp3")) if mood_folder.exists() else []
        if not bgm_candidates:
            bgm_candidates = list(config.bgm_dir.rglob("*.mp3"))
        chosen_bgm = random.choice(bgm_candidates) if bgm_candidates else None

        out_w, out_h = 1080, 1920
        fade_out_start = max(0.0, total_duration - 1.5)

        # 4. Prepare Dynamic Universal Contextual Visual Cards
        card_items = []
        has_turn_concepts = any(t.get("visual_concept") for t in turn_records)

        if has_turn_concepts:
            print(f"[DevClaude/UniversalVisuals] Sourcing contextual cards for {len(turn_records)} dialogue turns...")
            for idx, turn in enumerate(turn_records):
                concept = turn.get("visual_concept")
                if not concept:
                    continue
                badge = turn.get("badge") or concept.replace("_", " ").title()
                start_t = turn["start"]
                end_t = turn_records[idx + 1]["start"] if idx + 1 < len(turn_records) else min(total_duration - 0.4, start_t + 5.0)
                end_t = min(total_duration - 0.4, max(start_t + 2.0, end_t))

                if start_t >= total_duration - 1.0:
                    continue

                # Fetch image using Universal Concept Fetcher with MD5 disk cache
                img_path = self.concept_fetcher.fetch(concept)

                # Render enlarged, borderless, label-free visual with soft drop shadow
                card_png_path = temp_dir / f"visual_card_{idx}.png"
                self.card_engine.render_card(
                    image_input=img_path,
                    badge_text=badge,
                    output_png=card_png_path,
                    card_width=900,
                    card_height=620,
                    corner_radius=32,
                )

                card_items.append({
                    "index": idx,
                    "png_path": card_png_path,
                    "start": start_t,
                    "end": end_t,
                    "badge": badge,
                    "query": concept,
                })
                print(f"  * Turn #{idx+1} Visual: '{badge}' [{concept}] @ {start_t:.2f}s -> {end_t:.2f}s")
        elif visual_timeline:
            print(f"[DevClaude/Carousel] Sourcing encyclopedic cards from timeline ({len(visual_timeline)} cuts planned)...")
            item_starts = []
            for idx, item in enumerate(visual_timeline):
                trigger = item.get("trigger_phrase", "")
                fallback = 1.0 + (idx * (total_duration / max(1, len(visual_timeline))))
                start_t = self._find_phrase_start(trigger, word_objs, fallback)
                item_starts.append(start_t)

            for i in range(1, len(item_starts)):
                if item_starts[i] <= item_starts[i - 1]:
                    item_starts[i] = item_starts[i - 1] + 3.0

            for i, item in enumerate(visual_timeline):
                start_t = item_starts[i]
                end_t = item_starts[i + 1] if i + 1 < len(item_starts) else min(total_duration - 0.5, start_t + 5.0)
                end_t = min(total_duration - 0.5, max(start_t + 2.5, end_t))

                if start_t >= total_duration - 1.5:
                    continue

                badge = item.get("badge", "Concept")
                concept = item.get("concept_name") or item.get("search_keyword") or badge
                img_path = self.concept_fetcher.fetch(concept)

                card_png_path = temp_dir / f"visual_card_{i}.png"
                self.card_engine.render_card(
                    image_input=img_path,
                    badge_text=badge,
                    output_png=card_png_path,
                    card_width=900,
                    card_height=620,
                    corner_radius=32,
                )

                card_items.append({
                    "index": i,
                    "png_path": card_png_path,
                    "start": start_t,
                    "end": end_t,
                    "badge": badge,
                    "query": concept,
                })
                print(f"  * Cut #{i+1}: '{badge}' [{concept}] @ {start_t:.2f}s -> {end_t:.2f}s")

        # 5. Build Active Speaker Expressions
        dev_enables = []
        claude_enables = []
        for t in turn_records:
            if t["speaker"] == "claude":
                claude_enables.append(f"between(t,{t['start']:.3f},{t['end']:.3f})")
            else:
                dev_enables.append(f"between(t,{t['start']:.3f},{t['end']:.3f})")

        claude_expr = "+".join(claude_enables) if claude_enables else "0"
        dev_expr = "+".join(dev_enables) if dev_enables else "0"

        filter_chains = []

        # Scale & crop gameplay video to 1080x1920
        filter_chains.append(
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h}[v_gp]"
        )

        # Overlay active speaker layers over gameplay
        filter_chains.append(f"[v_gp][1:v]overlay=enable='{dev_expr}'[v_with_dev]")
        filter_chains.append(f"[v_with_dev][2:v]overlay=enable='{claude_expr}'[v_both]")
        curr_v = "v_both"

        # Overlay Enlarged Borderless Cards in Top-Middle (Centered horizontally X=(W-w)/2, Y=190, 900x620)
        card_start_input_idx = 4  # Inputs: 0=gp, 1=dev, 2=claude, 3=voice, 4+ = cards
        card_filters, curr_v = self.timeline_builder.build_video_chain(
            base_video_label=curr_v,
            cards=card_items,
            start_input_idx=card_start_input_idx,
            card_y=190,
        )
        filter_chains.extend(card_filters)

        # Attention-Reset Micro-Zoom on opening hook (0 to 2.8s)
        filter_chains.append(
            f"[{curr_v}]split=2[v_orig][v_hook];"
            f"[v_hook]scale=1134:2016,crop={out_w}:{out_h}[v_hook_crop];"
            f"[v_orig][v_hook_crop]overlay=enable='between(t,0,2.8)':shortest=1[v_zoomed]"
        )
        curr_v = "v_zoomed"

        # Glowing Bottom Progress Bar
        filter_chains.append(
            f"[{curr_v}]drawbox=x=0:y=1914:"
            f"w='min(1080,1080*t/{total_duration:.3f})':h=6:color=#38BDF8@0.95:t=fill[v_prog]"
        )
        curr_v = "v_prog"

        # Burn Dynamic Karaoke Subtitles
        filter_chains.append(f"[{curr_v}]subtitles='{safe_ass}'[v_sub]")
        curr_v = "v_sub"

        # 6. Build Audio Filtergraph
        cmd_inputs = [
            ffmpeg_exe, "-y",
            "-loglevel", "error",
            "-i", str(gameplay_mp4),                 # 0: Sliced gameplay video
            "-loop", "1", "-i", str(overlay_dev),    # 1: Dev active overlay
            "-loop", "1", "-i", str(overlay_claude), # 2: Claude active overlay
            "-i", str(master_voice),                 # 3: Master voice
        ]

        # Add visual cards to inputs
        for card in card_items:
            cmd_inputs.extend(["-loop", "1", "-i", str(card["png_path"])])

        next_input_idx = card_start_input_idx + len(card_items)

        # Voice highpass + sidechain trigger
        audio_filters = [
            "[3:a]highpass=f=80,asplit=2[vox_clean][vox_sc]"
        ]
        sfx_pads = []

        # Chime SFX at start of first Claude turn
        first_claude = next((t for t in turn_records if t["speaker"] == "claude"), None)
        if ding_wav.exists() and first_claude:
            cmd_inputs.extend(["-i", str(ding_wav)])
            ding_idx = next_input_idx
            next_input_idx += 1
            delay_ms = int(first_claude["start"] * 1000)
            audio_filters.append(f"[{ding_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.80[sfx_ding]")
            sfx_pads.append("[sfx_ding]")

        # Pop SFX synchronized with every image cut
        if pop_wav.exists() and card_items:
            sfx_in, sfx_fil, sfx_pads_cut = self.timeline_builder.build_audio_sfx_chain(
                cards=card_items,
                pop_sfx_path=pop_wav,
                start_input_idx=next_input_idx,
                volume=0.45,
            )
            cmd_inputs.extend(sfx_in)
            audio_filters.extend(sfx_fil)
            sfx_pads.extend(sfx_pads_cut)
            next_input_idx += len(card_items)

        # Punchline Thud SFX on final turn
        final_turn = turn_records[-1] if turn_records else None
        if thud_wav.exists() and final_turn:
            cmd_inputs.extend(["-i", str(thud_wav)])
            thud_idx = next_input_idx
            next_input_idx += 1
            delay_ms = int(final_turn["start"] * 1000)
            audio_filters.append(f"[{thud_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.85[sfx_thud]")
            sfx_pads.append("[sfx_thud]")

        # Ducked Studio BGM
        if chosen_bgm and chosen_bgm.exists():
            cmd_inputs.extend(["-stream_loop", "-1", "-i", str(chosen_bgm)])
            bgm_idx = next_input_idx
            next_input_idx += 1

            audio_filters.append(
                f"[{bgm_idx}:a]aloop=loop=-1:size=2e+09,"
                f"equalizer=f=2500:t=q:w=1.5:g=-5,"
                f"volume=0.28,"
                f"afade=t=in:ss=0:d=0.8,"
                f"afade=t=out:st={fade_out_start:.2f}:d=1.5[bgm_prepared]"
            )
            audio_filters.append(
                "[bgm_prepared][vox_sc]sidechaincompress="
                "threshold=0.10:ratio=2.5:attack=15:release=350[bgm_ducked]"
            )
            mix_inputs = ["[vox_clean]", "[bgm_ducked]"] + sfx_pads
            audio_filters.append(
                f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0[mixed]"
            )
            audio_filters.append("[mixed]loudnorm=I=-14:LRA=7:TP=-1.5[aout]")
        else:
            if sfx_pads:
                mix_inputs = ["[vox_clean]"] + sfx_pads
                audio_filters.append(
                    f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0[mixed]"
                )
                audio_filters.append("[mixed]loudnorm=I=-14:LRA=7:TP=-1.5[aout]")
            else:
                audio_filters.append("[vox_clean]loudnorm=I=-14:LRA=7:TP=-1.5[aout]")

        full_filtergraph = ";".join(filter_chains + audio_filters)

        cmd = cmd_inputs + [
            "-filter_complex", full_filtergraph,
            "-map", f"[{curr_v}]",
            "-map", "[aout]",
            "-t", f"{total_duration:.3f}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_mp4),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg render failed: {res.stderr}\nCommand: {' '.join(cmd)}")

        return output_mp4

    def run(self, topic: Optional[str] = None, gameplay_style: str = "random") -> Dict[str, Any]:
        """Execute end-to-end generation of Developer vs Claude short with Real-Stock Carousel."""
        session_id = int(time.time())
        temp_dir = config.temp_dir / f"dev_claude_{session_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        print("=" * 60)
        print("[START] AI Shorts Mode 2: Developer vs Claude (Real-Stock Carousel)")
        print("=" * 60)

        # 1. Generate Script with Visual Timeline
        script = self.generate_dialogue(topic)
        print(f"  * Title: {script['title']}")
        print(f"  * Hook: {script['hook']}")
        print(f"  * Turns: {len(script['dialogue'])}")
        print(f"  * Stock Cuts Planned: {len(script.get('visual_timeline', []))}")

        # 2. Synthesize Voices
        master_voice, turn_records, duration = self.synthesize_conversation(
            dialogue=script["dialogue"],
            temp_dir=temp_dir,
            dev_voice="en-US-ChristopherNeural",
            claude_voice="en-GB-RyanNeural",
        )

        # 3. Slicing Gameplay Video (Full-screen 1080x1920)
        print(f"[DevClaude/Gameplay] Slicing satisfying gameplay ({gameplay_style}) for {duration:.1f}s...")
        gameplay_slice = temp_dir / "gameplay_slice.mp4"
        self.gameplay_manager.get_gameplay_slice(
            target_duration=duration,
            output_mp4=gameplay_slice,
            style=gameplay_style,
            width=config.video_width,
            height=config.video_height,
        )

        # 4. Assemble Master Video with Encyclopedic Media Carousel
        slug = slugify(script["title"])
        output_mp4 = config.output_dir / f"dev_claude_encyclopedia_{slug}_{session_id}.mp4"
        output_meta = config.output_dir / f"dev_claude_encyclopedia_{slug}_{session_id}_metadata.txt"

        t0 = time.time()
        self.assemble_short(
            gameplay_mp4=gameplay_slice,
            master_voice=master_voice,
            turn_records=turn_records,
            total_duration=duration,
            output_mp4=output_mp4,
            temp_dir=temp_dir,
            visual_timeline=script.get("visual_timeline", []),
            bgm_mood=script.get("bgm_mood", "chill_lofi"),
        )
        render_time = time.time() - t0

        # 5. Save Social Metadata
        hashtags = " ".join(script.get("hashtags", ["#tech", "#claude", "#programming", "#educational", "#shorts"]))
        if any(t.get("visual_concept") for t in script.get("dialogue", [])):
            cuts_summary = "\n".join([
                f"- [{t.get('badge', 'Concept')}]: {t.get('visual_concept', '')} (Speaker: {t.get('speaker', '')})"
                for t in script.get("dialogue", []) if t.get("visual_concept")
            ])
        else:
            cuts_summary = "\n".join([
                f"- [{c.get('badge', '')}]: {c.get('concept_name', '') or c.get('search_keyword', '')} (Trigger: '{c.get('trigger_phrase', '')}')"
                for c in script.get("visual_timeline", [])
            ])
        meta_content = f"""=== YOUTUBE SHORTS / INSTAGRAM REELS / TIKTOK METADATA ===

TITLE:
{script['title']}

HOOK:
"{script['hook']}"

ENCYCLOPEDIC MEDIA CUTS (Wikipedia / Wikimedia):
{cuts_summary}

DESCRIPTION:
{script['title']}
Did you know this before? Drop your thoughts below! 👇

HASHTAGS:
{hashtags}

PINNED COMMENT:
Did you know how this actually worked? Drop a 🔥 if this blew your mind! 👇
"""
        output_meta.write_text(meta_content, encoding="utf-8")

        print("\n" + "=" * 60)
        print(f"[SUCCESS] Developer vs Claude Short with Real-Stock Carousel rendered in {render_time:.1f}s!")
        print(f"  * Master Video: {output_mp4}")
        print(f"  * Metadata: {output_meta}")
        print("=" * 60)

        return {
            "title": script["title"],
            "video_path": output_mp4,
            "metadata_path": output_meta,
            "duration": round(duration, 2),
            "render_time": round(render_time, 1),
            "turns": turn_records,
            "visual_timeline": script.get("visual_timeline", []),
        }
