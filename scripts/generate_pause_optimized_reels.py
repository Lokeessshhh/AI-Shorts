"""
Production and Verification Script for Critical Audio Pause Optimization across English & Hindi Modes.

Generates:
1. output/final_shorts/15_optimized_pause_english.mp4
2. output/final_shorts/16_optimized_pause_hindi.mp4

Measures:
- Pre-trim leading/trailing silences removed
- Dynamic inter-sentence breath pause distribution (120ms - 220ms)
- End-to-end silence detection on rendered videos
- Word-level synchronization with kinetic typography captions
"""

import sys
import time
import subprocess
from pathlib import Path
import imageio_ffmpeg

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()


def measure_audio_silences(video_or_audio_path: Path):
    cmd = [
        ffmpeg_exe, "-i", str(video_or_audio_path),
        "-af", "silencedetect=noise=-34dB:d=0.08",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    silences = []
    for line in res.stderr.splitlines():
        if "silencedetect" in line and "silence_duration" in line:
            parts = line.split("silence_duration: ")
            dur = float(parts[1].split()[0])
            silences.append(dur)
    return silences


def extract_qa_frames(video_path: Path, output_dir: Path, prefix: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamps = [1.5, 6.0, 12.0, 18.0]
    frame_paths = []
    for i, ts in enumerate(timestamps):
        out_f = output_dir / f"{prefix}_frame_{i+1}_{int(ts*1000)}ms.jpg"
        cmd = [
            ffmpeg_exe, "-y",
            "-ss", str(ts),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(out_f)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if out_f.exists():
            frame_paths.append(out_f)
    return frame_paths


def main():
    agent = FacelessShortsAgent()
    final_dir = ROOT_DIR / "output" / "final_shorts"
    final_dir.mkdir(parents=True, exist_ok=True)
    qa_dir = ROOT_DIR / "output" / "qa_frames"
    qa_dir.mkdir(parents=True, exist_ok=True)

    # 1. English Mode Production
    print("\n" + "=" * 80)
    print("PRODUCING TEST 1: ENGLISH MODE (NATURAL PAUSE FLOW)")
    print("=" * 80)

    en_topic = "The Microscopic Flaw in Square Airplane Windows"
    en_format = "mystery_breakdown"
    en_angle = "In 1954, early jetliners shattered mid-air until microscopic stress cracks revealed the deadly physics of square window corners."
    en_output = final_dir / "15_optimized_pause_english.mp4"

    t0 = time.time()
    en_res = agent.create_short(
        topic=en_topic,
        language="en",
        format_type=en_format,
        angle=en_angle,
        skip_evaluation=True,
        target_duration=26.5,
        explicit_output_path=en_output,
    )
    t_en_dur = time.time() - t0
    en_silences = measure_audio_silences(en_output)
    en_frames = extract_qa_frames(en_output, qa_dir, "15_english")

    print(f"\n[EN RESULT] Rendered in {t_en_dur:.1f}s: {en_output.name} ({en_res.duration_seconds:.2f}s)")
    print(f"Detected Silences in Final Audio: {[f'{s:.3f}s' for s in en_silences]}")
    print(f"Max Silence: {max(en_silences) if en_silences else 0.0:.3f}s")

    # 2. Hindi Mode Production
    print("\n" + "=" * 80)
    print("PRODUCING TEST 2: HINDI MODE (NATURAL PAUSE FLOW + HINGLISH CAPTIONS)")
    print("=" * 80)

    hi_topic = "The 1902 Cobra Effect: How a Bounty on Snakes Backfired"
    hi_format = "counter_intuitive_truth"
    hi_angle = "In British colonial Delhi, offering cash bounties for dead venomous cobras created a lucrative breeding scheme that made the snake population explode."
    hi_output = final_dir / "16_optimized_pause_hindi.mp4"

    t1 = time.time()
    hi_res = agent.create_short(
        topic=hi_topic,
        language="hi",
        format_type=hi_format,
        angle=hi_angle,
        skip_evaluation=True,
        target_duration=27.5,
        explicit_output_path=hi_output,
    )
    t_hi_dur = time.time() - t1
    hi_silences = measure_audio_silences(hi_output)
    hi_frames = extract_qa_frames(hi_output, qa_dir, "16_hindi")

    print(f"\n[HI RESULT] Rendered in {t_hi_dur:.1f}s: {hi_output.name} ({hi_res.duration_seconds:.2f}s)")
    print(f"Detected Silences in Final Audio: {[f'{s:.3f}s' for s in hi_silences]}")
    print(f"Max Silence: {max(hi_silences) if hi_silences else 0.0:.3f}s")

    print("\n" + "=" * 80)
    print("AUDIO PAUSE OPTIMIZATION BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"1. English Mode Video: {en_output} ({en_res.duration_seconds:.2f}s)")
    print(f"   Max silence: {max(en_silences) if en_silences else 0.0:.3f}s | Silences: {[f'{s:.3f}s' for s in en_silences]}")
    print(f"   QA Frames: {[f.name for f in en_frames]}")
    print(f"2. Hindi Mode Video:   {hi_output} ({hi_res.duration_seconds:.2f}s)")
    print(f"   Max silence: {max(hi_silences) if hi_silences else 0.0:.3f}s | Silences: {[f'{s:.3f}s' for s in hi_silences]}")
    print(f"   QA Frames: {[f.name for f in hi_frames]}")
    print("=" * 80)


if __name__ == "__main__":
    main()
