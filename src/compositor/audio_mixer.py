import os
import wave
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional, List
from ..config import config
from .ffmpeg_engine import FFmpegEngine


class AudioMixer:
    def __init__(self, ffmpeg_engine: Optional[FFmpegEngine] = None):
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()

    def _generate_ambient_bgm(self, output_path: Path, duration: float) -> Path:
        """Procedurally generate a subtle, warm cinematic ambient drone using FFmpeg audio synthesizer."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg.ffmpeg_path,
            "-y",
            "-f", "lavfi",
            "-i", f"anoisesrc=d={duration + 2}:c=pink:r=44100:a=0.006",
            "-af", "lowpass=f=400,volume=0.2",
            "-c:a", "libmp3lame",
            str(output_path),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path

    def _ensure_sfx_files(self):
        """Ensure standard whoosh and pop sound effects exist in assets/sfx."""
        sfx_dir = config.assets_dir / "sfx"
        sfx_dir.mkdir(parents=True, exist_ok=True)

        whoosh_path = sfx_dir / "whoosh.wav"
        if not whoosh_path.exists():
            cmd_whoosh = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-f", "lavfi",
                "-i", "anoisesrc=d=0.3:c=pink:r=44100:a=0.5",
                "-af", "bandpass=f=1200:w=800,volume=1.5,afade=t=in:ss=0:d=0.1,afade=t=out:st=0.15:d=0.15",
                str(whoosh_path)
            ]
            subprocess.run(cmd_whoosh, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        pop_path = sfx_dir / "pop.wav"
        if not pop_path.exists():
            cmd_pop = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-f", "lavfi",
                "-i", "aevalsrc=sin(2*PI*(900+300*exp(-40*t))*t)*exp(-25*t):d=0.15:s=44100",
                "-af", "volume=1.2",
                str(pop_path)
            ]
            subprocess.run(cmd_pop, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def _build_sfx_track(
        self,
        total_duration: float,
        cut_timestamps: Optional[List[float]],
        impact_timestamps: Optional[List[float]],
        output_wav: Path,
    ) -> Optional[Path]:
        """Synthesize a sample-accurate SFX track with transition whooshes on cuts and pops on key words."""
        self._ensure_sfx_files()
        sfx_dir = config.assets_dir / "sfx"
        whoosh_path = sfx_dir / "whoosh.wav"
        pop_path = sfx_dir / "pop.wav"

        if not whoosh_path.exists() and not pop_path.exists():
            return None

        def load_wav(p: Path):
            with wave.open(str(p), "rb") as w:
                return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)

        sr = 44100
        timeline = np.zeros(int((total_duration + 3.0) * sr), dtype=np.float32)
        has_sfx = False

        if cut_timestamps and whoosh_path.exists():
            whoosh = load_wav(whoosh_path)
            for ct in cut_timestamps:
                if ct < 0.3:
                    continue  # Don't whoosh right at 0.0s before intro starts
                idx = int(ct * sr)
                if idx < len(timeline):
                    end_idx = min(len(timeline), idx + len(whoosh))
                    timeline[idx:end_idx] += whoosh[:end_idx - idx] * 0.45
                    has_sfx = True

        if impact_timestamps and pop_path.exists():
            pop = load_wav(pop_path)
            for it in impact_timestamps:
                idx = int(it * sr)
                if idx < len(timeline):
                    end_idx = min(len(timeline), idx + len(pop))
                    timeline[idx:end_idx] += pop[:end_idx - idx] * 0.60
                    has_sfx = True

        if not has_sfx:
            return None

        timeline = np.clip(timeline, -32768, 32767).astype(np.int16)
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(timeline.tobytes())

        return output_wav

    def get_or_create_bgm(self, target_duration: float, custom_bgm_path: Optional[Path] = None) -> Path:
        """Find an existing BGM file in assets/bgm or generate a procedural ambient bed."""
        if custom_bgm_path and custom_bgm_path.exists():
            return custom_bgm_path

        bgm_files = list(config.bgm_dir.glob("*.mp3"))
        if bgm_files:
            return bgm_files[0]

        ambient_path = config.temp_dir / "ambient_bed.mp3"
        return self._generate_ambient_bgm(ambient_path, target_duration)

    def mix_voice_and_bgm(
        self,
        voice_audio: Path,
        output_path: Path,
        bgm_path: Optional[Path] = None,
        cut_timestamps: Optional[List[float]] = None,
        impact_timestamps: Optional[List[float]] = None,
        voice_volume: float = 1.0,
        bgm_volume: float = 0.14,
    ) -> Path:
        """Mix voiceover, background music, transition whooshes, and impact SFX."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_bgm = self.get_or_create_bgm(60.0, bgm_path)

        # Estimate duration
        sfx_track_path = config.temp_dir / "sfx_track.wav"
        sfx_file = self._build_sfx_track(
            total_duration=60.0,
            cut_timestamps=cut_timestamps,
            impact_timestamps=impact_timestamps,
            output_wav=sfx_track_path,
        )

        if sfx_file and sfx_file.exists():
            filter_complex = (
                f"[0:a]volume={voice_volume}[voice];"
                f"[1:a]volume={bgm_volume}[bgm];"
                f"[2:a]volume=1.0[sfx];"
                f"[voice][bgm][sfx]amix=inputs=3:duration=first:normalize=0[outa]"
            )
            cmd = [
                self.ffmpeg.ffmpeg_path,
                "-y",
                "-i", str(voice_audio),
                "-stream_loop", "-1",
                "-i", str(resolved_bgm),
                "-i", str(sfx_file),
                "-filter_complex", filter_complex,
                "-map", "[outa]",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]
        else:
            filter_complex = (
                f"[1:a]volume={bgm_volume}[bgm];"
                f"[0:a]volume={voice_volume}[voice];"
                f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            )
            cmd = [
                self.ffmpeg.ffmpeg_path,
                "-y",
                "-i", str(voice_audio),
                "-stream_loop", "-1",
                "-i", str(resolved_bgm),
                "-filter_complex", filter_complex,
                "-map", "[outa]",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return output_path
