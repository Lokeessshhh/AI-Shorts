"""Autonomous Production Runner: Discovers its own topic, evaluates via 100-pt rubric, and renders full documentary Reel.
Target: output/final_shorts/08_autonomous_champion.mp4
Features:
- No hardcoded topic: LLM brainstorms 5 high-retention candidates
- 100-Point Topic Evaluation Gate automatically selects the highest-scoring topic
- 90% Real Archival Media / 10% Dynamic Infographic ratio
- Image-based opening hook
- Maximum 1-2 images per sentence (smooth documentary pacing)
- Bright editorial studio background with borderless visual cards
- Dynamic word-level Hormozi subtitles
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent


def main():
    agent = FacelessShortsAgent()
    final_dir = ROOT_DIR / "output" / "final_shorts"
    final_dir.mkdir(parents=True, exist_ok=True)

    output_path = final_dir / "08_autonomous_champion.mp4"

    print("\n" + "=" * 75)
    print("RUNNING 100% AUTONOMOUS AI SHORTS GENERATOR (NO TOPIC SUPPLIED)")
    print("=" * 75)

    # Call create_short with topic=None!
    res = agent.create_short(
        topic=None,
        target_duration=32.0,
        explicit_output_path=output_path,
    )

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Autonomous Reel Rendered: {output_path.name}")
    print(f"Topic:    {res.title}")
    print(f"Duration: {res.duration_seconds:.1f}s")
    print("=" * 75)


if __name__ == "__main__":
    main()
