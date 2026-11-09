"""Master Production Script for Cinematic Storytelling Reel (Phase 1-4 Upgrade).
Generates: output/final_shorts/10_cinematic_story_champion.mp4
Features:
- Dynamic narrative architecture with progressive revelation
- Strict 25-30s duration budgeting (68-82 words, ~155 WPM)
- Kinetic Typography Studio (88pt bold typography, spring pop-overshoot, semantic coloring)
- Cinematic Camera Engine (Golden-Ratio upper-third framing, 5 distinct camera moves)
- Audio-Visual Punctuation (60ms J-Cut sonic pre-emption, speech-reactive sidechain ducking)
- 100% dynamic, unconstrained visual direction with Muse Spark 1.3 verification
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent
from src.pipeline.topic_evaluator import TopicEvaluator


def main():
    agent = FacelessShortsAgent()
    evaluator = TopicEvaluator()

    final_dir = ROOT_DIR / "output" / "final_shorts"
    final_dir.mkdir(parents=True, exist_ok=True)

    topic = "The 1953 Comet Disasters: How Microscopic Window Cracks Changed Aviation Forever"
    format_type = "mystery_breakdown"
    angle = "In 1953, two passenger jets exploded mid-air with zero warning, baffling scientists until a microscopic corner tear revealed the deadly physics of square windows."
    output_path = final_dir / "10_cinematic_story_champion.mp4"

    print("\n" + "=" * 75)
    print("PRODUCING MASTER CINEMATIC REEL (DYNAMIC STORYTELLING & KINETIC CAPTIONS)")
    print(f"Topic:  {topic}")
    print(f"Target: {output_path.name}")
    print("=" * 75)

    eval_res = evaluator.evaluate(topic)
    print(f"  * 100-Point Topic Evaluation Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")

    res = agent.create_short(
        topic=topic,
        format_type=format_type,
        angle=angle,
        skip_evaluation=True,
        target_duration=28.0,
        explicit_output_path=output_path,
    )
    res.evaluation = eval_res

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Cinematic Reel Rendered: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.1f}s | Score: {eval_res.total_score}/100")
    print("=" * 75)


if __name__ == "__main__":
    main()
