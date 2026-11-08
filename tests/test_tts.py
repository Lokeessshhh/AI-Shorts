import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.voice.tts import TTSEngine


def test_edge_tts_synthesis():
    engine = TTSEngine(voice="en-US-ChristopherNeural")
    test_text = "Have you ever wondered why you cannot remember anything from when you were a baby?"
    result = engine.synthesize(text=test_text, output_filename="test_voice.mp3")

    assert result.audio_path.exists()
    assert result.duration_seconds > 2.0
    print(f"\n[PASSED] TTS synthesized: {result.audio_path.name}")
    print(f"Duration: {result.duration_seconds:.2f}s | Voice: {result.voice_name}")


if __name__ == "__main__":
    test_edge_tts_synthesis()
