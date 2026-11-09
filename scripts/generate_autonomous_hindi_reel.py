"""Autonomous Hindi Mode Production Script (No Topic Supplied).
Generates: output/final_shorts/14_autonomous_hindi_champion.mp4
Features:
- 100% Autonomous Topic Discovery via 100-Point Audience Retention Rubric
- Natural conversational Indian Hindi voiceover (Microsoft Edge Neural hi-IN-MadhurNeural)
- 100% Hinglish (Roman Hindi) Kinetic Typography Subtitles
- 100% Free Zero-Trial Acoustic Word Alignment (Zero Whisper dependency)
- Dynamic Context-Aware Soundtrack via AI Music Director
- Golden-Ratio Upper-Third Camera Motion
- Strictly 25-30s runtime target
"""

import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent


def main():
    agent = FacelessShortsAgent()
    final_dir = ROOT_DIR / "output" / "final_shorts"
    final_dir.mkdir(parents=True, exist_ok=True)

    output_path = final_dir / "14_autonomous_hindi_champion.mp4"

    print("\n" + "=" * 80)
    print("PRODUCING AUTONOMOUS HINDI REEL (NO TOPIC SUPPLIED - AUTO-DISCOVERY ACTIVE)")
    print("=" * 80)

    start_t = time.time()
    res = agent.create_short(
        topic=None,  # Autonomous Topic Discovery
        language="hi",  # Hindi Mode
        target_duration=27.5,
        explicit_output_path=output_path,
    )
    elapsed = time.time() - start_t

    print("\n" + "=" * 80)
    print(f"[SUCCESS] Autonomous Hindi Reel Rendered in {elapsed:.1f}s: {output_path.name}")
    print(f"Title:         {res.title}")
    print(f"Duration:      {res.duration_seconds:.2f}s | Language: {res.language.upper()}")
    print(f"Spoken Hook:   {res.script.hook}")
    print(f"Hinglish Hook: {res.script.text_hook}")
    if res.score_plan:
        print(f"Soundtrack:    {res.score_plan.track_title} [{res.score_plan.genre}]")
        print(f"Audio Score:   Base Vol {res.score_plan.base_bgm_volume:.2f}, {len(res.score_plan.volume_keyframes)} Keyframes")
    print("=" * 80)


if __name__ == "__main__":
    main()
