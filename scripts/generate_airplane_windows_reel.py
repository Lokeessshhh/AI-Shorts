"""Master Production Script for Airplane Windows Short with Unconstrained Visual Topology.
Generates: output/final_shorts/09_airplane_windows_unconstrained.mp4
Features:
- LLM has full creative freedom on visual representation
- Dynamic visual topology (engineering stress / structural failure)
- 90% real archival media (1950s de Havilland Comet archives), 10% custom graphic
- Opening hook is 100% real imagery
- Warm editorial studio canvas (zero dark voids)
- Hormozi word-level ASS subtitles
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

    topic = "Why commercial airplane windows are strictly rounded instead of square"
    format_type = "mystery_breakdown"
    angle = "In 1953, square windows caused two passenger jets to disintegrate mid-air, baffling engineers until a micro-tear revealed corner pressure physics."
    output_path = final_dir / "09_airplane_windows_unconstrained.mp4"

    print("\n" + "=" * 75)
    print("PRODUCING REEL WITH UNCONSTRAINED VISUAL FREEDOM ENGINE")
    print(f"Topic:  {topic}")
    print(f"Target: {output_path.name}")
    print("=" * 75)

    res = agent.create_short(
        topic=topic,
        format_type=format_type,
        angle=angle,
        skip_evaluation=True,
        target_duration=32.0,
        explicit_output_path=output_path,
    )

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Reel Rendered: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.1f}s")
    print("=" * 75)


if __name__ == "__main__":
    main()
