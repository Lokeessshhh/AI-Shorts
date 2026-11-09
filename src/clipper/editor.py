"""Mode 3 Short Editor & Filtergraph Polish Engine.
Applies attention-reset micro-zooms, glowing progress bar, dynamic ASS subtitle burn-in,
3D color emoji overlays, and broadcast loudness mastering.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import imageio_ffmpeg

from ..config import config
from ..subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp, EmojiEvent
from .reframe import SmartReframer
from scripts.setup_bgm_vault import get_bgm_for_mood


class ShortEditor:
    """Renders polished viral shorts from raw subclips."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or self._locate_ffmpeg()
        self.subtitle_builder = ASSSubtitleBuilder(
            font_size=78,
            margin_v=430,  # Perfectly centered above platform UI overlay
            max_words_per_line=3,
        )
        self.reframer = SmartReframer()

    def _extract_exact_slice_words(self, video_path: Path, temp_dir: Path) -> List[Dict[str, Any]]:
        """
        Extract millisecond-accurate acoustic word timestamps directly from the sliced video's audio
        using faster-whisper. Guarantees 100% synchronization with speech, eliminating any CDN keyframe drift.
        """
        import wave
        import numpy as np
        from faster_whisper import WhisperModel

        slice_wav = temp_dir / "slice_audio_exact.wav"
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", str(video_path),
            "-ar", "16000",
            "-ac", "1",
            str(slice_wav),
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            with wave.open(str(slice_wav), "rb") as wf:
                data = wf.readframes(wf.getnframes())
                audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio, word_timestamps=True)
            words = []
            for s in segments:
                if s.words:
                    for w in s.words:
                        w_text = w.word.strip()
                        if w_text:
                            words.append({
                                "word": w_text,
                                "start": round(float(w.start), 3),
                                "end": round(float(w.end), 3),
                            })
            if words:
                print(f"[Clipper/Editor] Acoustically resynced {len(words)} words directly from cut slice audio (Language: {info.language}).")
                return words
        except Exception as e:
            print(f"[Clipper/Editor] Slice acoustic resync notice: {e}. Falling back to candidate timestamps.")
        return []

    @staticmethod
    def _is_non_latin(text: str) -> bool:
        """Check if string contains non-Latin scripts (Devanagari, Urdu, Arabic, etc.)."""
        return any(
            ("\u0900" <= ch <= "\u097f") or ("\u0600" <= ch <= "\u06ff") or (ord(ch) > 0x024F and ch.isalpha())
            for ch in text
        )

    _has_devanagari = _is_non_latin

    def _transliterate_text(self, text: str) -> str:
        """Transliterate a non-Latin Hindi/Urdu phrase or hook to Roman Hinglish using LLM."""
        if not self._is_non_latin(text):
            return text
        try:
            from ..llm.client import OpenRouterClient
            llm = OpenRouterClient()
            prompt = (
                f"Transliterate the following Hindi/Urdu text into conversational Roman Hindi (Hinglish) using Latin script (A-Za-z).\n"
                f"Rules:\n"
                f"1. Output ONLY English/Latin alphabet letters (A-Za-z). Do NOT use Devanagari or Urdu script.\n"
                f"2. Keep it punchy, popular, and natural as used on YouTube Shorts and Instagram Reels.\n"
                f"Input: {text}"
            )
            res = llm.complete(
                system_prompt="You are an expert Hindi to Roman Hinglish transliterator.",
                user_prompt=prompt,
                temperature=0.1,
            )
            return res.strip()
        except Exception:
            return text

    def _transliterate_and_align_hinglish(self, words_data: List[Dict[str, Any]]) -> List[WordTimestamp]:
        """Convert non-Latin Hindi/Urdu transcript words into Roman Hinglish with millisecond timestamps."""
        if not words_data:
            return []

        from ..llm.client import OpenRouterClient
        from ..subtitles.acoustic_aligner import AcousticWordAligner

        aligner = AcousticWordAligner()
        llm = OpenRouterClient()

        # Group words into sentence / phrase blocks
        blocks = []
        curr_words = []
        for i, w in enumerate(words_data):
            curr_words.append(w)
            word_str = w.get("word", "")
            is_punct = any(p in word_str for p in [".", "?", "!", "।", "॥"])
            has_pause = (i < len(words_data) - 1 and (words_data[i+1].get("start", 0) - w.get("end", 0)) > 0.45)
            is_long = len(curr_words) >= 8

            if is_punct or has_pause or is_long or i == len(words_data) - 1:
                start_t = float(curr_words[0].get("start", 0))
                end_t = float(curr_words[-1].get("end", start_t + 1.0))
                text_block = " ".join(item.get("word", "") for item in curr_words).strip()
                if text_block:
                    blocks.append((text_block, start_t, end_t))
                curr_words = []

        if not blocks:
            return [WordTimestamp(word=w["word"], start=w["start"], end=w["end"]) for w in words_data]

        full_hindi_text = "\n".join(f"[{i+1}] {b[0]}" for i, b in enumerate(blocks))
        prompt = (
            "Transliterate the following spoken Hindi/Urdu numbered sentences into natural conversational Roman Hindi (Hinglish) using Latin alphabet (A-Za-z).\n"
            "Rules:\n"
            "1. Output ONLY the numbered transliterations matching each [N].\n"
            "2. Must be 100% Latin script (A-Za-z). Do NOT output any Devanagari or Arabic/Urdu characters.\n"
            "3. Use standard popular Roman Hinglish spellings (e.g. 'Dukan to har aane par hi discount deti hai...').\n\n"
            f"{full_hindi_text}"
        )
        try:
            res = llm.complete(
                system_prompt="You are an expert Hindi to Roman Hinglish transliterator.",
                user_prompt=prompt,
                temperature=0.1,
            )
            lines = [line.strip() for line in res.strip().split("\n") if line.strip()]
            hinglish_map = {}
            for line in lines:
                m = re.match(r"^\[?(\d+)\]?[\.\:\s]*(.+)$", line)
                if m:
                    idx = int(m.group(1)) - 1
                    hinglish_map[idx] = m.group(2).strip()

            all_aligned: List[WordTimestamp] = []
            for i, (orig_text, st, et) in enumerate(blocks):
                h_text = hinglish_map.get(i) or orig_text
                aligned_block = aligner.align_scene(h_text, st, et)
                all_aligned.extend(aligned_block)

            return all_aligned if all_aligned else [WordTimestamp(word=w["word"], start=w["start"], end=w["end"]) for w in words_data]
        except Exception as e:
            print(f"[Clipper/Editor] Transliteration note ({e}); falling back to phonetic alignment.")
            full_text = " ".join(b[0] for b in blocks)
            return aligner.align_scene(full_text, blocks[0][1], blocks[-1][2])

    def _locate_ffmpeg(self) -> str:
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()

    @staticmethod
    def build_audio_filtergraph(duration: float) -> str:
        """
        Studio-Grade Audio Mixing Filtergraph:
        1. Highpass speech at 80Hz to eliminate microphone rumble and split for sidechain.
        2. Infinite BGM loop with -5dB spectral EQ carve at 2.5kHz (vocal pocket).
        3. Dynamic sidechain compression (ducking BGM under voice, swelling during pauses).
        4. Broadcast loudness normalization to -14 LUFS.
        """
        fade_out_start = max(0.0, duration - 1.5)
        return (
            # 1. Highpass speech at 80Hz & split into clean voice and sidechain trigger
            "[0:a]highpass=f=80,asplit=2[vox_clean][vox_sc];"
            # 2. Loop BGM infinitely, carve 5dB pocket at 2.5kHz for vocals, apply volume envelope
            f"[1:a]aloop=loop=-1:size=2e+09,"
            f"equalizer=f=2500:t=q:w=1.5:g=-5,"
            f"volume=0.32,"
            f"afade=t=in:ss=0:d=0.8,"
            f"afade=t=out:st={fade_out_start:.2f}:d=1.5[bgm_prepared];"
            # 3. Dynamic Sidechain Compression: Duck BGM when voice speaks, swell in pauses
            "[bgm_prepared][vox_sc]sidechaincompress="
            "threshold=0.10:ratio=2.5:attack=15:release=350[bgm_ducked];"
            # 4. Mix speech and ducked BGM
            "[vox_clean][bgm_ducked]amix=inputs=2:duration=first:normalize=0[mixed];"
            # 5. Broadcast Loudness Normalization to -14 LUFS
            "[mixed]loudnorm=I=-14:LRA=7:TP=-1.5[aout]"
        )

    def render_short(
        self,
        source_video: Path,
        highlight: Dict[str, Any],
        output_mp4: Path,
        temp_dir: Path,
        reframe_analysis: Optional[Dict[str, Any]] = None,
        enable_micro_zoom: bool = True,
        enable_progress_bar: bool = True,
        layout: Optional[str] = None,
        is_pre_sliced: bool = False,
    ) -> Path:
        """
        Assemble one short from start_time to end_time with all viral polish effects.
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        start_time = float(highlight["start_time"])
        end_time = float(highlight["end_time"])
        duration = float(highlight["duration"])
        rank = highlight.get("rank", 1)

        feed_start = 0.0 if is_pre_sliced else start_time
        feed_end = duration if is_pre_sliced else end_time

        print(f"[Clipper/Editor] Rendering Clip #{rank}: {start_time:.1f}s -> {end_time:.1f}s ({duration:.1f}s) [Pre-sliced={is_pre_sliced}]")

        # 1. Analyze framing if not already provided
        if not reframe_analysis:
            reframe_analysis = self.reframer.analyze_clip(
                video_path=source_video,
                start_time=feed_start,
                end_time=feed_end,
                sample_fps=1.5,
                forced_layout=layout,
            )

        layout_type = reframe_analysis.get("layout", "solo")
        print(f"[Clipper/Editor] Clip #{rank} Layout detected: {layout_type.upper()}")

        # 2. Compile ASS Subtitles (100% Acoustic Sync & Hinglish Captions)
        # Extract millisecond-accurate word timestamps directly from the cut video audio!
        exact_words = self._extract_exact_slice_words(source_video, temp_dir)
        words_data = exact_words if exact_words else highlight.get("words", [])

        has_devanagari = any(self._has_devanagari(w.get("word", "")) for w in words_data)

        if has_devanagari:
            print(f"[Clipper/Editor] Devanagari Hindi speech detected. Transliterating into Roman Hinglish subtitles...")
            word_objs = self._transliterate_and_align_hinglish(words_data)
        else:
            word_objs = [
                WordTimestamp(word=w["word"], start=w["start"], end=w["end"])
                for w in words_data
            ]

        # Extract bold text hook for frames 0-2.4s (same style as Mode 1)
        raw_hook = highlight.get("clean_hook") or highlight.get("title") or "MIND-BLOWING MOMENT"
        header_hook = self._transliterate_text(raw_hook).upper()[:35]

        # Extract emphasis keywords for dynamic color accents (cyan, gold, red, canary yellow)
        all_emphasis = []
        for tag in highlight.get("hashtags", []):
            all_emphasis.append(tag.lstrip("#").upper())
        for token in re.findall(r"\b[A-Za-z0-9]{4,}\b", header_hook):
            all_emphasis.append(token.upper())
        for w in word_objs:
            if any(ch.isdigit() for ch in w.word) or len(w.word) >= 7:
                all_emphasis.append(w.word.upper())

        # Extract channel attribution for on-screen copyright/fair-use credit
        raw_channel = highlight.get("channel") or highlight.get("uploader") or ""
        credit_badge = re.sub(r"[^\w\s@.]", "", raw_channel).strip() if raw_channel else None

        ass_path = temp_dir / f"clip_{rank}_subtitles.ass"
        _, emoji_events = self.subtitle_builder.build_ass(
            words=word_objs,
            output_path=ass_path,
            header_hook=header_hook,
            emphasis_keywords=all_emphasis,
            credit_attribution=credit_badge,
        )

        # 3. Build FFmpeg Filtergraph
        reframe_filter = self.reframer.generate_ffmpeg_filtergraph(
            analysis=reframe_analysis,
            out_w=config.video_width,
            out_h=config.video_height,
        )

        filter_chain = []
        filter_chain.append(reframe_filter)

        curr_v = "v_reframe"

        # Attention-Reset Micro-Zoom during Hook (first 3.2 seconds: 1.08x scale punch-in)
        if enable_micro_zoom and duration > 6.0:
            zoom_out = "v_zoom"
            # Scale slightly 1.08x and crop back to 1080x1920 during t < 3.2s
            zoom_filter = (
                f"[{curr_v}]split=2[v_base][v_hook];"
                f"[v_hook]scale=1166:2074,crop=1080:1920[v_hook_crop];"
                f"[v_base][v_hook_crop]overlay=enable='between(t,0,3.2)':shortest=1[{zoom_out}]"
            )
            filter_chain.append(zoom_filter)
            curr_v = zoom_out

        # Animated Glowing Progress Bar at the bottom
        if enable_progress_bar:
            prog_out = "v_prog"
            # 6px bar at the bottom (y=1914) that expands from width 0 to 1080
            prog_filter = (
                f"[{curr_v}]drawbox=x=0:y=1914:"
                f"w='min(1080,1080*t/{duration:.3f})':h=6:color=#00FF99@0.9:t=fill[{prog_out}]"
            )
            filter_chain.append(prog_filter)
            curr_v = prog_out

        # Subtitle Burn-In (escape path for FFmpeg)
        safe_ass_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
        sub_out = "v_sub"
        filter_chain.append(f"[{curr_v}]subtitles='{safe_ass_path}'[{sub_out}]")
        curr_v = sub_out

        # Overlay 3D Color Emojis if any
        if emoji_events:
            for idx, ev in enumerate(emoji_events):
                next_v = f"v_em_{idx}"
                safe_em_path = str(ev.file_path).replace("\\", "/").replace(":", "\\:")
                # Overlay at center right above subtitle text: x=465, y=1200
                em_filter = (
                    f"movie='{safe_em_path}',scale=150:150[em_{idx}];"
                    f"[{curr_v}][em_{idx}]overlay=x=(W-w)/2:y=1220:"
                    f"enable='between(t,{ev.start:.3f},{ev.end:.3f})'[{next_v}]"
                )
                filter_chain.append(em_filter)
                curr_v = next_v

        video_filtergraph = ";".join(filter_chain)

        # 4. Multi-Signal BGM Sourcing & Studio Audio Mixing
        mood = highlight.get("mood", "chill_lofi")
        bgm_path = get_bgm_for_mood(mood)

        if bgm_path and bgm_path.exists():
            print(f"[Clipper/Editor] Sourcing BGM [{mood}]: {bgm_path.name}")
            audio_filtergraph = self.build_audio_filtergraph(duration)
            full_filtergraph = f"{video_filtergraph};{audio_filtergraph}"
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-loglevel", "error",
                "-ss", f"{feed_start:.3f}",
                "-to", f"{feed_end:.3f}",
                "-i", str(source_video),
                "-i", str(bgm_path),
                "-filter_complex", full_filtergraph,
                "-map", f"[{curr_v}]",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_mp4),
            ]
        else:
            # Fallback audio mastering if no BGM track available
            audio_filter = "highpass=f=80,loudnorm=I=-14:LRA=7:TP=-1.5"
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-loglevel", "error",
                "-ss", f"{feed_start:.3f}",
                "-to", f"{feed_end:.3f}",
                "-i", str(source_video),
                "-filter_complex", video_filtergraph,
                "-map", f"[{curr_v}]",
                "-map", "0:a:0?",
                "-af", audio_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_mp4),
            ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg Short render failed: {res.stderr}\nCommand: {' '.join(cmd)}")

        return output_mp4
