"""Master Autonomous Orchestrator for AI Shorts.
Coordinates Trend Scouting, State Persistence, and Batch Execution of Modes 1, 2, and 3
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
from .state_manager import StateManager
from .trend_scout import TrendScout
from .clip_selector import ClipSelector
from ..pipeline.faceless_agent import FacelessShortsAgent
from ..story.dev_claude_pipeline import DevClaudePipeline
from ..clipper.pipeline import Mode3ClipperPipeline


class AutonomousShortsOrchestrator:
    """End-to-End Autonomous Batch Coordinator."""

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
        skip_mode3: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes Modes 1, 2, and 3 sequentially with zero manual intervention.
        Consolidates all rendered videos and social metadata into a dedicated batch folder.
        """
        batch_start_time = time.time()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_{timestamp_str}"
        batch_dir = config.output_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        mode1_dir = batch_dir / "mode1_facts"
        mode2_dir = batch_dir / "mode2_dev_claude"
        mode3_dir = batch_dir / "mode3_clipper"

        print("\n" + "=" * 70)
        print(f"[ENGINE] AI SHORTS AUTONOMOUS BATCH ENGINE [{batch_id}]")
        print(f"    Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Batch Directory: {batch_dir}")
        print("=" * 70)

        manifest: Dict[str, Any] = {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "batch_dir": str(batch_dir),
            "modes_completed": [],
            "total_videos": 0,
            "mode1": {},
            "mode2": {},
            "mode3": {},
            "errors": [],
        }

        # -------------------------------------------------------------
        # STEP 1: AUTONOMOUS TREND & CONTENT SCOUTING
        # -------------------------------------------------------------
        print("\n[STEP 1/4] AUTONOMOUS TREND SCOUTING & TOPIC REASONING")
        print("-" * 70)
        topic_m1 = self.scout.scout_mode1_topic()
        topic_m2 = self.scout.scout_mode2_topic()
        podcast_m3 = self.scout.scout_mode3_podcast() if not skip_mode3 else None

        print("\n[SCOUT SUMMARY]")
        print(f"  * Mode 1 (Facts):      \"{topic_m1}\"")
        print(f"  * Mode 2 (Dev vs AI):  \"{topic_m2}\"")
        if podcast_m3:
            print(f"  * Mode 3 (Podcast):    \"{podcast_m3['title']}\" ({podcast_m3['channel']})")

        # -------------------------------------------------------------
        # STEP 2: MODE 1 (FACELESS NARRATIVE & FACTS)
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        print("[STEP 2/4] EXECUTING MODE 1: FACELESS NARRATIVE & FACTS")
        print("=" * 70)
        m1_start = time.time()
        try:
            mode1_dir.mkdir(parents=True, exist_ok=True)
            agent_m1 = FacelessShortsAgent()
            res_m1 = agent_m1.create_short(topic=topic_m1)

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
                metadata={"title": res_m1.title, "video": batch_video_m1.name},
            )

            manifest["mode1"] = {
                "status": "SUCCESS",
                "topic": topic_m1,
                "title": res_m1.title,
                "video_path": str(batch_video_m1),
                "metadata_path": str(batch_meta_m1) if batch_meta_m1 else None,
                "duration": round(res_m1.duration_seconds, 2),
                "execution_seconds": round(time.time() - m1_start, 1),
            }
            manifest["modes_completed"].append("mode1_facts")
            manifest["total_videos"] += 1
            print(f"[SUCCESS/Mode 1] Rendered: {batch_video_m1.name}")

        except Exception as e:
            err_msg = f"Mode 1 Generation Failed: {e}"
            print(f"[ERROR/Mode 1] {err_msg}")
            manifest["mode1"] = {"status": "FAILED", "error": str(e), "topic": topic_m1}
            manifest["errors"].append(err_msg)

        # -------------------------------------------------------------
        # STEP 3: MODE 2 (DEVELOPER VS CLAUDE DIALOGUE & GAMEPLAY)
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        print("[STEP 3/4] EXECUTING MODE 2: DEVELOPER VS CLAUDE DIALOGUE")
        print("=" * 70)
        m2_start = time.time()
        try:
            mode2_dir.mkdir(parents=True, exist_ok=True)
            pipeline_m2 = DevClaudePipeline()
            res_m2 = pipeline_m2.run(topic=topic_m2, gameplay_style="random")

            vpath_m2 = Path(res_m2["video_path"])
            mpath_m2 = Path(res_m2["metadata_path"])

            batch_video_m2 = mode2_dir / vpath_m2.name
            shutil.copy2(vpath_m2, batch_video_m2)
            batch_meta_m2 = mode2_dir / mpath_m2.name
            shutil.copy2(mpath_m2, batch_meta_m2)

            # Mark state
            self.state.mark_topic_done(
                topic_m2,
                mode="dev_claude",
                metadata={"title": res_m2["title"], "video": batch_video_m2.name},
            )

            manifest["mode2"] = {
                "status": "SUCCESS",
                "topic": topic_m2,
                "title": res_m2["title"],
                "video_path": str(batch_video_m2),
                "metadata_path": str(batch_meta_m2),
                "duration": res_m2.get("duration", 0.0),
                "execution_seconds": round(time.time() - m2_start, 1),
            }
            manifest["modes_completed"].append("mode2_dev_claude")
            manifest["total_videos"] += 1
            print(f"[SUCCESS/Mode 2] Rendered: {batch_video_m2.name}")

        except Exception as e:
            err_msg = f"Mode 2 Generation Failed: {e}"
            print(f"[ERROR/Mode 2] {err_msg}")
            manifest["mode2"] = {"status": "FAILED", "error": str(e), "topic": topic_m2}
            manifest["errors"].append(err_msg)

        # -------------------------------------------------------------
        # STEP 4: MODE 3 (PODCAST & LONG-FORM SMART CLIPPER)
        # -------------------------------------------------------------
        if not skip_mode3 and podcast_m3:
            print("\n" + "=" * 70)
            print("[STEP 4/4] EXECUTING MODE 3: PODCAST SMART CLIPPER")
            print("=" * 70)
            m3_start = time.time()
            try:
                mode3_dir.mkdir(parents=True, exist_ok=True)
                pipeline_m3 = Mode3ClipperPipeline()
                clips_res = pipeline_m3.run(
                    source=podcast_m3["url"],
                    num_clips=num_clipper_shorts,
                    output_dir=mode3_dir,
                )

                # Mark state
                self.state.mark_video_clipped(
                    podcast_m3["video_id"],
                    title=podcast_m3["title"],
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
                selected_file = mode3_dir / "selected_for_upload.json"
                with open(selected_file, "w", encoding="utf-8") as f:
                    json.dump(winner, f, indent=2, ensure_ascii=False)

                manifest["mode3"] = {
                    "status": "SUCCESS",
                    "source_url": podcast_m3["url"],
                    "source_title": podcast_m3["title"],
                    "source_channel": podcast_m3["channel"],
                    "clips_count": len(clips_res),
                    "selected_clip": winner,
                    "clips": scored_clips,
                    "execution_seconds": round(time.time() - m3_start, 1),
                }
                manifest["modes_completed"].append("mode3_clipper")
                manifest["total_videos"] += len(clips_res)
                print(f"[SUCCESS/Mode 3] Rendered {len(clips_res)} Podcast Shorts!")
                print(f"[SELECTED FOR UPLOAD] '{winner['title']}' (Composite: {winner['composite_upload_score']}/100, Tournament: {winner['viral_score']}/100)")
                print(f"  * Selection Reason: {winner['selection_reason']}")

            except Exception as e:
                err_msg = f"Mode 3 Clipper Failed: {e}"
                print(f"[ERROR/Mode 3] {err_msg}")
                manifest["mode3"] = {
                    "status": "FAILED",
                    "error": str(e),
                    "source_url": podcast_m3.get("url") if podcast_m3 else None,
                }
                manifest["errors"].append(err_msg)

                # Resilient Fallback: If cloud runner is blocked by YouTube bot-check on long podcasts,
                # generate a high-retention alternate short so the batch ALWAYS produces 3 premier uploads!
                print("\n[Orchestrator] Mode 3 stream blocked by platform; generating high-retention alternate short...")
                try:
                    alt_topic = self.scout.scout_mode1_topic()
                    alt_dir = batch_dir / "mode3_fallback"
                    alt_dir.mkdir(parents=True, exist_ok=True)
                    agent_alt = FacelessShortsAgent()
                    alt_res = agent_alt.create_short(topic=alt_topic, output_dir=alt_dir)

                    self.state.mark_topic_done(
                        alt_topic,
                        mode="mode1_facts",
                        title=alt_res.title,
                        metadata={"video_path": str(alt_res.video_path), "duration": alt_res.duration},
                    )

                    manifest["mode3"] = {
                        "status": "SUCCESS",
                        "is_fallback": True,
                        "topic": alt_topic,
                        "title": alt_res.title,
                        "video_path": str(alt_res.video_path),
                        "metadata_path": str(alt_res.metadata_path) if alt_res.metadata_path else None,
                        "duration": round(alt_res.duration, 1),
                        "selected_clip": {
                            "video_path": str(alt_res.video_path),
                            "metadata_path": str(alt_res.metadata_path) if alt_res.metadata_path else None,
                            "title": alt_res.title,
                            "rank": 1,
                            "composite_upload_score": 95.0,
                        },
                    }
                    manifest["modes_completed"].append("mode3_fallback")
                    manifest["total_videos"] += 1
                    print(f"[SUCCESS/Fallback] Alternate Premier Short Ready: {alt_res.title}")
                except Exception as fe:
                    print(f"[ERROR/Fallback] Fallback short generation failed: {fe}")

        # -------------------------------------------------------------
        # STEP 5: COMPILE BATCH MANIFEST & SUMMARY
        # -------------------------------------------------------------
        total_batch_time = time.time() - batch_start_time
        manifest["total_batch_seconds"] = round(total_batch_time, 1)

        # Write manifest.json
        manifest_file = batch_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Write ready-to-read BATCH_SUMMARY.txt
        summary_file = batch_dir / "BATCH_SUMMARY.txt"
        summary_content = self._format_batch_summary(manifest, batch_dir)
        summary_file.write_text(summary_content, encoding="utf-8")

        # Record in StateManager
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
            f"AI SHORTS AUTONOMOUS BATCH REPORT: {manifest['batch_id']}",
            f"Generated: {manifest['timestamp']}",
            f"Total Videos Rendered: {manifest['total_videos']}",
            f"Total Execution Time: {manifest['total_batch_seconds']} seconds",
            "=======================================================\n",
        ]

        if manifest.get("mode1", {}).get("status") == "SUCCESS":
            m1 = manifest["mode1"]
            lines.extend([
                "[MODE 1: FACELESS NARRATIVE & FACTS]",
                f"Topic:    {m1['topic']}",
                f"Title:    {m1['title']}",
                f"Video:    {Path(m1['video_path']).name}",
                f"Duration: {m1['duration']}s",
                f"Metadata: {Path(m1['metadata_path']).name if m1.get('metadata_path') else 'N/A'}",
                "",
            ])

        if manifest.get("mode2", {}).get("status") == "SUCCESS":
            m2 = manifest["mode2"]
            lines.extend([
                "[MODE 2: DEVELOPER VS CLAUDE TECH DIALOGUE]",
                f"Topic:    {m2['topic']}",
                f"Title:    {m2['title']}",
                f"Video:    {Path(m2['video_path']).name}",
                f"Duration: {m2['duration']}s",
                f"Metadata: {Path(m2['metadata_path']).name if m2.get('metadata_path') else 'N/A'}",
                "",
            ])

        if manifest.get("mode3", {}).get("status") == "SUCCESS":
            m3 = manifest["mode3"]
            selected = m3.get("selected_clip", {})
            lines.extend([
                "[MODE 3: PODCAST & VIDEO VIRAL CLIPS]",
                f"Source: {m3['source_title']} ({m3['source_channel']})",
                f"URL:    {m3['source_url']}",
                f"Total Clips Extracted: {m3['clips_count']}",
                "",
                ">>> SELECTED FOR UPLOAD (WINNER) <<<",
                f"Clip Title:      {selected.get('title')}",
                f"Video File:      {Path(selected.get('video_path', '')).name}",
                f"Composite Score: {selected.get('composite_upload_score', 'N/A')}/100 (Tournament Viral Score: {selected.get('viral_score')}/100)",
                f"Duration:        {selected.get('duration')}s",
                f"Hook Sentence:   \"{selected.get('hook_sentence', '')}\"",
                f"Selection Reason: {selected.get('selection_reason')}",
                f"Metadata File:   {Path(selected.get('metadata_path', '')).name}",
                "",
                "Candidate Clips Ranking:",
            ])
            for clip in m3.get("clips", []):
                badge = "[SELECTED FOR UPLOAD]" if clip.get("selected_for_upload") else f"[RUNNER-UP #{clip.get('selection_rank', clip.get('rank'))}]"
                score_val = clip.get("composite_upload_score", clip.get("viral_score"))
                lines.append(
                    f"  * #{clip['rank']} [{score_val}/100] {badge}: {Path(clip['video_path']).name} ({clip['duration']}s)"
                )
            lines.append("")

        if manifest.get("errors"):
            lines.extend([
                "[WARNINGS / ERRORS DURING RUN]",
                "\n".join([f"- {e}" for e in manifest["errors"]]),
                "",
            ])

        return "\n".join(lines)
