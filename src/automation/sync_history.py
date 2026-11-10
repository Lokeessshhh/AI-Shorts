"""
Atomic, Conflict-Free Sync for data/automation_history.json.
Merges local changes with remote origin/main in memory to guarantee zero git merge
conflicts even when multiple GitHub Action workflows push simultaneously.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List

HISTORY_FILE = Path("data/automation_history.json")


def merge_histories(base_data: Dict[str, Any], incoming_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform semantic deduplicated merge of history records."""
    merged = dict(base_data)

    # 1. Merge completed_topics (preserve order, deduplicate)
    t_list: List[str] = list(base_data.get("completed_topics", []))
    for t in incoming_data.get("completed_topics", []):
        if t not in t_list:
            t_list.append(t)
    merged["completed_topics"] = t_list

    # 2. Merge clipped_youtube_ids (preserve order, deduplicate)
    c_list: List[str] = list(base_data.get("clipped_youtube_ids", []))
    for c in incoming_data.get("clipped_youtube_ids", []):
        if c not in c_list:
            c_list.append(c)
    merged["clipped_youtube_ids"] = c_list

    # 3. Merge batch_history (deduplicate by batch_id)
    batches_map = {}
    for b in base_data.get("batch_history", []):
        bid = b.get("batch_id")
        if bid:
            batches_map[bid] = b
    for b in incoming_data.get("batch_history", []):
        bid = b.get("batch_id")
        if bid:
            batches_map[bid] = b

    merged["batch_history"] = list(batches_map.values())
    return merged


def sync_and_push(max_retries: int = 5) -> bool:
    """Sync local history with remote origin/main and push conflict-free."""
    if not HISTORY_FILE.exists():
        print("[SyncHistory] No local history file found to sync.")
        return True

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            local_data = json.load(f)
    except Exception as e:
        print(f"[SyncHistory] Error reading local history: {e}")
        return True

    for attempt in range(max_retries):
        try:
            print(f"[SyncHistory] Sync attempt {attempt + 1}/{max_retries}...")
            # 1. Fetch latest origin/main
            subprocess.run(["git", "fetch", "origin", "main"], check=True, capture_output=True)

            # 2. Extract remote history content without branch checkout
            show_res = subprocess.run(
                ["git", "show", "origin/main:data/automation_history.json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if show_res.returncode == 0 and show_res.stdout.strip():
                try:
                    remote_data = json.loads(show_res.stdout)
                    final_data = merge_histories(remote_data, local_data)
                except Exception:
                    final_data = local_data
            else:
                final_data = local_data

            # 3. Reset workspace state to origin/main
            subprocess.run(["git", "reset", "--hard", "origin/main"], check=True, capture_output=True)

            # 4. Write merged clean JSON
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            # 5. Check if changes exist
            diff_res = subprocess.run(["git", "diff", "--exit-code", str(HISTORY_FILE)], capture_output=True)
            if diff_res.returncode == 0:
                print("[SyncHistory] History matches remote. Nothing to commit.")
                return True

            # 6. Commit and Push
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", str(HISTORY_FILE)], check=True)
            subprocess.run(["git", "commit", "-m", "chore: update autonomous batch history [skip ci]"], check=True)

            push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
            if push_res.returncode == 0:
                print(f"[SyncHistory] Successfully synced and pushed history!")
                return True

            print(f"[SyncHistory] Push rejected (concurrent push detected), retrying in {attempt + 2}s...")
            time.sleep(attempt + 2)

        except Exception as e:
            print(f"[SyncHistory] Warning during sync attempt {attempt + 1}: {e}")
            time.sleep(attempt + 2)

    print("[SyncHistory] Notice: Reached max retries. Exiting cleanly.")
    return True


if __name__ == "__main__":
    sync_and_push()
