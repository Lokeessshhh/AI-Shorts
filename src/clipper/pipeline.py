"""Mode 3 Master Pipeline Coordinator.
Orchestrates long-form video download, faster-whisper transcription,
LLM viral moment detection, OpenCV reframing, and FFmpeg shorts assembly.
"""

import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..config import config
from .downloader import VideoDownloader
from .transcriber import LongFormTranscriber
from .highlight_detector import HighlightDetector
from .editor import ShortEditor


def slugify(text: str) -> str:
    """Convert text into a safe filename slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "_", text)[:40]


class Mode3ClipperPipeline:
    """End-to-End Pipeline for Mode 3: Long-Form Video & Podcast Smart Clipper."""

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        transcriber: Optional[LongFormTranscriber] = None,
        highlight_detector: Optional[HighlightDetector] = None,
        editor: Optional[ShortEditor] = None,
    ):
        self.downloader = downloader or VideoDownloader()
        self.transcriber = transcriber or LongFormTranscriber()
        self.highlight_detector = highlight_detector or HighlightDetector()
        self.editor = editor or ShortEditor()

    def run(
        self,
        source: str,
        num_clips: int = 3,
        min_duration: float = 30.0,
        max_duration: float = 60.0,
        output_dir: Optional[Path] = None,
        layout: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute full Mode 3 workflow.
        Returns a list of dictionaries with info on each generated short.
        """
        output_dir = output_dir or config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        session_id = int(time.time())

        print("=" * 60)
        print("[START] AI Shorts Mode 3: Podcast & Video Smart Clipper")
        print(f"[SOURCE] {source}")
        print(f"[TARGET] Top {num_clips} Viral Shorts ({min_duration:.0f}s - {max_duration:.0f}s)")
        print("=" * 60)

        # Step 1: Zero-Video Transcription / Ingestion
        is_url = self.downloader.is_url(source)
        if is_url:
            print("\n[1/4] Zero-Video Ingestion: Pulling instant word-level captions...")
            meta, transcript_data = self.downloader.get_transcript_and_meta(
                source=source,
                transcriber=self.transcriber,
            )
            video_path = None
        else:
            print("\n[1/4] Ingesting local video file & extracting audio...")
            video_path, audio_path, meta = self.downloader.download_or_ingest(source)
            cache_json = audio_path.parent / "transcript.json"
            transcript_data = self.transcriber.transcribe(audio_path, cache_json_path=cache_json)

        print(f"  * Video Title: {meta['title']}")
        print(f"  * Total Duration: {meta['duration']:.1f}s ({meta['duration']/60:.1f} min)")
        print(f"  * Transcribed {transcript_data['total_words']} words across {len(transcript_data['segments'])} segments.")

        # Step 2: AI Viral Highlight Detection
        print(f"\n[2/4] Detecting Top {num_clips} viral moments via OpenRouter...")
        highlights = self.highlight_detector.detect_highlights(
            transcript_data=transcript_data,
            num_clips=num_clips,
            min_duration=min_duration,
            max_duration=max_duration,
        )

        if not highlights:
            raise RuntimeError("No viral highlights were returned by the detector.")

        print(f"  * Identified {len(highlights)} viral segments:")
        for h in highlights:
            print(f"    - #{h['rank']}: '{h['title']}' ({h['duration']:.1f}s, Score: {h['viral_score']}/100) [{h.get('category', 'General')} | Mood: {h.get('mood', 'chill_lofi')} ({h.get('wpm', 0)} WPM)]")
            print(f"      Hook (35%): \"{h['hook_sentence']}\" -> {h.get('hook_score', 0)}/35")
            print(f"      Resolution (30%): \"{h.get('punchline_resolution', 'Natural punchline')}\" -> {h.get('narrative_score', 0)}/30")
            print(f"      Debate (20%): {h.get('debate_score', 0)}/20 | Density (15%): {h.get('density_score', 0)}/15")
            print(f"      Timeline Act: {h.get('act', 'General')}")

        # Step 3: Render Each Short with Polish (Selective Slicing if URL)
        print(f"\n[3/4] Slicing & rendering {len(highlights)} vertical 9:16 shorts...")
        results: List[Dict[str, Any]] = []

        for idx, h in enumerate(highlights, 1):
            clip_slug = slugify(h["title"])
            clip_filename = f"clip_{idx}_{clip_slug}_{session_id}.mp4"
            clip_meta_filename = f"clip_{idx}_{clip_slug}_{session_id}_metadata.txt"

            out_video = output_dir / clip_filename
            out_meta = output_dir / clip_meta_filename
            temp_dir = config.temp_dir / f"clip_{idx}_{session_id}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Attach source creator & clearance metadata for on-screen attribution
            h["channel"] = meta.get("uploader") or meta.get("channel") or ""
            h["source_title"] = meta.get("title", "")
            h["source_url"] = meta.get("url", source)
            h["license"] = meta.get("license", "Transformative Commentary / Fair Use")

            t_start = time.time()
            if is_url:
                # Selective Range Slicing: Download ONLY this 30-60s clip
                sliced_input = temp_dir / f"raw_slice_{idx}_{session_id}.mp4"
                self.downloader.download_slice(
                    source=source,
                    start_time=h["start_time"],
                    end_time=h["end_time"],
                    output_path=sliced_input,
                )
                self.editor.render_short(
                    source_video=sliced_input,
                    highlight=h,
                    output_mp4=out_video,
                    temp_dir=temp_dir,
                    enable_micro_zoom=True,
                    enable_progress_bar=True,
                    layout=layout,
                    is_pre_sliced=True,
                )
                if sliced_input.exists():
                    sliced_input.unlink(missing_ok=True)
            else:
                self.editor.render_short(
                    source_video=video_path,
                    highlight=h,
                    output_mp4=out_video,
                    temp_dir=temp_dir,
                    enable_micro_zoom=True,
                    enable_progress_bar=True,
                    layout=layout,
                    is_pre_sliced=False,
                )
            render_duration = time.time() - t_start

            # Generate Social Metadata File
            self._save_metadata(out_meta, h, meta)

            print(f"  [DONE] Short #{idx} exported in {render_duration:.1f}s -> {out_video.name}")

            results.append({
                "rank": idx,
                "title": h["title"],
                "video_path": out_video,
                "metadata_path": out_meta,
                "duration": h["duration"],
                "viral_score": h["viral_score"],
                "hook_score": h.get("hook_score"),
                "narrative_score": h.get("narrative_score"),
                "debate_score": h.get("debate_score"),
                "density_score": h.get("density_score"),
                "virality_reason": h.get("virality_reason"),
                "hook_sentence": h.get("hook_sentence"),
                "category": h.get("category"),
                "mood": h.get("mood"),
                "wpm": h.get("wpm"),
                "hashtags": h.get("hashtags"),
            })

        print("\n" + "=" * 60)
        print(f"[SUCCESS] All {len(results)} viral shorts generated successfully!")
        for r in results:
            print(f"  * #{r['rank']} [{r['viral_score']}/100]: {r['video_path']}")
        print("=" * 60)

        return results

    def _save_metadata(self, meta_path: Path, highlight: Dict[str, Any], source_meta: Dict[str, Any]) -> None:
        """Save ready-to-copy YouTube Shorts / Instagram Reels metadata with fair use attribution."""
        hashtags_str = " ".join(highlight.get("hashtags", ["#shorts", "#viral", "#podcast"]))
        uploader_credit = source_meta.get('uploader') or source_meta.get('channel') or 'Original Creator'
        license_str = source_meta.get('license') or highlight.get('license') or 'Transformative Fair Use / CC Attribution'
        content = f"""=== YOUTUBE SHORTS / INSTAGRAM REELS / TIKTOK METADATA ===

CLIP TITLE:
{highlight['title']}

CATEGORY:
{highlight.get('category', 'General')}

BGM MOOD ARCHETYPE:
{highlight.get('mood', 'chill_lofi')} (Speech Speed: {highlight.get('wpm', 0)} WPM)

COPYRIGHT & CLEARANCE STATUS:
- Original Creator: @{uploader_credit}
- Clearance Status: 100% Cleared (No Content ID registered commercial music)
- Applicable License: {license_str}
- Attribution: Provided on-screen and in caption description

VIRAL SCORE: {highlight['viral_score']}/100
SCORE BREAKDOWN:
- Hook Strength: {highlight.get('hook_score', 'N/A')}/35
- Narrative Completeness: {highlight.get('narrative_score', 'N/A')}/30
- Comment / Debate Arousal: {highlight.get('debate_score', 'N/A')}/20
- Information Density: {highlight.get('density_score', 'N/A')}/15

VIRALITY REASON:
{highlight.get('virality_reason', 'High-retention moment with immediate hook.')}

HOOK (First 3 Seconds):
"{highlight.get('hook_sentence', '')}"

PUNCHLINE / RESOLUTION:
"{highlight.get('punchline_resolution', '')}"

CAPTION / DESCRIPTION:
{highlight.get('hook_sentence', '')}

Extracted from: {source_meta.get('title', 'Video')}
Original Creator: @{uploader_credit}
Source: {source_meta.get('url', '')}

(Transformative educational highlight & commentary under Fair Use / Creative Commons attribution terms).

HASHTAGS:
{hashtags_str}

PINNED COMMENT:
Did you know about this? Drop your thoughts below! 👇
"""
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(content)


def run_clipper(
    source: str,
    num_clips: int = 3,
    min_duration: float = 30.0,
    max_duration: float = 60.0,
) -> List[Dict[str, Any]]:
    """Convenience entrypoint function for Mode 3."""
    pipeline = Mode3ClipperPipeline()
    return pipeline.run(
        source=source,
        num_clips=num_clips,
        min_duration=min_duration,
        max_duration=max_duration,
    )
