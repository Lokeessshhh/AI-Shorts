"""Mode 2 Video Compositor & Filtergraph Editor.
Supports:
1. Full-Screen Floating Card layout (Hook pop-in -> Full-screen gameplay + Top Pill + Hormozi Subs)
2. 50/50 Split-Screen layout (Top: Reddit Card / Story UI, Bottom: Gameplay, 3px Divider)
3. Studio BGM Engine with Spectral EQ Carving (-5dB @ 2.5kHz), Dynamic Sidechain Compression,
   and SFX Sound Design (Card pop ding, Twist impact hit).
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import imageio_ffmpeg

from ..config import config
from ..subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp, EmojiEvent


class StoryEditor:
    """Assembles and polishes Mode 2 Reddit narrative shorts."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or self._locate_ffmpeg()
        self.subtitle_builder = ASSSubtitleBuilder(
            font_size=68,
            margin_v=440,
            max_words_per_line=3,
        )

    def _locate_ffmpeg(self) -> str:
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()

    def _build_studio_audio_graph(
        self,
        voice_idx: int,
        bgm_path: Optional[Path],
        story_duration: float,
        has_ding: bool,
        ding_idx: int,
        has_twist_sfx: bool = False,
        twist_idx: int = -1,
        twist_time: float = 0.0,
    ) -> Tuple[List[str], str]:
        """
        Build studio-grade multi-track audio filtergraph:
        - Voice highpass at 80Hz + sidechain trigger split
        - BGM looped + EQ 2.5kHz scooped + dynamic sidechain ducking
        - SFX at t=0 and twist
        - EBU R128 loudness normalization (-14 LUFS)
        """
        filter_lines = []

        # 1. Clean voice & sidechain trigger
        filter_lines.append(f"[{voice_idx}:a]highpass=f=80,asplit=2[vox_clean][vox_sc]")

        # 2. SFX track
        sfx_pads = []
        if has_ding:
            filter_lines.append(f"[{ding_idx}:a]volume=0.85[sfx_ding]")
            sfx_pads.append("[sfx_ding]")

        if has_twist_sfx and twist_idx >= 0:
            delay_ms = int(twist_time * 1000)
            filter_lines.append(f"[{twist_idx}:a]adelay={delay_ms}|{delay_ms},volume=0.75[sfx_twist]")
            sfx_pads.append("[sfx_twist]")

        fade_out_start = max(0.0, story_duration - 1.5)

        if bgm_path and bgm_path.exists():
            bgm_idx = ding_idx + (1 if has_ding else 0) + (1 if (has_twist_sfx and twist_idx >= 0) else 0)
            # BGM loop, EQ carve, volume 0.32, fade in/out
            filter_lines.append(
                f"[{bgm_idx}:a]aloop=loop=-1:size=2e+09,"
                f"equalizer=f=2500:t=q:w=1.5:g=-5,"
                f"volume=0.30,"
                f"afade=t=in:ss=0:d=0.8,"
                f"afade=t=out:st={fade_out_start:.2f}:d=1.5[bgm_prepared]"
            )
            # Dynamic Sidechain Compression
            filter_lines.append(
                "[bgm_prepared][vox_sc]sidechaincompress="
                "threshold=0.10:ratio=2.5:attack=15:release=350[bgm_ducked]"
            )

            # Mix voice, ducked BGM, and SFX
            mix_inputs = ["[vox_clean]", "[bgm_ducked]"] + sfx_pads
            filter_lines.append(
                f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0[mixed]"
            )
            filter_lines.append("[mixed]loudnorm=I=-14:LRA=7:TP=-1.5[aout]")
        else:
            # Fallback without BGM
            if sfx_pads:
                mix_inputs = ["[vox_clean]"] + sfx_pads
                filter_lines.append(
                    f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:normalize=0[mixed]"
                )
                filter_lines.append("[mixed]loudnorm=I=-14:LRA=7:TP=-1.5[aout]")
            else:
                filter_lines.append("[vox_clean]loudnorm=I=-14:LRA=7:TP=-1.5[aout]")

        return filter_lines, "[aout]"

    def assemble_floating_card(
        self,
        card_png: Path,
        gameplay_mp4: Path,
        voice_audio: Path,
        word_timestamps: List[Dict[str, Any]],
        output_mp4: Path,
        temp_dir: Path,
        story_duration: float,
        header_pill_png: Optional[Path] = None,
        comment_card_png: Optional[Path] = None,
        bgm_path: Optional[Path] = None,
        card_duration: float = 3.6,
        twist_time: float = 0.0,
        enable_progress_bar: bool = True,
        enable_micro_zoom: bool = True,
    ) -> Path:
        """
        Assemble Modern Full-Screen Floating Card Short:
        - Full-screen satisfying gameplay (1080x1920)
        - 0-3.6s: Transparent dark-mode Reddit Card floats in center with pop-in + ding SFX
        - 3.6s+: Card fades away into subtle header pill, full focus on gameplay & Hormozi subtitles
        - Twist Moment: Micro-zoom punch-in + subtle thud SFX
        - Studio sidechain ducked BGM + broadcast loudnorm (-14 LUFS)
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Story/Editor] Assembling Floating-Card Master Short ({story_duration:.1f}s)...")

        # 1. Compile ASS Subtitles
        word_objs = [
            WordTimestamp(word=w["word"], start=w["start"], end=w["end"])
            for w in word_timestamps
        ]
        ass_path = temp_dir / "floating_subtitles.ass"
        # Subtitles centered in lower third
        self.subtitle_builder.margin_v = 440
        _, emoji_events = self.subtitle_builder.build_ass(word_objs, ass_path)

        safe_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
        ding_wav = config.sfx_dir / "ding.wav"
        thud_wav = config.sfx_dir / "thud.wav"

        out_w = config.video_width   # 1080
        out_h = config.video_height  # 1920

        filter_chains = []

        # 0. Scale/Crop Gameplay to 1080x1920
        base_filter = (
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h}[v_raw]"
        )
        filter_chains.append(base_filter)
        curr_v = "v_raw"

        # 1. Overlay Floating Card (Inputs: 0=gameplay, 1=voice, 2=card_png)
        # Card pop-in scale / display for first card_duration seconds
        card_filter = (
            f"[{curr_v}][2:v]overlay=x=(W-w)/2:y=(H-h)/2 - 100:"
            f"enable='between(t,0,{card_duration:.2f})'[v_card]"
        )
        filter_chains.append(card_filter)
        curr_v = "v_card"

        # 2. Overlay Header Pill after card fades out if provided
        next_input_idx = 3
        if header_pill_png and header_pill_png.exists():
            pill_idx = next_input_idx
            next_input_idx += 1
            pill_filter = (
                f"[{curr_v}][{pill_idx}:v]overlay=x=(W-w)/2:y=110:"
                f"enable='gte(t,{card_duration:.2f})'[v_pill]"
            )
            filter_chains.append(pill_filter)
            curr_v = "v_pill"

        # 3. Overlay Comment Card at twist/climax if provided
        if comment_card_png and comment_card_png.exists() and twist_time > 5.0:
            comm_idx = next_input_idx
            next_input_idx += 1
            comm_start = max(5.0, twist_time)
            comm_end = min(story_duration - 1.0, comm_start + 4.5)
            comm_filter = (
                f"[{curr_v}][{comm_idx}:v]overlay=x=(W-w)/2:y=240:"
                f"enable='between(t,{comm_start:.2f},{comm_end:.2f})'[v_comm]"
            )
            filter_chains.append(comm_filter)
            curr_v = "v_comm"

        # 4. Micro-Zoom Punch-In during the hook (first 3.0s)
        if enable_micro_zoom and story_duration > 6.0:
            zoom_out = "v_zoom"
            zoom_filter = (
                f"[{curr_v}]split=2[v_orig][v_hook];"
                f"[v_hook]scale=1144:2035,crop={out_w}:{out_h}[v_hook_crop];"
                f"[v_orig][v_hook_crop]overlay=enable='between(t,0,3.0)':shortest=1[{zoom_out}]"
            )
            filter_chains.append(zoom_filter)
            curr_v = zoom_out

        # 5. Glowing Animated Progress Bar at bottom
        if enable_progress_bar:
            prog_out = "v_prog"
            prog_filter = (
                f"[{curr_v}]drawbox=x=0:y=1914:"
                f"w='min(1080,1080*t/{story_duration:.3f})':h=6:color=#FF4500@0.95:t=fill[{prog_out}]"
            )
            filter_chains.append(prog_filter)
            curr_v = prog_out

        # 6. Burn ASS Subtitles
        sub_out = "v_sub"
        filter_chains.append(f"[{curr_v}]subtitles='{safe_ass}'[{sub_out}]")
        curr_v = sub_out

        # 7. 3D Emoji popups
        if emoji_events:
            for idx, ev in enumerate(emoji_events):
                next_v = f"v_em_{idx}"
                safe_em = str(ev.file_path).replace("\\", "/").replace(":", "\\:")
                em_filter = (
                    f"movie='{safe_em}',scale=150:150[em_{idx}];"
                    f"[{curr_v}][em_{idx}]overlay=x=(W-w)/2:y=1250:"
                    f"enable='between(t,{ev.start:.3f},{ev.end:.3f})'[{next_v}]"
                )
                filter_chains.append(em_filter)
                curr_v = next_v

        # Prepare Inputs & Audio Graph
        cmd_inputs = [
            self.ffmpeg_path,
            "-y",
            "-loglevel", "error",
            "-i", str(gameplay_mp4),           # Input 0: Gameplay video
            "-i", str(voice_audio),            # Input 1: Voiceover audio
            "-loop", "1", "-i", str(card_png), # Input 2: Floating Card image
        ]

        if header_pill_png and header_pill_png.exists():
            cmd_inputs.extend(["-loop", "1", "-i", str(header_pill_png)])

        if comment_card_png and comment_card_png.exists() and twist_time > 5.0:
            cmd_inputs.extend(["-loop", "1", "-i", str(comment_card_png)])

        # Sound Effects
        has_ding = ding_wav.exists()
        ding_idx = next_input_idx
        if has_ding:
            cmd_inputs.extend(["-i", str(ding_wav)])
            next_input_idx += 1

        has_twist_sfx = thud_wav.exists() and twist_time > 5.0
        twist_idx = next_input_idx if has_twist_sfx else -1
        if has_twist_sfx:
            cmd_inputs.extend(["-i", str(thud_wav)])
            next_input_idx += 1

        if bgm_path and bgm_path.exists():
            cmd_inputs.extend(["-stream_loop", "-1", "-i", str(bgm_path)])

        audio_filters, aout_pad = self._build_studio_audio_graph(
            voice_idx=1,
            bgm_path=bgm_path,
            story_duration=story_duration,
            has_ding=has_ding,
            ding_idx=ding_idx,
            has_twist_sfx=has_twist_sfx,
            twist_idx=twist_idx,
            twist_time=twist_time,
        )

        full_filtergraph = ";".join(filter_chains + audio_filters)

        cmd = cmd_inputs + [
            "-filter_complex", full_filtergraph,
            "-map", f"[{curr_v}]",
            "-map", aout_pad,
            "-t", f"{story_duration:.3f}",
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
            raise RuntimeError(f"FFmpeg Floating-Card render failed: {res.stderr}\nCommand: {' '.join(cmd)}")

        return output_mp4

    def assemble_split_screen(
        self,
        card_png: Path,
        gameplay_mp4: Path,
        voice_audio: Path,
        word_timestamps: List[Dict[str, Any]],
        output_mp4: Path,
        temp_dir: Path,
        story_duration: float,
        bgm_path: Optional[Path] = None,
        title_duration: float = 3.5,
        enable_progress_bar: bool = True,
        enable_micro_zoom: bool = True,
    ) -> Path:
        """
        Assemble Classic 50/50 Split-Screen Short with Studio Ducked BGM:
        - Top Half (1080x960): Deep slate background + Reddit Dark Card
        - Bottom Half (1080x960): Satisfying gameplay
        - Center Divider: 3px sleek border at Y=960
        - Center Subtitles: Dynamic Hormozi captions
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Story/Editor] Assembling 50/50 Split-Screen Short ({story_duration:.1f}s)...")

        word_objs = [
            WordTimestamp(word=w["word"], start=w["start"], end=w["end"])
            for w in word_timestamps
        ]
        ass_path = temp_dir / "story_subtitles.ass"
        self.subtitle_builder.margin_v = 460
        _, emoji_events = self.subtitle_builder.build_ass(word_objs, ass_path)

        safe_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
        ding_wav = config.sfx_dir / "ding.wav"

        out_w = config.video_width   # 1080
        out_h = config.video_height  # 1920
        half_h = out_h // 2          # 960

        filter_chains = []

        # Top Container: Scaled Reddit Card from input 2 (1080x960)
        top_filter = f"[2:v]scale={out_w}:{half_h}[top_half]"
        filter_chains.append(top_filter)

        # Bottom Container: Scaled & Cropped Gameplay (1080x960) from input 0
        bot_filter = (
            f"[0:v]scale={out_w}:{half_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{half_h}[bot_half]"
        )
        filter_chains.append(bot_filter)

        # Vertical Stack + 3px Divider at center (Y=960)
        stack_filter = (
            f"[top_half][bot_half]vstack[v_stack];"
            f"[v_stack]drawbox=x=0:y={half_h - 1}:w={out_w}:h=3:color=#343536@0.9:t=fill[v_base]"
        )
        filter_chains.append(stack_filter)
        curr_v = "v_base"

        # Attention-Reset Micro-Zoom during Hook
        if enable_micro_zoom and story_duration > 6.0:
            zoom_out = "v_zoom"
            zoom_filter = (
                f"[{curr_v}]split=2[v_orig][v_hook];"
                f"[v_hook]scale=1144:2035,crop={out_w}:{out_h}[v_hook_crop];"
                f"[v_orig][v_hook_crop]overlay=enable='between(t,0,3.2)':shortest=1[{zoom_out}]"
            )
            filter_chains.append(zoom_filter)
            curr_v = zoom_out

        # Animated Glowing Progress Bar at Bottom
        if enable_progress_bar:
            prog_out = "v_prog"
            prog_filter = (
                f"[{curr_v}]drawbox=x=0:y=1914:"
                f"w='min(1080,1080*t/{story_duration:.3f})':h=6:color=#FF4500@0.95:t=fill[{prog_out}]"
            )
            filter_chains.append(prog_filter)
            curr_v = prog_out

        # Burn ASS Subtitles
        sub_out = "v_sub"
        filter_chains.append(f"[{curr_v}]subtitles='{safe_ass}'[{sub_out}]")
        curr_v = sub_out

        # 3D Emojis
        if emoji_events:
            for idx, ev in enumerate(emoji_events):
                next_v = f"v_em_{idx}"
                safe_em = str(ev.file_path).replace("\\", "/").replace(":", "\\:")
                em_filter = (
                    f"movie='{safe_em}',scale=150:150[em_{idx}];"
                    f"[{curr_v}][em_{idx}]overlay=x=(W-w)/2:y={half_h + 380}:"
                    f"enable='between(t,{ev.start:.3f},{ev.end:.3f})'[{next_v}]"
                )
                filter_chains.append(em_filter)
                curr_v = next_v

        # Audio Graph Setup
        cmd_inputs = [
            self.ffmpeg_path,
            "-y",
            "-loglevel", "error",
            "-i", str(gameplay_mp4),           # Input 0: Gameplay video
            "-i", str(voice_audio),            # Input 1: Voiceover audio
            "-loop", "1", "-i", str(card_png), # Input 2: Looped Reddit Card image
        ]

        has_ding = ding_wav.exists()
        ding_idx = 3
        if has_ding:
            cmd_inputs.extend(["-i", str(ding_wav)])

        if bgm_path and bgm_path.exists():
            cmd_inputs.extend(["-stream_loop", "-1", "-i", str(bgm_path)])

        audio_filters, aout_pad = self._build_studio_audio_graph(
            voice_idx=1,
            bgm_path=bgm_path,
            story_duration=story_duration,
            has_ding=has_ding,
            ding_idx=ding_idx,
        )

        full_filtergraph = ";".join(filter_chains + audio_filters)

        cmd = cmd_inputs + [
            "-filter_complex", full_filtergraph,
            "-map", f"[{curr_v}]",
            "-map", aout_pad,
            "-t", f"{story_duration:.3f}",
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
            raise RuntimeError(f"FFmpeg Split-Screen render failed: {res.stderr}\nCommand: {' '.join(cmd)}")

        return output_mp4
