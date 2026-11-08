"""Mode 3 Short Editor & Filtergraph Polish Engine.
Applies attention-reset micro-zooms, glowing progress bar, dynamic ASS subtitle burn-in,
3D color emoji overlays, and broadcast loudness mastering.
"""

import os
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
            font_size=68,
            margin_v=420,  # Perfectly centered above platform UI overlay
            max_words_per_line=3,
        )
        self.reframer = SmartReframer()

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

        print(f"[Clipper/Editor] Rendering Clip #{rank}: {start_time:.1f}s -> {end_time:.1f}s ({duration:.1f}s)")

        # 1. Analyze framing if not already provided
        if not reframe_analysis:
            reframe_analysis = self.reframer.analyze_clip(
                video_path=source_video,
                start_time=start_time,
                end_time=end_time,
                sample_fps=1.5,
                forced_layout=layout,
            )

        layout_type = reframe_analysis.get("layout", "solo")
        print(f"[Clipper/Editor] Clip #{rank} Layout detected: {layout_type.upper()}")

        # 2. Compile ASS Subtitles
        words_data = highlight.get("words", [])
        word_objs = [
            WordTimestamp(word=w["word"], start=w["start"], end=w["end"])
            for w in words_data
        ]
        ass_path = temp_dir / f"clip_{rank}_subtitles.ass"
        _, emoji_events = self.subtitle_builder.build_ass(word_objs, ass_path)

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
                "-ss", f"{start_time:.3f}",
                "-to", f"{end_time:.3f}",
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
                "-ss", f"{start_time:.3f}",
                "-to", f"{end_time:.3f}",
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
