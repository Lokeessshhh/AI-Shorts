"""Mode 3 Clip Scoring & Upload Selection Engine.
Evaluates all generated candidate clips across multi-dimensional retention metrics
(Viral Score, Hook Strength, Comment/Debate Arousal, Information Density, Pacing)
and autonomously selects the single best clip for upload to YouTube Shorts and Instagram Reels.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class ClipSelector:
    """Evaluates, scores, and selects the single highest-virality clip for social publishing."""

    @staticmethod
    def parse_metadata_file(meta_path: Path) -> Dict[str, Any]:
        """Extract scoring metrics and copy from a clip metadata .txt file."""
        if not meta_path.exists():
            return {}

        text = meta_path.read_text(encoding="utf-8")
        data: Dict[str, Any] = {}

        # Title
        m_title = re.search(r"CLIP TITLE:\s*\n([^\n]+)", text)
        if m_title:
            data["title"] = m_title.group(1).strip()

        # Viral Score
        m_score = re.search(r"VIRAL SCORE:\s*(\d+)/100", text)
        if m_score:
            data["viral_score"] = int(m_score.group(1))

        # Score Breakdown
        m_hook = re.search(r"Hook Strength:\s*([\d.]+)/35", text)
        if m_hook:
            data["hook_score"] = float(m_hook.group(1))

        m_narrative = re.search(r"Narrative Completeness:\s*([\d.]+)/30", text)
        if m_narrative:
            data["narrative_score"] = float(m_narrative.group(1))

        m_debate = re.search(r"Comment / Debate Arousal:\s*([\d.]+)/20", text)
        if m_debate:
            data["debate_score"] = float(m_debate.group(1))

        m_density = re.search(r"Information Density:\s*([\d.]+)/15", text)
        if m_density:
            data["density_score"] = float(m_density.group(1))

        # Hook sentence
        m_hook_sent = re.search(r'HOOK \(First 3 Seconds\):\s*\n"([^"]+)"', text)
        if m_hook_sent:
            data["hook_sentence"] = m_hook_sent.group(1).strip()

        # Virality Reason
        m_reason = re.search(r"VIRALITY REASON:\s*\n([^\n]+)", text)
        if m_reason:
            data["virality_reason"] = m_reason.group(1).strip()

        # Mood & WPM
        m_mood = re.search(r"BGM MOOD ARCHETYPE:\s*\n([^\n(]+)(?:\(Speech Speed:\s*([\d.]+)\s*WPM\))?", text)
        if m_mood:
            data["mood"] = m_mood.group(1).strip()
            if m_mood.group(2):
                data["wpm"] = float(m_mood.group(2))

        # Category
        m_cat = re.search(r"CATEGORY:\s*\n([^\n]+)", text)
        if m_cat:
            data["category"] = m_cat.group(1).strip()

        return data

    def compute_composite_upload_score(self, clip: Dict[str, Any]) -> float:
        """
        Calculate algorithmic Upload Priority Score (0-100+).
        Factors:
        - Base Viral Score: 50%
        - Hook Strength (out of 35 normalized to 100): 30%
        - Debate / Comment Arousal (out of 20 normalized to 100): 20%
        - Duration Sweet Spot Bonus (30s - 45s): +2.0 pts
        """
        base_viral = float(clip.get("viral_score", 70))
        hook_raw = float(clip.get("hook_score", (base_viral / 100.0) * 35.0))
        debate_raw = float(clip.get("debate_score", (base_viral / 100.0) * 20.0))

        hook_norm = (hook_raw / 35.0) * 100.0
        debate_norm = (debate_raw / 20.0) * 100.0

        composite = (base_viral * 0.50) + (hook_norm * 0.30) + (debate_norm * 0.20)

        # Duration bonus: 30s to 45s is the highest completion retention window for vertical platforms
        duration = float(clip.get("duration", 0.0))
        if 30.0 <= duration <= 45.0:
            composite += 2.0
        elif duration < 25.0 or duration > 58.0:
            composite -= 3.0

        return round(composite, 2)

    def score_and_select_best_clip(
        self, clips: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Rank all clips, compute composite scores, and select the #1 winner for publishing.
        """
        if not clips:
            raise ValueError("No clips provided for scoring and selection.")

        scored_clips = []
        for c in clips:
            clip_dict = dict(c)

            # If metadata path exists, supplement with parsed breakdown if missing
            meta_path_str = clip_dict.get("metadata_path")
            if meta_path_str:
                meta_p = Path(meta_path_str)
                if meta_p.exists():
                    parsed = self.parse_metadata_file(meta_p)
                    for k, v in parsed.items():
                        if k not in clip_dict or clip_dict[k] is None:
                            clip_dict[k] = v

            comp_score = self.compute_composite_upload_score(clip_dict)
            clip_dict["composite_upload_score"] = comp_score
            scored_clips.append(clip_dict)

        # Sort descending by composite upload score (primary), then viral_score (secondary)
        scored_clips.sort(
            key=lambda x: (x.get("composite_upload_score", 0), x.get("viral_score", 0)),
            reverse=True,
        )

        # Mark winner vs runner-ups
        for rank_idx, c in enumerate(scored_clips, start=1):
            c["selection_rank"] = rank_idx
            if rank_idx == 1:
                c["selected_for_upload"] = True
                c["selection_verdict"] = "WINNER / SELECTED FOR UPLOAD"
                hook_txt = c.get("hook_sentence", "")
                hook_disp = f"'{hook_txt}'" if hook_txt else "High hook retention"
                c["selection_reason"] = (
                    f"Top Composite Score ({c['composite_upload_score']}/100) with "
                    f"{c.get('hook_score', 'N/A')}/35 hook strength ({hook_disp}) "
                    f"and {c.get('debate_score', 'N/A')}/20 comment arousal."
                )
            else:
                c["selected_for_upload"] = False
                c["selection_verdict"] = f"RUNNER-UP #{rank_idx}"
                c["selection_reason"] = (
                    f"Composite score ({c['composite_upload_score']}/100) behind winning clip."
                )

        winner = scored_clips[0]
        return winner, scored_clips

    def process_batch_folder(self, batch_dir: Path) -> Dict[str, Any]:
        """
        Process an existing batch folder: score its Mode 3 clips, select the winner,
        and update manifest.json and BATCH_SUMMARY.txt without re-rendering anything.
        """
        manifest_file = batch_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found in {batch_dir}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        m3 = manifest.get("mode3", {})
        clips = m3.get("clips", [])
        if not clips:
            raise ValueError(f"No Mode 3 clips recorded in {manifest_file}")

        # Score and select winner
        winner, scored_clips = self.score_and_select_best_clip(clips)

        # Update manifest
        manifest["mode3"]["clips"] = scored_clips
        manifest["mode3"]["selected_clip"] = winner

        # Write mode3_clipper/selected_for_upload.json
        mode3_dir = batch_dir / "mode3_clipper"
        if mode3_dir.exists():
            selected_file = mode3_dir / "selected_for_upload.json"
            with open(selected_file, "w", encoding="utf-8") as f:
                json.dump(winner, f, indent=2, ensure_ascii=False)

        # Update manifest.json
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Re-generate BATCH_SUMMARY.txt with selection breakdown
        summary_file = batch_dir / "BATCH_SUMMARY.txt"
        summary_content = self._render_updated_summary(manifest)
        summary_file.write_text(summary_content, encoding="utf-8")

        return {
            "batch_id": manifest.get("batch_id"),
            "winner": winner,
            "all_scored_clips": scored_clips,
            "manifest_file": manifest_file,
            "summary_file": summary_file,
        }

    def _render_updated_summary(self, manifest: Dict[str, Any]) -> str:
        """Render updated plain-text summary highlighting the selected clip."""
        lines = [
            "=======================================================",
            f"AI SHORTS AUTONOMOUS BATCH REPORT: {manifest.get('batch_id')}",
            f"Generated: {manifest.get('timestamp')}",
            f"Total Videos Rendered: {manifest.get('total_videos')}",
            f"Total Execution Time: {manifest.get('total_batch_seconds')} seconds",
            "=======================================================\n",
        ]

        if manifest.get("mode1", {}).get("status") == "SUCCESS":
            m1 = manifest["mode1"]
            lines.extend([
                "[MODE 1: FACELESS NARRATIVE & FACTS]",
                f"Topic:    {m1.get('topic')}",
                f"Title:    {m1.get('title')}",
                f"Video:    {Path(m1.get('video_path', '')).name}",
                f"Duration: {m1.get('duration')}s",
                f"Metadata: {Path(m1.get('metadata_path', '')).name if m1.get('metadata_path') else 'N/A'}",
                "",
            ])

        if manifest.get("mode2", {}).get("status") == "SUCCESS":
            m2 = manifest["mode2"]
            lines.extend([
                "[MODE 2: DEVELOPER VS CLAUDE TECH DIALOGUE]",
                f"Topic:    {m2.get('topic')}",
                f"Title:    {m2.get('title')}",
                f"Video:    {Path(m2.get('video_path', '')).name}",
                f"Duration: {m2.get('duration')}s",
                f"Metadata: {Path(m2.get('metadata_path', '')).name if m2.get('metadata_path') else 'N/A'}",
                "",
            ])

        if manifest.get("mode3", {}).get("status") == "SUCCESS":
            m3 = manifest["mode3"]
            selected = m3.get("selected_clip", {})
            lines.extend([
                "[MODE 3: PODCAST & VIDEO VIRAL CLIPS]",
                f"Source: {m3.get('source_title')} ({m3.get('source_channel')})",
                f"URL:    {m3.get('source_url')}",
                f"Total Clips Generated: {m3.get('clips_count')}",
                "",
                ">>> SELECTED FOR UPLOAD (WINNER) <<<",
                f"Clip Title:      {selected.get('title')}",
                f"Video File:      {Path(selected.get('video_path', '')).name}",
                f"Composite Score: {selected.get('composite_upload_score', 'N/A')}/100 (Tournament Viral Score: {selected.get('viral_score')}/100)",
                f"Duration:        {selected.get('duration')}s",
                f"Hook Sentence:   \"{selected.get('hook_sentence', '')}\"",
                f"Selection Logic: {selected.get('selection_reason')}",
                f"Metadata File:   {Path(selected.get('metadata_path', '')).name}",
                "",
                "Candidate Clips Ranking:",
            ])
            for clip in m3.get("clips", []):
                badge = "[SELECTED FOR UPLOAD]" if clip.get("selected_for_upload") else f"[RUNNER-UP #{clip.get('selection_rank')}]"
                lines.append(
                    f"  * #{clip.get('rank')} [{clip.get('composite_upload_score')}/100] {badge}: "
                    f"{Path(clip.get('video_path', '')).name} ({clip.get('duration')}s)"
                )
            lines.append("")

        if manifest.get("errors"):
            lines.extend([
                "[WARNINGS / ERRORS DURING RUN]",
                "\n".join([f"- {e}" for e in manifest["errors"]]),
                "",
            ])

        return "\n".join(lines)
