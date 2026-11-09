"""Production script to generate the 4th Audience-Driven Short:
The Survivorship Bias (WWII Abraham Wald Bomber Armor Paradox).
Executes the approved multi-source retrieval, Muse Spark 1.3 Contributor vision reranking,
and procedural diagram engine.
Saves to output/final_shorts/04_survivorship_bias.mp4
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

    topic = "The Survivorship Bias: Why Armor Was Placed on the Wrong Parts of WWII Bombers"
    format_type = "mystery_breakdown"
    angle = "Why military engineers reinforced bullet-riddled bomber wings until Abraham Wald proved the armor belonged where the bullet holes WEREN'T."
    output_path = final_dir / "04_survivorship_bias.mp4"

    print("\n" + "=" * 75)
    print(f"EVALUATING & GENERATING 4TH AUDIENCE-DRIVEN SHORT")
    print(f"Topic:  {topic}")
    print(f"Format: {format_type}")
    print("=" * 75)

    eval_res = evaluator.evaluate(topic)
    print(f"  * Topic Rubric Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")

    res = agent.create_short(
        topic=topic,
        format_type=format_type,
        angle=angle,
        skip_evaluation=True,
        target_duration=35.0,
        explicit_output_path=output_path,
    )
    res.evaluation = eval_res

    print("\n" + "=" * 75)
    print(f"[SUCCESS] 4th Short Successfully Rendered: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.1f}s | Score: {eval_res.total_score}/100")
    print("=" * 75)


if __name__ == "__main__":
    main()
