import os
import wave
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..config import config
from .ffmpeg_engine import FFmpegEngine
from .music_director import AudioScorePlan, VolumeKeyframe, SelectiveSFXCue


class AudioMixer:
    """
    Production-grade dynamic audio mixer.
    Executes narrative-aware background music scoring, spectral EQ vocal carving,
    piecewise linear volume automation curves, speech-reactive sidechain ducking,
    and 60ms J-cut pre-empted sound design cues.
    """

    def __init__(self, ffmpeg_engine: Optional[FFmpegEngine] = None):
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()

    def _generate_ambient_bgm(self, output_path: Path, duration: float) -> Path:
        """Procedurally generate a subtle, warm cinematic ambient drone using FFmpeg audio synthesizer."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg.ffmpeg_path,
            "-y",
            "-f", "lavfi",
            "-i", f"anoisesrc=d={duration + 4}:c=pink:r=44100:a=0.006",
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

    def _build_piecewise_volume_expr(
        self,
        base_volume: float,
        keyframes: List[VolumeKeyframe],
        total_duration: float,
    ) -> str:
        """
        Construct a smooth piecewise linear volume automation expression for FFmpeg's volume filter.
        Interpolates smoothly between narrative beats (Hook -> Build -> Climax -> Payoff -> Outro).
        """
        if not keyframes:
            return f"{base_volume:.4f}"

        # Clean and sort keyframes
        clean_kfs = []
        for kf in keyframes:
            t = max(0.0, min(total_duration, float(kf.time_sec)))
            v = base_volume * max(0.0, float(kf.volume_multiplier))
            clean_kfs.append((t, v))
        clean_kfs.sort(key=lambda x: x[0])

        # Ensure t=0 is defined
        if clean_kfs[0][0] > 0.0:
            clean_kfs.insert(0, (0.0, clean_kfs[0][1]))

        # Ensure end duration is defined
        if clean_kfs[-1][0] < total_duration:
            clean_kfs.append((total_duration, clean_kfs[-1][1]))

        # Build nested if(lt(t, t_i), interpolated_val, ...)
        def make_segment(i: int) -> str:
            if i >= len(clean_kfs) - 1:
                return f"{clean_kfs[-1][1]:.4f}"
            t0, v0 = clean_kfs[i]
            t1, v1 = clean_kfs[i + 1]
            dt = max(0.01, t1 - t0)
            dv = v1 - v0
            curr_interp = f"({v0:.4f}+({dv:.4f})*(t-{t0:.2f})/{dt:.2f})"
            next_seg = make_segment(i + 1)
            return f"if(lt(t,{t1:.2f}),{curr_interp},{next_seg})"

        return make_segment(0)

    def _build_selective_sfx_track(
        self,
        total_duration: float,
        sfx_cues: List[SelectiveSFXCue],
        output_wav: Path,
    ) -> Optional[Path]:
        """Synthesize a sample-accurate SFX track placing subtle whooshes with 60ms J-cut pre-emption."""
        self._ensure_sfx_files()
        sfx_dir = config.assets_dir / "sfx"
        whoosh_path = sfx_dir / "whoosh.wav"
        pop_path = sfx_dir / "pop.wav"

        if not sfx_cues:
            return None

        def load_wav(p: Path):
            with wave.open(str(p), "rb") as w:
                return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)

        sr = 44100
        timeline = np.zeros(int((total_duration + 3.0) * sr), dtype=np.float32)
        has_sfx = False

        for cue in sfx_cues:
            ct = cue.timestamp
            if ct < 0.4:
                continue  # Never whoosh at 0.0s before opening hook establishes

            chosen_file = pop_path if cue.sfx_type == "pop" and pop_path.exists() else whoosh_path
            if not chosen_file.exists():
                continue

            audio_data = load_wav(chosen_file)
            # 60ms J-cut sonic pre-emption
            lead_time = 0.06
            idx = max(0, int((ct - lead_time) * sr))
            if idx < len(timeline):
                end_idx = min(len(timeline), idx + len(audio_data))
                # Subtle volume so sound design stays organic
                vol = 0.32 if cue.sfx_type == "whoosh" else 0.50
                timeline[idx:end_idx] += audio_data[:end_idx - idx] * vol
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

    def mix_with_score_plan(
        self,
        voice_audio: Path,
        output_path: Path,
        score_plan: AudioScorePlan,
        total_duration: float,
        voice_volume: float = 1.0,
    ) -> Path:
        """
        Execute full dynamic audio mixing with the given AudioScorePlan:
        1. Spectral EQ carving (-4dB at 2.5kHz) to give narration room to shine.
        2. Piecewise linear volume curve following narrative arc (Hook -> Climax swell -> Payoff).
        3. Smooth head/tail fades.
        4. Speech-reactive sidechain ducking.
        5. Curated J-cut sound design cues.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate BGM track
        resolved_bgm = score_plan.track_path
        if not resolved_bgm.exists():
            ambient_path = config.temp_dir / "ambient_fallback.mp3"
            resolved_bgm = self._generate_ambient_bgm(ambient_path, total_duration)

        # Build selective SFX track
        sfx_track_path = config.temp_dir / "dynamic_sfx_track.wav"
        sfx_file = self._build_selective_sfx_track(
            total_duration=total_duration,
            sfx_cues=score_plan.sfx_cues,
            output_wav=sfx_track_path,
        )

        # Construct piecewise volume curve for BGM
        volume_expr = self._build_piecewise_volume_expr(
            base_volume=score_plan.base_bgm_volume,
            keyframes=score_plan.volume_keyframes,
            total_duration=total_duration,
        )

        fade_out_start = max(1.0, total_duration - score_plan.fade_out_duration)

        # Build BGM preparation chain
        # aloop/stream_loop -> equalizer (2.5kHz vocal carve) -> dynamic volume curve -> head fade -> tail fade
        bgm_chain = (
            f"[1:a]aloop=loop=-1:size=2e+09,"
            f"equalizer=f={score_plan.eq_carve_freq}:t=q:w=1.5:g={score_plan.eq_carve_gain},"
            f"volume=eval=frame:volume='{volume_expr}',"
            f"afade=t=in:ss=0:d={score_plan.fade_in_duration:.2f},"
            f"afade=t=out:st={fade_out_start:.2f}:d={score_plan.fade_out_duration:.2f}[bgm_prepared];"
            f"[bgm_prepared][0:a]sidechaincompress="
            f"threshold={score_plan.ducking_threshold}:"
            f"ratio={score_plan.ducking_ratio}:"
            f"attack={score_plan.ducking_attack_ms}:"
            f"release={score_plan.ducking_release_ms}[bgm_ducked]"
        )

        voice_chain = f"[0:a]volume={voice_volume}[voice]"

        if sfx_file and sfx_file.exists():
            filter_complex = (
                f"{voice_chain};"
                f"{bgm_chain};"
                f"[2:a]volume=1.0[sfx];"
                f"[voice][bgm_ducked][sfx]amix=inputs=3:duration=first:normalize=0[outa]"
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
                f"{voice_chain};"
                f"{bgm_chain};"
                f"[voice][bgm_ducked]amix=inputs=2:duration=first:normalize=0[outa]"
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

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"[AudioMixer] FFmpeg filter_complex warning: {res.stderr[:400]}")
            # Fallback to standard 2-channel mix if complex expression threw an edge case
            fallback_fc = (
                f"[0:a]volume={voice_volume}[voice];"
                f"[1:a]volume={score_plan.base_bgm_volume}[bgm];"
                f"[voice][bgm]amix=inputs=2:duration=first:normalize=0[outa]"
            )
            cmd_fb = [
                self.ffmpeg.ffmpeg_path, "-y",
                "-i", str(voice_audio),
                "-stream_loop", "-1",
                "-i", str(resolved_bgm),
                "-filter_complex", fallback_fc,
                "-map", "[outa]",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]
            subprocess.run(cmd_fb, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)

        return output_path

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
        """Legacy compatibility wrapper creating an ad-hoc score plan."""
        from .music_director import VolumeKeyframe, SelectiveSFXCue, AudioScorePlan
        
        target_path = bgm_path or (config.bgm_dir / "chill_lofi" / "chill_lofi_starter_1.mp3")
        cues = []
        if cut_timestamps:
            for ct in cut_timestamps[:3]:
                if ct > 0.5:
                    cues.append(SelectiveSFXCue(timestamp=ct, sfx_type="whoosh", narrative_reason="cut"))

        plan = AudioScorePlan(
            track_path=target_path,
            track_title=target_path.name,
            genre="Ambient Production",
            mood="Adaptive",
            score_rationale="Legacy compatibility audio mix",
            base_bgm_volume=bgm_volume,
            volume_keyframes=[
                VolumeKeyframe(time_sec=0.0, volume_multiplier=1.0, narrative_beat="hook"),
                VolumeKeyframe(time_sec=20.0, volume_multiplier=1.1, narrative_beat="climax"),
                VolumeKeyframe(time_sec=28.0, volume_multiplier=0.0, narrative_beat="fade"),
            ],
            sfx_cues=cues,
        )
        return self.mix_with_score_plan(
            voice_audio=voice_audio,
            output_path=output_path,
            score_plan=plan,
            total_duration=30.0,
            voice_volume=voice_volume,
        )
