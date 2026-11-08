"""Batch generator for Mode 2 Ultimate Reddit Story Shorts."""

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.story.pipeline import Mode2StoryPipeline

STORIES = [
    {
        "topic": "Finding a secret safe hidden under the floorboards of our newly bought house",
        "layout": "floating_card",
        "desc": "Mystery & Suspense: Hidden House Safe",
    },
    {
        "topic": "My coworker tried to take credit for my six month project in front of the CEO",
        "layout": "floating_card",
        "desc": "Workplace Drama: CEO Project Showdown",
    },
    {
        "topic": "My mother-in-law secretly canceled our wedding catering to save money",
        "layout": "split_screen",
        "desc": "Family Drama: Wedding Catering Sabotage",
    },
]


def main():
    pipeline = Mode2StoryPipeline()
    results = []
    print("=" * 60)
    print(f"[BATCH] Starting generation of {len(STORIES)} Ultimate Mode 2 Shorts")
    print("=" * 60)

    for i, s in enumerate(STORIES, start=1):
        print(f"\n>>> GENERATING SHORT #{i}/{len(STORIES)}: {s['desc']} <<<")
        t0 = time.time()
        res = pipeline.run(
            topic=s["topic"],
            layout=s["layout"],
            gameplay_style="minecraft",
        )
        elapsed = time.time() - t0
        res["elapsed"] = elapsed
        res["desc"] = s["desc"]
        results.append(res)
        print(f"[BATCH] Completed Short #{i} in {elapsed:.1f}s -> {res['video_path'].name}")

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Batch Generation Complete: {len(results)} Shorts Generated!")
    print("=" * 60)
    for i, r in enumerate(results, start=1):
        print(f"#{i} [{r['layout']}]: {r['video_path']}")


if __name__ == "__main__":
    main()
