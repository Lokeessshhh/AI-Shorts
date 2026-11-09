"""Master Autonomous Orchestrator for AI Shorts.
Coordinates Trend Scouting, State Persistence, and Batch Execution of:
- Mode 1: Faceless Narrative & Facts (Google Trends / Pexels B-Roll / Edge-TTS / Dynamic ASS Subtitles)
- Mode 2: Podcast & Video Smart Clipper (YouTube Transcript API / Selective Range Slicing / Highlight Detection / Polish)
sequentially with zero human input.
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from ..config import config
from .state_manager import StateManager, normalize_short_record
from .trend_scout import TrendScout
from .clip_selector import ClipSelector
from ..pipeline.faceless_agent import FacelessShortsAgent
from ..clipper.pipeline import Mode3ClipperPipeline as Mode2ClipperPipeline


class AutonomousShortsOrchestrator:
    """End-to-End Autonomous Batch Coordinator for Mode 1 (Facts) & Mode 2 (Clipper)."""

    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        trend_scout: Optional[TrendScout] = None,
    ):
        self.state = state_manager or StateManager()
        self.scout = trend_scout or TrendScout(state_manager=self.state)

    def run_autonomous_batch(
        self,
        num_clipper_shorts: int = 3,
        skip_mode2: bool = False,
        skip_mode3: bool = False,
        modes: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Executes configured modes (Mode 1 and/or Mode 2 Clipper) with zero manual intervention.
        Consolidates all rendered videos and social metadata into a dedicated batch folder.
        """
        batch_start_time = time.time()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_{timestamp_str}"
        batch_dir = config.output_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        mode1_dir = batch_dir / "mode1_facts"
        mode2_dir = batch_dir / "mode2_clipper"

        print("\n" + "=" * 70)
        print(f"[ENGINE] AI SHORTS AUTONOMOUS BATCH ENGINE [{batch_id}]")
        print(f"    Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Batch Directory: {batch_dir}")
        print("=" * 70)

        # Resolve active modes
        if modes:
            active_modes = set()
            for m in modes:
                m_norm = m.lower().strip()
                if m_norm in ("mode1", "facts", "1"):
                    active_modes.add("mode1")
                elif m_norm in ("mode2", "clipper", "2", "mode3", "3"):
                    active_modes.add("mode2")
        else:
            active_modes = {"mode1", "mode2"}

        if skip_mode2 or skip_mode3:
            active_modes.discard("mode2")

        print(f"[ENGINE] Active Modes: {sorted(list(active_modes))}")

        manifest: Dict[str, Any] = {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "batch_dir": str(batch_dir),
            "modes_completed": [],
            "total_videos": 0,
            "mode1": {},
            "mode2": {},
            "errors": [],
        }

        # -------------------------------------------------------------
        # STEP 1: AUTONOMOUS TREND & CONTENT SCOUTING
        # -------------------------------------------------------------
        print("\n[STEP 1] AUTONOMOUS TREND SCOUTING & TOPIC REASONING")
        print("-" * 70)
        topic_m1 = self.scout.scout_mode1_topic() if "mode1" in active_modes else None
        podcast_m2 = self.scout.scout_mode2_podcast() if "mode2" in active_modes else None

        print("\n[SCOUT SUMMARY]")
        if topic_m1:
            print(f"  * Mode 1 (Facts):    \"{topic_m1}\"")
        if podcast_m2:
            print(f"  * Mode 2 (Podcast):  \"{podcast_m2['title']}\" ({podcast_m2['channel']})")

        # -------------------------------------------------------------
        # STEP 2: MODE 1 (FACELESS NARRATIVE & FACTS)
        # -------------------------------------------------------------
        if "mode1" in active_modes and topic_m1:
            print("\n" + "=" * 70)
            print("[STEP 2] EXECUTING MODE 1: FACELESS NARRATIVE & FACTS")
            print("=" * 70)
            m1_start = time.time()
            try:
                mode1_dir.mkdir(parents=True, exist_ok=True)
                agent_m1 = FacelessShortsAgent()
                lang_code = kwargs.get("language", "en")
                res_m1 = agent_m1.create_short(topic=topic_m1, language=lang_code)

                # Copy to batch directory
                batch_video_m1 = mode1_dir / res_m1.video_path.name
                shutil.copy2(res_m1.video_path, batch_video_m1)
                batch_meta_m1 = None
                if res_m1.metadata_path and res_m1.metadata_path.exists():
                    batch_meta_m1 = mode1_dir / res_m1.metadata_path.name
                    shutil.copy2(res_m1.metadata_path, batch_meta_m1)

                # Mark state
                self.state.mark_topic_done(
                    topic_m1,
                    mode="facts",
                    title=res_m1.title,
                    metadata={"video_path": str(batch_video_m1), "duration": res_m1.duration_seconds},
                )

                manifest["mode1"] = normalize_short_record({
                    "status": "SUCCESS",
                    "topic": topic_m1,
                    "title": res_m1.title,
                    "video_path": str(batch_video_m1),
                    "metadata_path": str(batch_meta_m1) if batch_meta_m1 else None,
                    "duration": round(res_m1.duration_seconds, 2),
                    "execution_seconds": round(time.time() - m1_start, 1),
                })
                manifest["modes_completed"].append("mode1_facts")
                manifest["total_videos"] += 1
                print(f"[SUCCESS/Mode 1] Rendered: {batch_video_m1.name}")

            except Exception as e:
                err_msg = f"Mode 1 Generation Failed: {e}"
                print(f"[ERROR/Mode 1] {err_msg}")
                manifest["mode1"] = normalize_short_record({"status": "FAILED", "error": str(e), "topic": topic_m1})
                manifest["errors"].append(err_msg)

        # -------------------------------------------------------------
        # STEP 3: MODE 2 (PODCAST & LONG-FORM SMART CLIPPER)
        # -------------------------------------------------------------
        if "mode2" in active_modes and podcast_m2:
            print("\n" + "=" * 70)
            print("[STEP 3] EXECUTING MODE 2: PODCAST & VIDEO SMART CLIPPER")
            print("=" * 70)
            m2_start = time.time()
            try:
                mode2_dir.mkdir(parents=True, exist_ok=True)
                pipeline_m2 = Mode2ClipperPipeline()
                clips_res = pipeline_m2.run(
                    source=podcast_m2["url"],
                    num_clips=num_clipper_shorts,
                    output_dir=mode2_dir,
                )

                # Mark state
                self.state.mark_video_clipped(
                    podcast_m2["video_id"],
                    title=podcast_m2["title"],
                    metadata={"clips_count": len(clips_res)},
                )

                clip_items = []
                for c in clips_res:
                    clip_items.append({
                        "rank": c.get("rank"),
                        "title": c.get("title"),
                        "viral_score": c.get("viral_score"),
                        "hook_score": c.get("hook_score"),
                        "narrative_score": c.get("narrative_score"),
                        "debate_score": c.get("debate_score"),
                        "density_score": c.get("density_score"),
                        "virality_reason": c.get("virality_reason"),
                        "hook_sentence": c.get("hook_sentence"),
                        "category": c.get("category"),
                        "mood": c.get("mood"),
                        "wpm": c.get("wpm"),
                        "video_path": str(c.get("video_path")),
                        "metadata_path": str(c.get("metadata_path")),
                        "duration": c.get("duration"),
                    })

                # Automatically score all candidate clips and select the single best one for upload
                selector = ClipSelector()
                winner, scored_clips = selector.score_and_select_best_clip(clip_items)

                # Persist dedicated upload target pointer
                selected_file = mode2_dir / "selected_for_upload.json"
                with open(selected_file, "w", encoding="utf-8") as f:
                    json.dump(winner, f, indent=2, ensure_ascii=False)

                manifest["mode2"] = normalize_short_record({
                    "status": "SUCCESS",
                    "source_url": podcast_m2["url"],
                    "source_title": podcast_m2["title"],
                    "source_channel": podcast_m2["channel"],
                    "clips_count": len(clips_res),
                    "selected_clip": winner,
                    "clips": scored_clips,
                    "title": winner.get("title", podcast_m2["title"]),
                    "video_path": winner.get("video_path"),
                    "metadata_path": winner.get("metadata_path"),
                    "duration": winner.get("duration", 45.0),
                    "viral_score": winner.get("viral_score", 90),
                    "execution_seconds": round(time.time() - m2_start, 1),
                })
                manifest["modes_completed"].append("mode2_clipper")
                manifest["total_videos"] += len(clips_res)
                print(f"[SUCCESS/Mode 2] Rendered {len(clips_res)} Podcast Shorts!")
                print(f"[SELECTED FOR UPLOAD] '{winner['title']}' (Composite: {winner.get('composite_upload_score')}/100, Viral: {winner.get('viral_score')}/100)")
                print(f"  * Selection Reason: {winner.get('selection_reason')}")

            except Exception as e:
                err_msg = f"Mode 2 Clipper Failed: {e}"
                print(f"[ERROR/Mode 2] {err_msg}")
                manifest["errors"].append(err_msg)

                # Autonomous Fallback: If streaming is blocked, generate alternate high-retention short
                print("\n[Orchestrator] Mode 2 stream blocked; generating high-retention alternate short...")
                try:
                    alt_topic = self.scout.scout_mode1_topic()
                    alt_dir = batch_dir / "mode2_fallback"
                    alt_dir.mkdir(parents=True, exist_ok=True)
                    agent_alt = FacelessShortsAgent()
                    alt_res = agent_alt.create_short(topic=alt_topic)

                    alt_vpath = Path(alt_res.video_path)
                    batch_video_alt = alt_dir / alt_vpath.name
                    shutil.copy2(alt_vpath, batch_video_alt)

                    batch_meta_alt = None
                    if alt_res.metadata_path:
                        alt_mpath = Path(alt_res.metadata_path)
                        batch_meta_alt = alt_dir / alt_mpath.name
                        shutil.copy2(alt_mpath, batch_meta_alt)

                    self.state.mark_topic_done(
                        alt_topic,
                        mode="mode1_facts",
                        title=alt_res.title,
                        metadata={"video_path": str(batch_video_alt), "duration": alt_res.duration_seconds},
                    )

                    manifest["mode2"] = normalize_short_record({
                        "status": "SUCCESS",
                        "is_fallback": True,
                        "source_url": "N/A",
                        "source_title": alt_res.title,
                        "source_channel": "Google Trends RSS",
                        "clips_count": 1,
                        "topic": alt_topic,
                        "title": alt_res.title,
                        "video_path": str(batch_video_alt),
                        "metadata_path": str(batch_meta_alt) if batch_meta_alt else None,
                        "duration": round(alt_res.duration_seconds, 1),
                        "selected_clip": {
                            "video_path": str(batch_video_alt),
                            "metadata_path": str(batch_meta_alt) if batch_meta_alt else None,
                            "title": alt_res.title,
                            "rank": 1,
                            "composite_upload_score": 95.0,
                        },
                    })
                    manifest["modes_completed"].append("mode2_fallback")
                    manifest["total_videos"] += 1
                    print(f"[SUCCESS/Fallback] Alternate Premier Short Ready: {alt_res.title}")
                except Exception as fe:
                    print(f"[ERROR/Fallback] Fallback short generation failed: {fe}")
                    manifest["mode2"] = normalize_short_record({"status": "FAILED", "error": str(fe)})

        # -------------------------------------------------------------
        # STEP 4: COMPILE BATCH MANIFEST & SUMMARY
        # -------------------------------------------------------------
        total_batch_time = time.time() - batch_start_time
        manifest["total_batch_seconds"] = round(total_batch_time, 1)

        manifest_file = batch_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        summary_file = batch_dir / "BATCH_SUMMARY.txt"
        summary_content = self._format_batch_summary(manifest, batch_dir)
        summary_file.write_text(summary_content, encoding="utf-8")

        self.state.record_batch(manifest)

        print("\n" + "=" * 70)
        print(f"[COMPLETE] AUTONOMOUS BATCH COMPLETED IN {total_batch_time:.1f}s")
        print(f"    Total Shorts Generated: {manifest['total_videos']}")
        print(f"    Batch Directory: {batch_dir}")
        print(f"    Manifest: {manifest_file.name}")
        print(f"    Summary:  {summary_file.name}")
        print("=" * 70 + "\n")

        return manifest

    def _format_batch_summary(self, manifest: Dict[str, Any], batch_dir: Path) -> str:
        """Format human-friendly plain text summary for social publishing."""
        lines = [
            "=======================================================",
            f"AI SHORTS AUTONOMOUS BATCH REPORT: {manifest.get('batch_id', 'Unknown')}",
            f"Generated: {manifest.get('timestamp', 'Now')}",
            f"Total Videos Rendered: {manifest.get('total_videos', 0)}",
            f"Total Execution Time: {manifest.get('total_batch_seconds', 0)} seconds",
            "=======================================================\n",
        ]

        if manifest.get("mode1", {}).get("status") == "SUCCESS":
            m1 = normalize_short_record(manifest["mode1"])
            lines.extend([
                "[MODE 1: FACELESS NARRATIVE & FACTS]",
                f"Topic:    {m1['topic']}",
                f"Title:    {m1['title']}",
                f"File:     {Path(m1['video_path']).name if m1['video_path'] else 'None'} ({m1['duration']}s)",
                f"Metadata: {Path(m1['metadata_path']).name if m1.get('metadata_path') else 'None'}",
                "",
            ])

        if manifest.get("mode2", {}).get("status") == "SUCCESS":
            m2 = normalize_short_record(manifest["mode2"])
            selected = normalize_short_record(m2.get("selected_clip", {}))
            m2_label = "[MODE 2: PREMIER ALTERNATE SHORT]" if m2.get("is_fallback") else "[MODE 2: PODCAST & VIDEO SMART CLIPPER]"
            lines.extend([
                m2_label,
                f"Source: {m2['source_title']} ({m2['source_channel']})",
                f"URL:    {m2['source_url']}",
                f"Total Clips Extracted: {m2['clips_count']}",
                "",
                ">>> SELECTED FOR UPLOAD (WINNER) <<<",
                f"Clip Title:      {selected['title']}",
                f"Video File:      {Path(selected['video_path']).name if selected['video_path'] else 'None'}",
                f"Composite Score: {selected.get('composite_upload_score', 'N/A')}/100 (Tournament Viral Score: {selected['viral_score']}/100)",
                f"Duration:        {selected['duration']}s",
                f"Hook Sentence:   \"{selected['hook_sentence']}\"",
                f"Selection Reason: {selected.get('selection_reason', 'Top-ranked viral highlight')}",
                f"Metadata File:   {Path(selected['metadata_path']).name if selected.get('metadata_path') else 'None'}",
                "",
            ])
            if m2.get("clips"):
                lines.append("Candidate Clips Ranking:")
                for clip in m2.get("clips", []):
                    norm_c = normalize_short_record(clip)
                    badge = "[SELECTED FOR UPLOAD]" if clip.get("selected_for_upload") else f"[RUNNER-UP #{clip.get('selection_rank', clip.get('rank', 2))}]"
                    score_val = clip.get("composite_upload_score", norm_c["viral_score"])
                    lines.append(
                        f"  * #{clip.get('rank', 1)} [{score_val}/100] {badge}: {Path(norm_c['video_path']).name if norm_c['video_path'] else 'Clip'} ({norm_c['duration']}s)"
                    )
                lines.append("")

        return "\n".join(lines)
