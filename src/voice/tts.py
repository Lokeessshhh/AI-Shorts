import asyncio
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import edge_tts
from ..config import config


@dataclass
class TTSResult:
    audio_path: Path
    duration_seconds: float
    voice_name: str


class TTSEngine:
    def __init__(self, voice: Optional[str] = None):
        self.voice = voice or config.default_voice

    async def _synthesize_async(
        self, text: str, output_path: Path, rate: str = "+0%", pitch: str = "+0Hz"
    ) -> None:
        """Async generation using edge-tts with timeout and retry."""
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate=rate,
                    pitch=pitch,
                )
                await asyncio.wait_for(communicate.save(str(output_path)), timeout=25.0)
                if output_path.exists() and output_path.stat().st_size > 1000:
                    return
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"EdgeTTS failed after 3 attempts: {e}")
                await asyncio.sleep(1.0)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Extract exact audio duration using av or ffprobe / ffmpeg."""
        try:
            import av
            with av.open(str(audio_path)) as container:
                stream = container.streams.audio[0]
                if stream.duration is not None and stream.time_base is not None:
                    return float(stream.duration * stream.time_base)
                # Fallback to container duration
                if container.duration is not None:
                    return float(container.duration / av.time.AV_TIME_BASE)
        except Exception:
            pass

        # Fallback to imageio_ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            # Run ffmpeg -i audio_path to read duration
            res = subprocess.run(
                [ffmpeg_exe, "-i", str(audio_path)],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            for line in res.stderr.splitlines():
                if "Duration:" in line:
                    # e.g., Duration: 00:00:35.42, start: ...
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = time_str.split(":")
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except Exception:
            pass

        # Rough estimate if all else fails (avg 150 words per minute = 2.5 words/sec)
        return 30.0

    def _format_humanized_text(self, text: str) -> str:
        """Clean and enhance text rhythm with natural pauses for conversational neural TTS."""
        cleaned = text.strip()
        # Convert double dashes to em-dashes for natural breath pauses
        cleaned = cleaned.replace("--", " — ")
        # Add subtle pause after the opening hook if not already punctuated
        parts = cleaned.split(". ", 1)
        if len(parts) == 2 and not any(p in parts[0] for p in ["—", "..."]):
            cleaned = f"{parts[0]} — {parts[1]}"
        return cleaned

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

    def synthesize(
        self,
        text: str,
        output_filename: str = "voiceover.mp3",
        target_duration: Optional[float] = 30.0,
        apply_studio_mastering: bool = True,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> TTSResult:
        """Synchronous wrapper to synthesize voice, conform to target duration, and apply studio mastering."""
        output_path = config.temp_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        humanized_text = self._format_humanized_text(text)
        asyncio.run(self._synthesize_async(humanized_text, output_path, rate=rate, pitch=pitch))
        duration = self._get_audio_duration(output_path)

        if target_duration is not None and duration > 0:
            # We want duration to be strictly in [target_duration - 1.5, target_duration] (approx 28.5s - 30.0s)
            ideal_target = max(10.0, target_duration - 0.5)
            if duration > target_duration or duration < (target_duration - 2.5):
                speed_ratio = duration / ideal_target
                rate_pct = int(round((speed_ratio - 1.0) * 100))
                # Clamp within natural speech range [-15%, +30%]
                rate_pct = max(-15, min(30, rate_pct))
                if rate_pct != 0:
                    adjusted_rate = f"{rate_pct:+d}%"
                    asyncio.run(self._synthesize_async(humanized_text, output_path, rate=adjusted_rate, pitch=pitch))
                    duration = self._get_audio_duration(output_path)

            # If still slightly above target_duration (e.g. 30.2s), precisely conform with FFmpeg atempo
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
                    conformed_path.replace(output_path)
                    duration = self._get_audio_duration(output_path)

        # Apply studio podcast mastering chain
        if apply_studio_mastering and output_path.exists():
            studio_path = output_path.with_name(f"studio_{output_path.name}")
            self._apply_studio_vocal_chain(output_path, studio_path)
            if studio_path.exists():
                studio_path.replace(output_path)
                duration = self._get_audio_duration(output_path)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            voice_name=self.voice,
        )

    def synthesize_dialogue(
        self,
        segments: list,
        output_filename: str = "dialogue_voiceover.mp3",
        narrator_voice: str = "en-US-ChristopherNeural",
        female_voice: str = "en-US-AvaNeural",
        male_voice: str = "en-US-EricNeural",
        apply_studio_mastering: bool = True,
    ) -> TTSResult:
        """
        Synthesize multi-voice character dialogue for storytelling shorts.
        Switches between narrator, female character, and male character voices.
        """
        output_path = config.temp_dir / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        seg_dir = output_path.parent / "dialogue_parts"
        seg_dir.mkdir(parents=True, exist_ok=True)

        if not segments:
            raise ValueError("No dialogue segments provided to synthesize.")

        if len(segments) == 1:
            self.voice = narrator_voice
            return self.synthesize(
                text=segments[0]["text"],
                output_filename=output_filename,
                target_duration=None,
                apply_studio_mastering=apply_studio_mastering,
            )

        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        concat_lines = []

        print(f"[TTS] Synthesizing {len(segments)} multi-voice dialogue segments...")
        for idx, seg in enumerate(segments):
            text = seg.get("text", "").strip()
            speaker = seg.get("speaker", "narrator").lower()
            if not text:
                continue

            if "female" in speaker or "woman" in speaker or "wife" in speaker or "sister" in speaker:
                v_name = female_voice
            elif "male" in speaker or "man" in speaker or "husband" in speaker or "brother" in speaker:
                v_name = male_voice
            else:
                v_name = narrator_voice

            seg_path = seg_dir / f"seg_{idx}_{v_name.split('-')[-1][:6]}.mp3"
            human_text = self._format_humanized_text(text)

            # Synthesize segment with selected voice
            old_voice = self.voice
            self.voice = v_name
            asyncio.run(self._synthesize_async(human_text, seg_path))
            self.voice = old_voice

            if seg_path.exists():
                safe_path = str(seg_path.resolve()).replace("\\", "/")
                concat_lines.append(f"file '{safe_path}'")

        if not concat_lines:
            raise RuntimeError("Failed to synthesize any dialogue segments.")

        concat_file = seg_dir / "concat_list.txt"
        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

        # Concat all segments into single audio file
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

        # Apply studio podcast vocal mastering chain
        if apply_studio_mastering:
            self._apply_studio_vocal_chain(raw_concat, output_path)
            if not output_path.exists():
                raw_concat.replace(output_path)
        else:
            raw_concat.replace(output_path)

        duration = self._get_audio_duration(output_path)
        print(f"[TTS] Multi-voice dialogue audio created: {duration:.2f}s across {len(concat_lines)} clips.")

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            voice_name=f"MultiVoice({narrator_voice}+{female_voice})",
        )
