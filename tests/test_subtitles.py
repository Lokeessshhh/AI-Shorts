import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import config
from src.subtitles.ass_builder import ASSSubtitleBuilder, WordTimestamp
from src.subtitles.whisper_stt import WhisperTranscriber


def test_ass_subtitle_builder():
    builder = ASSSubtitleBuilder()
    words = [
        WordTimestamp(word="CASINOS", start=0.0, end=0.4),
        WordTimestamp(word="ARE", start=0.4, end=0.7),
        WordTimestamp(word="NOT", start=0.7, end=1.0),
        WordTimestamp(word="BUILT", start=1.0, end=1.3),
        WordTimestamp(word="FOR", start=1.3, end=1.5),
        WordTimestamp(word="LUCK", start=1.5, end=2.0),
    ]

    ass_output = config.temp_dir / "test_captions.ass"
    builder.build_ass(words, ass_output)

    assert ass_output.exists()
    content = ass_output.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "Style: Hormozi" in content
    assert "Dialogue:" in content
    assert "\\c&H0000FFFF&" in content  # Karaoke highlight color

    print(f"\n[PASSED] ASS Subtitles built successfully: {ass_output.name}")
    print(f"File size: {ass_output.stat().st_size} bytes")


def test_strictly_no_overlapping_dialogues():
    builder = ASSSubtitleBuilder()
    # Deliberately overlapping input timestamps (typical of speech aligners)
    words = [
        WordTimestamp(word="LAUNCHING", start=0.0, end=0.45),
        WordTimestamp(word="CHATGPT", start=0.35, end=0.85),
        WordTimestamp(word="WAS", start=0.75, end=1.15),
        WordTimestamp(word="KIND", start=1.05, end=1.45),
        WordTimestamp(word="OF", start=1.35, end=1.75),
        WordTimestamp(word="AN", start=1.65, end=2.05),
        WordTimestamp(word="EXAMPLE", start=1.95, end=2.45),
    ]

    ass_output = config.temp_dir / "test_timing.ass"
    builder.build_ass(words, ass_output)

    content = ass_output.read_text(encoding="utf-8")
    dialogues = [line for line in content.splitlines() if line.startswith("Dialogue:")]

    assert len(dialogues) > 0
    # Parse start and end times for all dialogues
    def parse_ass_time(ts: str) -> float:
        h, m, rest = ts.split(":")
        s = float(rest)
        return int(h) * 3600 + int(m) * 60 + s

    for i in range(len(dialogues) - 1):
        curr_parts = dialogues[i].split(",")
        next_parts = dialogues[i + 1].split(",")
        curr_end = parse_ass_time(curr_parts[2])
        next_start = parse_ass_time(next_parts[1])
        # MUST NEVER OVERLAP
        assert curr_end <= next_start + 0.001, f"Overlap detected between dialogue {i} (end={curr_end}) and {i+1} (start={next_start})"

    # Verify inline emoji is present in dialogue text
    assert any("🚀" in d or "🤖" in d for d in dialogues)


def test_whisper_transcription():
    audio_file = config.temp_dir / "test_voice.mp3"
    if not audio_file.exists():
        print("[SKIP] test_voice.mp3 does not exist, run test_tts.py first")
        return

    transcriber = WhisperTranscriber(model_size="base")
    words = transcriber.transcribe_words(audio_file)

    assert len(words) > 0
    print(f"\n[PASSED] Whisper transcribed {len(words)} words:")
    for w in words[:6]:
        print(f"  {w.start:.2f}s - {w.end:.2f}s: {w.word}")


if __name__ == "__main__":
    test_ass_subtitle_builder()
    test_whisper_transcription()
