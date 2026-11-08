"""State Manager for Autonomous AI Shorts Engine.
Persists completed topics, clipped YouTube IDs, and batch execution records in data/automation_history.json.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..config import config


def normalize_topic(text: str) -> str:
    """Normalize topic to lowercase, alphanumeric-only for deduplication."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in cleaned.split() if len(w) > 1]
    return " ".join(words)


class StateManager:
    """Manages persistent automation state and history."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or (config.root_dir / "data" / "automation_history.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, Any] = {
            "completed_topics": [],
            "clipped_youtube_ids": [],
            "batch_history": [],
            "last_updated": datetime.now().isoformat(),
        }
        self._load_state()

    def _load_state(self) -> None:
        """Load state from disk, or initialize if not present."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.state["completed_topics"] = data.get("completed_topics", [])
                        self.state["clipped_youtube_ids"] = data.get("clipped_youtube_ids", [])
                        self.state["batch_history"] = data.get("batch_history", [])
                        self.state["last_updated"] = data.get("last_updated", datetime.now().isoformat())
                        return
            except Exception as e:
                print(f"[StateManager] Warning: Failed to read state file ({e}). Starting fresh.")

        # Seed initial topics from output directory if starting fresh
        self._seed_from_output_dir()
        self._save_state()

    def _seed_from_output_dir(self) -> None:
        """Pre-seed completed topics from existing output videos."""
        if not config.output_dir.exists():
            return

        seeded = set()
        for mp4 in config.output_dir.glob("*.mp4"):
            stem = mp4.stem
            # Clean common prefixes & timestamp suffixes
            stem = re.sub(r"_\d{9,11}$", "", stem)
            stem = stem.replace("dev_claude_encyclopedia_", "").replace("dev_claude_", "")
            stem = stem.replace("_", " ")
            norm = normalize_topic(stem)
            if norm and len(norm) > 4:
                seeded.add(norm)

        for topic in sorted(seeded):
            if topic not in self.state["completed_topics"]:
                self.state["completed_topics"].append(topic)

    def _save_state(self) -> None:
        """Atomically persist state to disk."""
        self.state["last_updated"] = datetime.now().isoformat()
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.state_file)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            print(f"[StateManager] Error saving state: {e}")

    def is_topic_fresh(self, topic: str) -> bool:
        """Check if topic has not been generated before (exact match & high word overlap)."""
        norm = normalize_topic(topic)
        if not norm:
            return False

        # 1. Exact normalized match
        if norm in self.state["completed_topics"]:
            return False

        # 2. Overlap similarity check (if > 75% words match an existing topic)
        norm_words = set(norm.split())
        for completed in self.state["completed_topics"]:
            comp_words = set(completed.split())
            if not comp_words:
                continue
            common = norm_words.intersection(comp_words)
            overlap = len(common) / max(len(norm_words), len(comp_words))
            if overlap >= 0.75:
                return False

        return True

    def mark_topic_done(
        self,
        topic: str,
        mode: str = "general",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a topic as completed and save to state."""
        norm = normalize_topic(topic)
        if norm and norm not in self.state["completed_topics"]:
            self.state["completed_topics"].append(norm)

        # Log entry in batch history or record
        entry_meta = metadata.copy() if metadata else {}
        if title:
            entry_meta["title"] = title

        entry = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "topic": topic,
            "normalized": norm,
            "metadata": entry_meta,
        }
        self.state.setdefault("topic_logs", []).append(entry)
        self._save_state()

    def is_video_clipped(self, video_id: str) -> bool:
        """Check if a YouTube video has already been clipped."""
        clean_id = video_id.strip()
        return clean_id in self.state["clipped_youtube_ids"]

    def mark_video_clipped(
        self, video_id: str, title: str = "", metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a YouTube video ID as clipped."""
        clean_id = video_id.strip()
        if clean_id and clean_id not in self.state["clipped_youtube_ids"]:
            self.state["clipped_youtube_ids"].append(clean_id)

        self.state.setdefault("clip_logs", []).append({
            "timestamp": datetime.now().isoformat(),
            "video_id": clean_id,
            "title": title,
            "metadata": metadata or {},
        })
        self._save_state()

    def record_batch(self, batch_data: Dict[str, Any]) -> None:
        """Log a full autonomous batch execution into state history."""
        self.state.setdefault("batch_history", []).append(batch_data)
        self._save_state()

    def get_completed_topics(self) -> List[str]:
        """Return list of all completed normalized topics."""
        return list(self.state.get("completed_topics", []))

    def get_clipped_ids(self) -> List[str]:
        """Return list of all clipped YouTube video IDs."""
        return list(self.state.get("clipped_youtube_ids", []))
