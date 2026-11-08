"""AI Shorts Production CLI Engine
Supported Modes:
  - Mode 1: Faceless Narrative & Facts (LLM Script + Edge-TTS + ASS Subtitles + Pexels B-Roll + FFmpeg)
  - Mode 2: Reddit Stories & Gameplay (Zero-Key Scraper / AI Storyteller + Pillow Card + Gameplay + 50/50 Split)
  - Mode 3: Video & Podcast Smart Clipper (yt-dlp + faster-whisper + OpenRouter Highlights + OpenCV Reframe + Polish)
  - Mode auto: Autonomous Trend Scout & 3-Mode Batch Orchestrator (Zero input, scans Google Trends, HN & YouTube)
"""

import sys
import time
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def parse_interval_seconds(interval_str: str) -> float:
    """Parse time interval string into seconds (e.g. 6h, 30m, 3600s, 1d)."""
    s = interval_str.strip().lower()
    if s.endswith("h"):
        return float(s[:-1]) * 3600
    elif s.endswith("m"):
        return float(s[:-1]) * 60
    elif s.endswith("d"):
        return float(s[:-1]) * 86400
    elif s.endswith("s"):
        return float(s[:-1])
    return float(s)


def main():
    parser = argparse.ArgumentParser(
        description="AI Shorts Engine: Automated Short-Form Content Generator (Modes 1, 2, 3 & Auto)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["facts", "story", "clipper", "auto"],
        default="facts",
        help="Content mode: 'facts' (Mode 1), 'story' (Mode 2), 'clipper' (Mode 3), or 'auto' (Autonomous 3-Mode Batch)",
    )

    # General / Shared Arguments
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="[Mode 1 & 2] Premise, topic, or concept to generate",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="[Mode 1 & 2] edge-tts voice name (e.g. en-US-ChristopherNeural, en-US-AndrewNeural)",
    )
    parser.add_argument(
        "--bgm",
        type=str,
        default=None,
        help="[Mode 1 & 2] Path to custom background music audio file",
    )

    # Mode 2 Story Arguments
    parser.add_argument(
        "--format",
        type=str,
        choices=["dev_claude", "reddit"],
        default="dev_claude",
        help="[Mode 2] Story format: 'dev_claude' (Developer vs Claude 2-person dialogue) or 'reddit' (Reddit narrative)",
    )
    parser.add_argument(
        "--reddit",
        type=str,
        default=None,
        help="[Mode 2] Reddit post URL to scrape and narrate",
    )
    parser.add_argument(
        "--subreddit",
        type=str,
        default=None,
        help="[Mode 2] Subreddit to pull top trending story from (e.g. AITA, AskReddit, confession)",
    )
    parser.add_argument(
        "--gameplay",
        type=str,
        choices=["random", "gta", "subway", "trackmania", "minecraft", "satisfying_asmr", "beamng", "temple_run", "marble_run"],
        default="random",
        help="[Mode 2] Background gameplay style (default: random dynamic download)",
    )
    parser.add_argument(
        "--layout",
        type=str,
        default=None,
        help="[Mode 2 & 3] Visual layout: 'split_screen', 'floating_card', 'auto', or 'solo'",
    )

    # Mode 3 Clipper Arguments
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="[Mode 3] YouTube video URL to download and clip",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="[Mode 3] Path to local video file to clip",
    )
    parser.add_argument(
        "--clips",
        type=int,
        default=3,
        help="[Mode 3 & Auto] Number of viral shorts to extract (default: 3)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=30.0,
        help="[Mode 3] Minimum duration in seconds per clip (default: 30.0)",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=60.0,
        help="[Mode 3] Maximum duration in seconds per clip (default: 60.0)",
    )

    # Autonomous Orchestrator Arguments
    parser.add_argument(
        "--loop",
        action="store_true",
        help="[Mode auto] Run continuously in the background on a repeating schedule",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="6h",
        help="[Mode auto] Sleep interval between batches when --loop is enabled (e.g. 6h, 12h, 30m)",
    )
    parser.add_argument(
        "--skip-mode3",
        action="store_true",
        help="[Mode auto] Skip Mode 3 podcast clipper in the batch run",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Automatically publish finished premier shorts to YouTube and Instagram",
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=["youtube", "instagram"],
        default=None,
        help="Platforms to publish to: 'youtube', 'instagram', or both (default: all authenticated)",
    )
    parser.add_argument(
        "--publish-batch",
        type=str,
        default=None,
        help="Publish an existing batch folder directly (e.g. output/batch_20261108_093648)",
    )
    parser.add_argument(
        "--keep-videos",
        action="store_true",
        help="Do NOT delete local MP4 video files after publishing (by default, local MP4s are cleaned up to save disk space)",
    )

    args = parser.parse_args()

    # Direct publishing of an existing batch
    if args.publish_batch:
        from src.publisher.batch_publisher import BatchPublisher
        publisher = BatchPublisher()
        publisher.publish_batch(
            batch_dir=Path(args.publish_batch),
            platforms=args.platforms,
            delete_after_upload=not args.keep_videos,
            delete_unselected_clips=not args.keep_videos,
        )
        return

    # Auto-detect mode if specific flags are passed
    if args.url or args.input:
        args.mode = "clipper"
    elif args.reddit or args.subreddit:
        args.mode = "story"

    # -------------------------------------------------------------
    # ROUTE: Mode auto (Autonomous Trend Scout & Batch Orchestrator)
    # -------------------------------------------------------------
    if args.mode == "auto":
        from src.automation.orchestrator import AutonomousShortsOrchestrator

        orchestrator = AutonomousShortsOrchestrator()
        interval_seconds = parse_interval_seconds(args.interval)

        while True:
            manifest = orchestrator.run_autonomous_batch(
                num_clipper_shorts=args.clips,
                skip_mode3=args.skip_mode3,
            )

            # Auto-publish to YouTube Shorts and Instagram Reels if requested
            if args.publish:
                from src.publisher.batch_publisher import BatchPublisher
                publisher = BatchPublisher()
                publisher.publish_batch(
                    batch_dir=Path(manifest["batch_dir"]),
                    platforms=args.platforms,
                    delete_after_upload=not args.keep_videos,
                    delete_unselected_clips=not args.keep_videos,
                )

            if not args.loop:
                break
            print(f"[LOOP SCHEDULER] Next batch scheduled in {args.interval} ({interval_seconds:.0f}s)...")
            time.sleep(interval_seconds)

    # -------------------------------------------------------------
    # ROUTE: Mode 2 (Developer vs Claude Dialogue OR Reddit Stories)
    # -------------------------------------------------------------
    elif args.mode == "story":
        if args.format == "dev_claude" and not (args.reddit or args.subreddit):
            from src.story.dev_claude_pipeline import DevClaudePipeline
            pipeline = DevClaudePipeline()
            result = pipeline.run(topic=args.topic, gameplay_style=args.gameplay)
            print(f"\n[SUCCESS] Mode 2 Developer vs Claude Short Created: {result['video_path']}")
        else:
            from src.story.pipeline import Mode2StoryPipeline

            pipeline = Mode2StoryPipeline()
            result = pipeline.run(
                reddit_url=args.reddit,
                subreddit=args.subreddit,
                topic=args.topic,
                gameplay_style=args.gameplay,
                voice=args.voice,
                layout=args.layout or "floating_card",
            )
            print(f"\n[SUCCESS] Mode 2 Story Short Created: {result['video_path']}")

    # -------------------------------------------------------------
    # ROUTE: Mode 3 (Podcast & Video Smart Clipper)
    # -------------------------------------------------------------
    elif args.mode == "clipper":
        source = args.url or args.input
        if not source:
            parser.error("Mode 'clipper' requires either --url <YouTube URL> or --input <Video Path>.")

        from src.clipper.pipeline import Mode3ClipperPipeline

        pipeline = Mode3ClipperPipeline()
        results = pipeline.run(
            source=source,
            num_clips=args.clips,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
            layout=args.layout,
        )
        print(f"\n[SUCCESS] Mode 3 Generated {len(results)} Shorts!")
        for r in results:
            print(f"  * #{r['rank']} ({r['viral_score']}/100): {r['video_path']}")

    # -------------------------------------------------------------
    # ROUTE: Mode 1 (Faceless Narrative & Facts)
    # -------------------------------------------------------------
    else:
        if not args.topic:
            parser.error("Mode 'facts' requires --topic <Topic String>.")

        from src.pipeline.faceless_agent import FacelessShortsAgent

        bgm_path = Path(args.bgm) if args.bgm else None
        agent = FacelessShortsAgent()
        result = agent.create_short(
            topic=args.topic,
            custom_voice=args.voice,
            custom_bgm=bgm_path,
        )
        print(f"\n[SUCCESS] Master Faceless Video: {result.video_path}")


if __name__ == "__main__":
    main()
