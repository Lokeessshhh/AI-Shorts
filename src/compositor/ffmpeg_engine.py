import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Any
from ..config import config


class FFmpegEngine:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or self._locate_ffmpeg()

    def _locate_ffmpeg(self) -> str:
        """Find system ffmpeg or fallback to imageio-ffmpeg bundled binary."""
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            raise RuntimeError(
                "FFmpeg is not installed and imageio-ffmpeg is unavailable."
            )

    def prepare_clip(
        self,
        input_path: Path,
        output_path: Path,
        duration: float,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> Path:
        """Normalize, center-crop to 9:16 portrait, loop/trim to duration, and re-encode to 30fps."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Scale to fill 1080x1920 and center-crop, then trim to target duration
        vf_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"setsar=1,fps={fps},"
            f"eq=contrast=1.06:saturation=1.12,"
            f"noise=alls=6:allf=t+u,"
            f"vignette=PI/4"
        )

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-stream_loop", "-1",  # Loop input if it's shorter than required duration
            "-i", str(input_path),
            "-t", str(duration),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-an",  # Strip original video audio (we mix voice + BGM cleanly)
            str(output_path),
        ]

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
        return output_path

    def concat_clips(
        self,
        clip_paths: List[Path],
        output_path: Path,
        scene_durations: Optional[List[float]] = None,
        transition: str = "fade",
        transition_duration: float = 0.20,
    ) -> Path:
        """Concatenate normalized video clips with seamless visual transitions (xfade) or concat demuxer."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if scene_durations and len(clip_paths) > 1 and len(scene_durations) == len(clip_paths):
            # Chained xfade transitions
            cmd = [self.ffmpeg_path, "-y"]
            for cp in clip_paths:
                cmd.extend(["-i", str(cp.resolve())])

            filters = []
            cum_offset = 0.0
            last_v = "0:v"

            for i in range(1, len(clip_paths)):
                cum_offset += scene_durations[i - 1]
                next_v = f"v{i}"
                filters.append(
                    f"[{last_v}][{i}:v]xfade=transition={transition}:duration={transition_duration}:offset={cum_offset:.2f}[{next_v}]"
                )
                last_v = next_v

            cmd.extend([
                "-filter_complex", ";".join(filters),
                "-map", f"[{last_v}]",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                str(output_path.resolve()),
            ])

            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                return output_path

        concat_txt = config.temp_dir / "concat_list.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                # Use forward slashes for FFmpeg concat manifest
                formatted = str(clip.resolve()).replace("\\", "/")
                f.write(f"file '{formatted}'\n")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c", "copy",
            str(output_path),
        ]

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
        return output_path

    def composite_final_short(
        self,
        concatenated_video: Path,
        master_audio: Path,
        ass_subtitles: Path,
        output_path: Path,
        emoji_events: Optional[List[Any]] = None,
        duration_limit: Optional[float] = 30.0,
    ) -> Path:
        """Single-pass master render: Combines video, audio, burns ASS subtitles, overlays 3D color emojis, and strictly caps duration."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ass_filename = ass_subtitles.name
        working_dir = ass_subtitles.parent

        if emoji_events:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(concatenated_video.resolve()),
                "-i", str(master_audio.resolve()),
            ]

            for event in emoji_events:
                cmd.extend(["-loop", "1", "-i", str(event.file_path.resolve())])

            filters = []
            filters.append(f"[0:v]subtitles={ass_filename}[vsub]")
            last_v = "vsub"

            for idx, event in enumerate(emoji_events):
                input_idx = 2 + idx
                scale_label = f"emo{idx}"
                next_v = f"v{idx+1}"
                filters.append(f"[{input_idx}:v]scale=130:130[{scale_label}]")
                filters.append(
                    f"[{last_v}][{scale_label}]overlay=x=(W-w)/2:y=1260:enable='between(t,{event.start:.2f},{event.end:.2f})'[{next_v}]"
                )
                last_v = next_v

            filter_complex_str = ";".join(filters)

            cmd.extend([
                "-filter_complex", filter_complex_str,
                "-map", f"[{last_v}]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
            ])
            if duration_limit:
                cmd.extend(["-t", str(duration_limit)])
            cmd.append(str(output_path.resolve()))
        else:
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(concatenated_video.resolve()),
                "-i", str(master_audio.resolve()),
                "-vf", f"subtitles={ass_filename}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
            ]
            if duration_limit:
                cmd.extend(["-t", str(duration_limit)])
            cmd.append(str(output_path.resolve()))

        result = subprocess.run(
            cmd,
            cwd=str(working_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg composite failed:\n{result.stderr}")

        return output_path
