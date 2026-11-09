"""Master Production Generator for the 3 Final Shorts.
Executes the approved multi-source discovery, Muse Spark 1.3 Contributor vision reranking,
and procedural fallback engine.
Saves to output/final_shorts/:
- 01_razor_and_blades.mp4
- 02_de_havilland_comet.mp4
- 03_pratfall_effect.mp4
"""

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent
from src.pipeline.topic_evaluator import TopicEvaluator

FINAL_SHORTS = [
    {
        "id": "01",
        "topic": "The Razor-and-Blades Business Model: Why handles are sold at an 80% loss",
        "format": "counter_intuitive_truth",
        "angle": "How companies sell the main product cheaply and make recurring profits from consumable blade cartridges.",
        "output_filename": "01_razor_and_blades.mp4",
    },
    {
        "id": "02",
        "topic": "The De Havilland Comet Disasters: How square windows caused structural fatigue",
        "format": "mystery_breakdown",
        "angle": "How 1950s passenger jets suffered catastrophic mid-air disintegration due to metal fatigue at 90-degree square window corners.",
        "output_filename": "02_de_havilland_comet.mp4",
    },
    {
        "id": "03",
        "topic": "The Pratfall Effect: Why competent people become more likable after making a small mistake",
        "format": "psychological_dilemma",
        "angle": "Why flawless competence triggers subconscious intimidation, whereas spilling coffee or making a small blunder makes competent individuals significantly more relatable.",
        "output_filename": "03_pratfall_effect.mp4",
    },
]


def main():
    agent = FacelessShortsAgent()
    evaluator = TopicEvaluator()

    final_dir = ROOT_DIR / "output" / "final_shorts"
    final_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 75)
    print("STARTING OMNI-SOURCE PRODUCTION & MUSE SPARK 1.3 VISION RERANKING")
    print("=" * 75)

    generated_results = []

    for item in FINAL_SHORTS:
        print(f"\n" + "-" * 75)
        print(f"PRODUCING VIDEO {item['id']}: [{item['format'].upper()}] {item['topic']}")
        print("-" * 75)

        # 1. 100-Point Topic Evaluation
        eval_res = evaluator.evaluate(item["topic"])
        print(f"  * Topic Rubric Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")

        out_path = final_dir / item["output_filename"]

        # 2. Render Short with Multi-Source Discovery & Muse Spark Vision Verification
        res = agent.create_short(
            topic=item["topic"],
            format_type=item["format"],
            angle=item["angle"],
            skip_evaluation=True,  # Evaluated above
            target_duration=35.0,
            explicit_output_path=out_path,
        )
        res.evaluation = eval_res
        generated_results.append(res)
        print(f"\n[SUCCESS] Rendered: {out_path.name} ({res.duration_seconds:.1f}s)")

    print("\n" + "=" * 75)
    print("ALL 3 FINAL SHORTS SUCCESSFULLY RENDERED IN output/final_shorts/!")
    print("=" * 75)
    for r in generated_results:
        print(f"  * {r.video_path.name} | Duration: {r.duration_seconds:.1f}s | Score: {r.evaluation.total_score}/100")


if __name__ == "__main__":
    main()
