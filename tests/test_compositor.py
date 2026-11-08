import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.compositor.ffmpeg_engine import FFmpegEngine
from src.compositor.audio_mixer import AudioMixer
from src.visuals.pexels import PexelsVisualFetcher
from src.subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp


def test_compositor_end_to_end_clip():
    ffmpeg = FFmpegEngine()
    mixer = AudioMixer(ffmpeg)
    visuals = PexelsVisualFetcher()
    subtitles = ASSSubtitleBuilder()

    # 1. Generate 2 short test clips (2 seconds each)
    clip1 = visuals.fetch_clip_for_scene(1, ["dark room"], 2.0)
    clip2 = visuals.fetch_clip_for_scene(2, ["neon light"], 2.0)

    norm1 = config.temp_dir / "test_norm_1.mp4"
    norm2 = config.temp_dir / "test_norm_2.mp4"

    ffmpeg.prepare_clip(clip1.file_path, norm1, duration=2.0)
    ffmpeg.prepare_clip(clip2.file_path, norm2, duration=2.0)

    # 2. Concat clips
    concat_out = config.temp_dir / "test_concat.mp4"
    ffmpeg.concat_clips([norm1, norm2], concat_out)
    assert concat_out.exists()

    # 3. Create audio bed
    audio_out = config.temp_dir / "test_master_audio.mp3"
    mixer._generate_ambient_bgm(audio_out, duration=4.0)
    assert audio_out.exists()

    # 4. Create mini ASS
    words = [
        WordTimestamp("TESTING", 0.0, 1.5),
        WordTimestamp("COMPOSITOR", 1.5, 3.5),
    ]
    ass_path = config.temp_dir / "test_comp.ass"
    subtitles.build_ass(words, ass_path)

    # 5. Master Composite
    final_out = config.output_dir / "test_final_render.mp4"
    ffmpeg.composite_final_short(
        concatenated_video=concat_out,
        master_audio=audio_out,
        ass_subtitles=ass_path,
        output_path=final_out,
    )

    assert final_out.exists()
    assert final_out.stat().st_size > 10000
    print(f"\n[PASSED] Compositor rendered test video: {final_out.name}")
    print(f"File size: {final_out.stat().st_size} bytes")


if __name__ == "__main__":
    test_compositor_end_to_end_clip()
