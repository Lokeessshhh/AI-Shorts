"""Master Production Script for Bright Editorial Short (80% Media / 20% Diagram).
Generates: output/final_shorts/06_cobra_effect_bright_editorial.mp4
Features:
- Bright Editorial Studio aesthetic (off-white/cream, zero black voids)
- Large, prominent visual media (980x1180 cards occupying 91% width)
- Fast visual pacing (0.8s - 1.4s per shot)
- 80% real historical/documentary media, 20% dynamic infographic
- Muse Spark 1.3 Contributor vision verification
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

    topic = "The Cobra Effect: Why the British Government Accidentally Bred Thousands of Venomous Snakes"
    format_type = "mystery_breakdown"
    angle = "How offering cash bounties for dead cobras created an entire industry of secret snake breeders, leading to wild citywide chaos when the policy was abruptly cancelled."
    output_path = final_dir / "06_cobra_effect_bright_editorial.mp4"

    print("\n" + "=" * 75)
    print("PRODUCING BRIGHT EDITORIAL REEL (80% MEDIA / 20% DIAGRAM)")
    print(f"Topic:  {topic}")
    print(f"Target: {output_path.name}")
    print("=" * 75)

    eval_res = evaluator.evaluate(topic)
    print(f"  * Topic Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")

    res = agent.create_short(
        topic=topic,
        format_type=format_type,
        angle=angle,
        skip_evaluation=True,
        target_duration=32.0,
        explicit_output_path=output_path,
    )
    res.evaluation = eval_res

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Bright Editorial Reel Rendered: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.1f}s | Score: {eval_res.total_score}/100")
    print("=" * 75)


if __name__ == "__main__":
    main()
