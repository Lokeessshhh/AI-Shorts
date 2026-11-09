"""Master Production Script for Context-Aware Dynamic Music & Audio Engine Reel.
Generates: output/final_shorts/11_dynamic_music_champion.mp4
Features:
- 100% Dynamic, video-aware background music selection via LLM Music Director
- Narrative-following volume automation (Hook -> Build -> Climax Swell -> Payoff Resolve)
- Vocal clarity via spectral EQ carving (-4dB @ 2.5kHz) and adaptive speech sidechain ducking
- Selective, context-aware 60ms J-cut sound design cues (no repetitive whoosh fatigue)
- Strict 25-30s duration budgeting (68-82 words, ~155 WPM)
- Kinetic Typography Studio (88pt bold typography, spring pop-overshoot, semantic coloring)
- Golden-Ratio upper-third camera dynamics with 100% dynamic visual selection
"""

import sys
import time
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

    topic = "The 1902 Cobra Effect: How a Bounty on Snakes Created a Million More"
    format_type = "counter_intuitive_truth"
    angle = "In British colonial Delhi, the government paid citizens cash bounties for dead cobras, triggering an unexpected economic exploit that made the snake problem ten times worse."
    output_path = final_dir / "11_dynamic_music_champion.mp4"

    print("\n" + "=" * 80)
    print("PRODUCING MASTER REEL: FULLY DYNAMIC, VIDEO-AWARE AUDIO & SCORE ENGINE")
    print(f"Topic:  {topic}")
    print(f"Target: {output_path.name}")
    print("=" * 80)

    eval_res = evaluator.evaluate(topic)
    print(f"  * 100-Point Topic Evaluation Score: {eval_res.total_score}/100 | Approved: {eval_res.approved}")

    start_t = time.time()
    res = agent.create_short(
        topic=topic,
        format_type=format_type,
        angle=angle,
        skip_evaluation=True,
        target_duration=27.5,
        explicit_output_path=output_path,
    )
    res.evaluation = eval_res
    dur = time.time() - start_t

    print("\n" + "=" * 80)
    print(f"[SUCCESS] Dynamic Music Reel Rendered in {dur:.1f}s: {output_path.name}")
    print(f"Duration: {res.duration_seconds:.2f}s | Score: {eval_res.total_score}/100")
    if res.score_plan:
        print(f"Soundtrack: {res.score_plan.track_title} [{res.score_plan.genre}]")
        print(f"Rationale:  {res.score_plan.score_rationale}")
        print(f"Dynamics:   Base Vol {res.score_plan.base_bgm_volume:.2f}, {len(res.score_plan.volume_keyframes)} Keyframes, {len(res.score_plan.sfx_cues)} SFX Cues")
    print("=" * 80)


if __name__ == "__main__":
    main()
