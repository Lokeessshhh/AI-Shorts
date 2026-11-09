import asyncio
import os
import re
import time
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import edge_tts
from ..config import config


@dataclass
class TTSResult:
    audio_path: Path
    duration_seconds: float
    voice_name: str


class TTSEngine:
    """
    Production-grade Bilingual TTS Engine (English & Hindi).
    Powered by Microsoft Edge Neural TTS with zero API keys, zero trials, and unlimited generation.
    Features:
    - Native Indian Hindi Male Voice: 'hi-IN-MadhurNeural' (Warm, conversational Indian Hindi)
    - Native Indian Hindi Female Voice: 'hi-IN-SwaraNeural' (Clear, expressive)
    - Global English Voice: 'en-US-ChristopherNeural' / 'en-US-AndrewNeural'
    - Studio vocal chain mastering: highpass, warmth, presence, compression, and EBU R128 loudness.
    - Per-scene physical audio synthesis with sample-accurate timeline alignment.
    """

    HINDI_MALE_VOICE = "hi-IN-MadhurNeural"
    HINDI_FEMALE_VOICE = "hi-IN-SwaraNeural"
    ENGLISH_MALE_VOICE = "en-US-ChristopherNeural"
    ENGLISH_FEMALE_VOICE = "en-US-AvaNeural"

    def __init__(self, voice: Optional[str] = None, language: str = "en"):
        self.language = "hi" if language in ("hi", "hindi") else "en"
        if voice:
            self.voice = voice
        else:
            self.voice = self.HINDI_MALE_VOICE if self.language == "hi" else config.default_voice

    async def _synthesize_async(
        self, text: str, output_path: Path, rate: str = "+0%", pitch: str = "+0Hz"
    ) -> None:
        """Async generation using edge-tts with timeout, language-aware fallback and robust retry."""
        if self.voice.startswith("hi-") or self.language == "hi":
            candidate_voices = [self.voice, self.HINDI_MALE_VOICE, self.HINDI_FEMALE_VOICE]
        else:
            candidate_voices = [self.voice, "en-US-GuyNeural", "en-US-AndrewNeural", "en-US-BrianNeural"]

        last_err = None
        for attempt in range(4):
            voice_to_use = candidate_voices[attempt % len(candidate_voices)]
            try:
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except Exception:
                        pass
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice_to_use,
                    rate=rate,
                    pitch=pitch,
                )
                await asyncio.wait_for(communicate.save(str(output_path)), timeout=35.0)
                if output_path.exists() and output_path.stat().st_size > 500:
                    return
            except Exception as e:
                last_err = e
                await asyncio.sleep(2.0 * (attempt + 1))
        raise RuntimeError(f"EdgeTTS failed after 4 attempts: {last_err}")

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Extract exact audio duration using av or ffprobe / ffmpeg."""
        try:
            import av
            with av.open(str(audio_path)) as container:
                stream = container.streams.audio[0]
                if stream.duration is not None and stream.time_base is not None:
                    return float(stream.duration * stream.time_base)
                if container.duration is not None:
                    return float(container.duration / av.time.AV_TIME_BASE)
        except Exception:
            pass

        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            res = subprocess.run(
                [ffmpeg_exe, "-i", str(audio_path)],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            for line in res.stderr.splitlines():
                if "Duration:" in line:
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = time_str.split(":")
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except Exception:
            pass

        return 28.0

    def _format_humanized_text(self, text: str, language: str = "en") -> str:
        """
        Clean and format narration text for fluid, natural neural TTS speech.
        Avoids long awkward gaps by converting heavy paragraph breaks into natural commas,
        and preserving expressive question marks and exclamation inflections.
        """
        cleaned = text.strip()
        cleaned = re.sub(r"[*_~`]", "", cleaned)
        cleaned = re.sub(r"[\t ]+", " ", cleaned)
        cleaned = re.sub(r"-{2,}", ", ", cleaned)
        cleaned = cleaned.replace("—", ", ")

        if language in ("hi", "hindi"):
            # In Hindi neural TTS, purna virams (।) or periods (.) cause an extreme 1.45s pause.
            # Convert internal sentence breaks to commas for conversational speech flow,
            # keeping trailing viram or question marks clean.
            cleaned = re.sub(r"[।\.]\s+", ", ", cleaned)
            cleaned = re.sub(r"[।\.]+$", "", cleaned).strip()
        else:
            # In English, periods cause a ~1.0s pause.
            # Convert internal periods into a natural comma pause (~250ms)
            cleaned = re.sub(r"\.\s+", ", ", cleaned)
            cleaned = re.sub(r"\.+$", "", cleaned).strip()

        return cleaned

    def _trim_audio_silence(self, input_path: Path, output_path: Path) -> float:
        """
        Trim leading and trailing digital silence from TTS segment down to audible phonemes
        using bidirectional peak silence removal.
        Returns the trimmed audio duration in seconds.
        """
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        trim_filter = (
            "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-38dB:detection=peak,"
            "areverse,"
            "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-38dB:detection=peak,"
            "areverse"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(input_path),
            "-af", trim_filter,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            dur = self._get_audio_duration(output_path)
            # Safety check: if silence removal overclipped or file is empty, fallback to input
            if dur < 0.2:
                shutil.copy2(str(input_path), str(output_path))
                dur = self._get_audio_duration(output_path)
            return dur
        except Exception:
            shutil.copy2(str(input_path), str(output_path))
            return self._get_audio_duration(output_path)

    def _generate_silence_pad(self, pad_path: Path, duration: float) -> Path:
        """Generate a procedural sample-accurate silence pad for natural human pauses."""
        if pad_path.exists() and abs(self._get_audio_duration(pad_path) - duration) < 0.03:
            return pad_path
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=24000:cl=mono",
            "-t", f"{duration:.3f}",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(pad_path),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return pad_path

    def _calculate_scene_pause(self, scene: Any, is_last_scene: bool, language: str = "en") -> float:
        """
        Dynamically determine contextual breathing pause between spoken sentences:
        - Last scene (outro): 0.0s (seamless infinite loop).
        - Question hook or opening cut ('?'): ~180-200ms.
        - Climax, dramatic punchline, or diagram transition ('!', graphic_card): ~220-240ms.
        - Standard sentence continuation: ~130-150ms.
        """
        if is_last_scene:
            return 0.0

        narr = getattr(scene, "narration", "").strip()
        sc_id = getattr(scene, "scene_id", 1)
        v_type = getattr(scene, "visual_type", "video")

        if narr.endswith("?") or sc_id == 1:
            return 0.20

        if narr.endswith("!") or v_type == "graphic_card":
            return 0.22

        return 0.14

    def _apply_studio_vocal_chain(self, input_path: Path, output_path: Path) -> Path:
        """Apply high-end podcast vocal mastering (highpass, vocal presence, warmth, broadcast compression, and EBU R128 loudnorm)."""
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        vocal_filter = (
            "highpass=f=80,"
            "equalizer=f=250:t=q:w=1.0:g=1.5,"
            "equalizer=f=3500:t=q:w=1.2:g=2.5,"
            "acompressor=threshold=-18dB:ratio=2.8:attack=10:release=120:makeup=2.5,"
            "loudnorm=I=-16:TP=-1.5:LRA=7"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(input_path),
            "-af", vocal_filter,
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path

    @staticmethod
    def _safe_replace(src: Path, dst: Path):
        """Safely move/replace a file on Windows handling lingering file handles."""
        import shutil
        for attempt in range(10):
            try:
                if dst.exists():
                    dst.unlink(missing_ok=True)
                shutil.move(str(src), str(dst))
                return
            except Exception:
                time.sleep(0.15)
        try:
            import shutil
            shutil.copy2(str(src), str(dst))
            src.unlink(missing_ok=True)
        except Exception:
            pass

    def synthesize(
        self,
        text: str,
        output_filename: str = "voiceover.mp3",
        target_duration: Optional[float] = 28.0,
        apply_studio_mastering: bool = True,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        language: str = "en",
    ) -> TTSResult:
        """Synchronous wrapper to synthesize voice, conform to target duration, and apply studio mastering."""
        if language in ("hi", "hindi"):
            self.language = "hi"
            if not self.voice.startswith("hi-"):
                self.voice = self.HINDI_MALE_VOICE
        else:
            self.language = "en"
            if self.voice.startswith("hi-"):
                self.voice = config.default_voice

        output_path = config.temp_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        humanized_text = self._format_humanized_text(text, language=self.language)
        asyncio.run(self._synthesize_async(humanized_text, output_path, rate=rate, pitch=pitch))
        
        # Strip digital dead air
        trimmed_single = output_path.with_name(f"trimmed_{output_path.name}")
        self._trim_audio_silence(output_path, trimmed_single)
        if trimmed_single.exists():
            self._safe_replace(trimmed_single, output_path)
        duration = self._get_audio_duration(output_path)

        if target_duration is not None and duration > 0:
            ideal_target = max(10.0, target_duration - 0.5)
            if duration > target_duration or duration < (target_duration - 2.5):
                speed_ratio = duration / ideal_target
                rate_pct = int(round((speed_ratio - 1.0) * 100))
                rate_pct = max(-15, min(30, rate_pct))
                if rate_pct != 0:
                    adjusted_rate = f"{rate_pct:+d}%"
                    asyncio.run(self._synthesize_async(humanized_text, output_path, rate=adjusted_rate, pitch=pitch))
                    duration = self._get_audio_duration(output_path)

            if duration > target_duration:
                tempo = duration / target_duration
                conformed_path = output_path.with_name(f"conformed_{output_path.name}")
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                subprocess.run(
                    [
                        ffmpeg_exe, "-y",
                        "-i", str(output_path),
                        "-filter:a", f"atempo={tempo:.4f}",
                        "-c:a", "libmp3lame",
                        str(conformed_path),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                if conformed_path.exists():
                    self._safe_replace(conformed_path, output_path)
                    duration = self._get_audio_duration(output_path)

        if apply_studio_mastering and output_path.exists():
            studio_path = output_path.with_name(f"studio_{output_path.name}")
            self._apply_studio_vocal_chain(output_path, studio_path)
            if studio_path.exists():
                self._safe_replace(studio_path, output_path)
                duration = self._get_audio_duration(output_path)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            voice_name=self.voice,
        )

    def synthesize_scenes(
        self,
        scenes: list,
        output_filename: str = "voiceover_scenes.mp3",
        language: str = "en",
        target_duration: Optional[float] = 27.5,
        apply_studio_mastering: bool = True,
    ) -> Tuple[TTSResult, List[Dict[str, Any]]]:
        """
        Synthesize voiceover scene-by-scene for sample-accurate acoustic alignment.
        Eliminates Whisper dependency and guarantees millisecond-accurate sync between
        audio boundaries, visual cuts, and kinetic subtitles.
        """
        lang = "hi" if language in ("hi", "hindi") else "en"
        self.language = lang
        if lang == "hi" and not self.voice.startswith("hi-"):
            self.voice = self.HINDI_MALE_VOICE
        elif lang == "en" and self.voice.startswith("hi-"):
            self.voice = config.default_voice

        output_path = config.temp_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        seg_dir = output_path.parent / "scene_audio_parts"
        seg_dir.mkdir(parents=True, exist_ok=True)

        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        scene_timelines: List[Dict[str, Any]] = []
        concat_lines: List[str] = []
        cum_time = 0.0

        for idx, scene in enumerate(scenes):
            narr_text = getattr(scene, "narration", "").strip()
            if not narr_text:
                continue

            scene_id = getattr(scene, "scene_id", idx + 1)
            raw_seg_path = seg_dir / f"scene_{scene_id}_{lang}_raw.mp3"
            trimmed_seg_path = seg_dir / f"scene_{scene_id}_{lang}.mp3"
            human_text = self._format_humanized_text(narr_text, language=lang)

            asyncio.run(self._synthesize_async(human_text, raw_seg_path))
            dur = self._trim_audio_silence(raw_seg_path, trimmed_seg_path)

            is_last = (idx == len(scenes) - 1)
            pause_dur = self._calculate_scene_pause(scene, is_last_scene=is_last, language=lang)

            safe_trimmed_path = str(trimmed_seg_path.resolve()).replace("\\", "/")
            concat_lines.append(f"file '{safe_trimmed_path}'")

            if pause_dur > 0.02 and not is_last:
                pad_path = seg_dir / f"pad_{scene_id}_{int(pause_dur * 1000)}ms.mp3"
                self._generate_silence_pad(pad_path, pause_dur)
                safe_pad_path = str(pad_path.resolve()).replace("\\", "/")
                concat_lines.append(f"file '{safe_pad_path}'")
                actual_pause = pause_dur
            else:
                actual_pause = 0.0

            scene_dur = dur + actual_pause
            scene_timelines.append({
                "scene_id": scene_id,
                "start_time": round(cum_time, 2),
                "end_time": round(cum_time + scene_dur, 2),
                "duration": round(scene_dur, 2),
                "speech_duration": round(dur, 2),
                "pause_duration": round(actual_pause, 2),
                "speech_start": round(cum_time, 2),
                "speech_end": round(cum_time + dur, 2),
                "narration": narr_text,
            })
            cum_time += scene_dur

        if not concat_lines:
            raise RuntimeError("No scene voice clips were synthesized.")

        concat_file = seg_dir / "scene_concat_list.txt"
        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

        raw_concat = output_path.with_name(f"raw_{output_path.name}")
        cmd = [
            ffmpeg_exe, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(raw_concat),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        tot_duration = self._get_audio_duration(raw_concat)

        # Conform duration if requested
        scale_factor = 1.0
        if target_duration is not None and tot_duration > target_duration:
            tempo = tot_duration / target_duration
            conformed_path = output_path.with_name(f"conformed_{output_path.name}")
            subprocess.run(
                [
                    ffmpeg_exe, "-y",
                    "-i", str(raw_concat),
                    "-filter:a", f"atempo={tempo:.4f}",
                    "-c:a", "libmp3lame",
                    str(conformed_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            if conformed_path.exists():
                self._safe_replace(conformed_path, raw_concat)
                new_tot = self._get_audio_duration(raw_concat)
                scale_factor = new_tot / max(0.1, tot_duration)
                tot_duration = new_tot

                # Scale scene timeline boundaries proportionally
                for st in scene_timelines:
                    st["start_time"] = round(st["start_time"] * scale_factor, 2)
                    st["end_time"] = round(st["end_time"] * scale_factor, 2)
                    st["duration"] = round(st["duration"] * scale_factor, 2)
                    st["speech_duration"] = round(st.get("speech_duration", st["duration"]) * scale_factor, 2)
                    st["pause_duration"] = round(st.get("pause_duration", 0.0) * scale_factor, 2)
                    st["speech_start"] = round(st.get("speech_start", st["start_time"]) * scale_factor, 2)
                    st["speech_end"] = round(st.get("speech_end", st["end_time"]) * scale_factor, 2)

        # Apply studio podcast mastering
        if apply_studio_mastering and raw_concat.exists():
            self._apply_studio_vocal_chain(raw_concat, output_path)
            if not output_path.exists():
                self._safe_replace(raw_concat, output_path)
        else:
            self._safe_replace(raw_concat, output_path)

        tot_duration = self._get_audio_duration(output_path)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=tot_duration,
            voice_name=self.voice,
        ), scene_timelines
