"""Production runner: Evaluates and generates 3 complete, audience-driven faceless Shorts
across the 3 narrative formats:
- Video 1: Counter-Intuitive Truth (Business & Finance)
- Video 2: Mystery Breakdown (Aviation & Engineering History)
- Video 3: Psychological Dilemma (Human Behavior & Social Paradox)
"""

import sys
import time
from pathlib import Path

# Set up path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent
from src.pipeline.topic_evaluator import TopicEvaluator

CANDIDATES = [
    {
        "format": "counter_intuitive_truth",
        "topic": "Why razor blade companies deliberately sell handles at an 80% loss",
        "angle": "Expose the 'Razor and Blades' monopoly trap that costs consumers $120 a year for 50 cents of metal.",
    },
    {
        "format": "mystery_breakdown",
        "topic": "Why commercial airplane windows are strictly rounded instead of square",
        "angle": "In 1953, square windows caused two passenger jets to disintegrate mid-air, baffling engineers until a micro-tear revealed corner pressure physics.",
    },
    {
        "format": "psychological_dilemma",
        "topic": "The Pratfall Effect: Why making clumsy mistakes secretly makes people like you more",
        "angle": "Flawless people trigger subconscious intimidation and distrust; spilling coffee actually makes competent people dramatically more charming.",
    },
]


def main():
    agent = FacelessShortsAgent()
    evaluator = TopicEvaluator()

    results = []

    print("\n" + "=" * 70)
    print("PHASE 1: EVALUATING CANDIDATE TOPICS AGAINST 100-POINT AUDIENCE RUBRIC")
    print("=" * 70)

    for idx, c in enumerate(CANDIDATES, 1):
        print(f"\n[EVAL {idx}/3] Evaluating: '{c['topic']}'")
        evaluation = evaluator.evaluate(c["topic"])
        print(f"  * Total Score: {evaluation.total_score}/100")
        print(f"  * Approved:    {evaluation.approved}")
        print(f"  * Target Aud:  {evaluation.target_audience}")
        for k, crit in evaluation.criteria_breakdown.items():
            print(f"    - {crit.name} ({crit.max_score}pts): {crit.score} pts -> {crit.feedback[:65]}...")

        if not evaluation.approved:
            print(f"  [ERROR] Candidate {idx} rejected by rubric!")
            sys.exit(1)

        c["evaluation"] = evaluation

    print("\n" + "=" * 70)
    print("PHASE 2: RENDERING 3 COMPLETE 1080x1920 9:16 HIGH-RETENTION SHORTS")
    print("=" * 70)

    for idx, c in enumerate(CANDIDATES, 1):
        print(f"\n>>> RENDERING VIDEO {idx}/3: [{c['format'].upper()}] <<<")
        res = agent.create_short(
            topic=c["topic"],
            format_type=c["format"],
            angle=c["angle"],
            skip_evaluation=True,  # Already evaluated
            target_duration=34.0,
        )
        res.evaluation = c["evaluation"]
        results.append(res)
        print(f"\n>>> SUCCESS: Video {idx} Rendered: {res.video_path.name} ({res.duration_seconds:.1f}s)")

    print("\n" + "=" * 70)
    print("ALL 3 VIDEOS GENERATED SUCCESSFULLY!")
    print("=" * 70)
    for idx, r in enumerate(results, 1):
        print(f"Video {idx}: {r.video_path} ({r.duration_seconds:.1f}s) | Score: {r.evaluation.total_score}/100")


if __name__ == "__main__":
    main()
