"""Production test script for the 100% Dynamic, Topic-Independent Visual Engine.
Runs the complete autonomous pipeline on a fresh, unseen topic:
'The Cobra Effect: Why the British Government Accidentally Bred Thousands of Venomous Snakes'
Saves output to: output/final_shorts/05_cobra_effect_dynamic.mp4
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
    output_path = final_dir / "05_cobra_effect_dynamic.mp4"

    print("\n" + "=" * 75)
    print("AUTONOMOUS PRODUCTION OF 100% DYNAMIC SHORT")
    print(f"Topic:  {topic}")
    print(f"Format: {format_type}")
    print("=" * 75)

    eval_res = evaluator.evaluate(topic)
    print(f"  * Topic Rubric Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")

    # Pure autonomous pipeline execution
    res = agent.create_short(
        topic=topic,
        format_type=format_type,
        angle=angle,
        skip_evaluation=True,
        target_duration=36.0,
        explicit_output_path=output_path,
    )
    res.evaluation = eval_res

    print("\n" + "=" * 75)
    print(f"[SUCCESS] Dynamic Reel Generated: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.1f}s | Score: {eval_res.total_score}/100")
    print("=" * 75)


if __name__ == "__main__":
    main()
