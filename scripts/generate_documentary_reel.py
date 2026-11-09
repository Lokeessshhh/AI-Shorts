"""Master Production Script for Image-First Documentary Reel (90% Real Media / 10% Dynamic Graphic).
Generates: output/final_shorts/07_cobra_effect_documentary.mp4
Features:
- Image-First Documentary editing: 90% real archival photography/media, 10% dynamic infographic
- Opening ALWAYS image-based (no diagrams or concept cards in hook)
- Maximum 1 or 2 images per narration sentence (smooth pacing, no rapid flashing)
- Large, clean framing (980x1180 cards on warm editorial studio background, zero dark voids)
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
    output_path = final_dir / "07_cobra_effect_documentary.mp4"

    print("\n" + "=" * 75)
    print("PRODUCING IMAGE-FIRST DOCUMENTARY REEL (90% MEDIA / 10% DIAGRAM)")
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
    print(f"[SUCCESS] Image-First Documentary Reel Rendered: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.1f}s | Score: {eval_res.total_score}/100")
    print("=" * 75)


if __name__ == "__main__":
    main()
