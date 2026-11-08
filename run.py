import sys
import argparse
from pathlib import Path

# Force UTF-8 stdout/stderr for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.pipeline.faceless_agent import FacelessShortsAgent


def main():
    parser = argparse.ArgumentParser(
        description="All-in-One AI Shorts Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --mode facts --topic "3 Dark Psychology Secrets"
  python run.py --mode facts --topic "The Bizarre Reason Why Rome Fell" --voice en-US-ChristopherNeural
        """,
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="story",
        choices=["facts", "gameplay", "story", "clipper"],
        help="Content mode (story = Mode 2: Dev vs Claude Encyclopedic Media, facts = Mode 1, clipper = Mode 3)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="The topic, premise, or title of the Short",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="Voice name for edge-tts (default: en-US-ChristopherNeural)",
    )

    args = parser.parse_args()

    if args.mode == "facts":
        agent = FacelessShortsAgent()
        result = agent.create_short(topic=args.topic, custom_voice=args.voice)
        print(f"\n[DONE] Render complete: {result.video_path}")
    elif args.mode in ("story", "gameplay"):
        from src.story.dev_claude_pipeline import DevClaudePipeline
        pipeline = DevClaudePipeline()
        result = pipeline.run(topic=args.topic)
        print(f"\n[DONE] Render complete: {result['video_path']}")
    elif args.mode == "clipper":
        print("\n[INFO] Mode 3 (Smart Podcast Clipper) is executed via main.py --mode clipper --url <URL>")


if __name__ == "__main__":
    main()
