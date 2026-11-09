"""AI Shorts Production CLI Engine
Supported Modes:
  - Mode 1: Faceless Narrative & Facts (LLM Script + Bilingual Edge-TTS + Kinetic ASS Subtitles + Pexels B-Roll + FFmpeg)
  - Mode 2: Video & Podcast Smart Clipper (yt-dlp + youtube-transcript-api + OpenRouter Highlights + OpenCV Reframe + Polish)
  - Mode auto: Autonomous Trend Scout & 2-Mode Batch Orchestrator (Google Trends & Podcast Watchlist)
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
        description="AI Shorts Engine: Automated Short-Form Content Generator (Mode 1: Facts, Mode 2: Clipper & Auto)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["facts", "clipper", "chatgpt", "mode3", "auto"],
        default="facts",
        help="Content mode: 'facts' (Mode 1), 'clipper' (Mode 2), 'mode3'/'chatgpt' (Mode 3: ChatGPT Conversation Shorts), or 'auto' (Autonomous Batch)",
    )

    # Language Mode Argument
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="en",
        choices=["en", "hi", "english", "hindi"],
        help="Language mode: 'en' / 'english' (Default) or 'hi' / 'hindi' (Natural Indian Voice + Hinglish Captions)",
    )

    # Mode 1 Arguments
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="[Mode 1] Premise, topic, or concept to generate",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="[Mode 1] edge-tts voice name (e.g. en-US-ChristopherNeural for EN, hi-IN-MadhurNeural for HI)",
    )
    parser.add_argument(
        "--bgm",
        type=str,
        default=None,
        help="[Mode 1] Path to custom background music audio file",
    )

    # Mode 2 Clipper Arguments
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="[Mode 2] YouTube video URL to download and clip",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="[Mode 2] Path to local video file to clip",
    )
    parser.add_argument(
        "--clips",
        type=int,
        default=3,
        help="[Mode 2 & Auto] Number of viral shorts to extract (default: 3)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=30.0,
        help="[Mode 2] Minimum duration in seconds per clip (default: 30.0)",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=60.0,
        help="[Mode 2] Maximum duration in seconds per clip (default: 60.0)",
    )
    parser.add_argument(
        "--layout",
        type=str,
        default=None,
        help="[Mode 2] Visual layout: 'auto', 'solo', or 'split_screen'",
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
        "--modes",
        nargs="+",
        default=None,
        help="[Mode auto] Specific modes to run in batch, e.g. '--modes mode1' or '--modes mode1 mode2' (default: all modes)",
    )
    parser.add_argument(
        "--skip-mode2",
        action="store_true",
        help="[Mode auto] Skip Mode 2 podcast clipper in the batch run",
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
    lang = "hi" if args.language in ("hi", "hindi") else "en"

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
                skip_mode2=args.skip_mode2,
                modes=args.modes,
                language=lang,
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
    # ROUTE: Mode 2 (Podcast & Video Smart Clipper)
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
        print(f"\n[SUCCESS] Mode 2 Clipper Generated {len(results)} Shorts!")
        for r in results:
            print(f"  * #{r['rank']} ({r['viral_score']}/100): {r['video_path']}")

    # -------------------------------------------------------------
    # ROUTE: Mode 3 (ChatGPT Conversation Shorts)
    # -------------------------------------------------------------
    elif args.mode in ("chatgpt", "mode3"):
        from src.mode3.pipeline import Mode3Pipeline

        pipeline = Mode3Pipeline()
        bgm_path = Path(args.bgm) if args.bgm else None
        res = pipeline.run(
            topic=args.topic,
            bgm_path=bgm_path,
        )
        print(f"\n[SUCCESS] Mode 3 Short Created: {res['video_path']}")
        if res.get("metadata_path"):
            print(f"  * Metadata: {res['metadata_path']}")

    # -------------------------------------------------------------
    # ROUTE: Mode 1 (Faceless Narrative & Facts)
    # -------------------------------------------------------------
    else:
        from src.pipeline.faceless_agent import FacelessShortsAgent

        bgm_path = Path(args.bgm) if args.bgm else None
        agent = FacelessShortsAgent()
        result = agent.create_short(
            topic=args.topic,
            language=lang,
            custom_voice=args.voice,
            custom_bgm=bgm_path,
        )
        print(f"\n[SUCCESS] Mode 1 Short Created ({lang.upper()}): {result.video_path}")
        if result.metadata_path:
            print(f"  * Metadata: {result.metadata_path}")


if __name__ == "__main__":
    main()
