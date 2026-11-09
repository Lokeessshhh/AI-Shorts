"""Autonomous Batch Publisher.
Publishes the 3 premier shorts of an automated batch (Mode 1, Mode 2, and winning Mode 3 clip)
to both YouTube Shorts and Instagram Reels.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from .youtube_uploader import YouTubeUploader
from .instagram_uploader import InstagramUploader


class BatchPublisher:
    """Coordinates multi-platform publishing of a finished AI Shorts batch."""

    def __init__(
        self,
        youtube_uploader: Optional[YouTubeUploader] = None,
        instagram_uploader: Optional[InstagramUploader] = None,
    ):
        self.yt = youtube_uploader or YouTubeUploader()
        self.insta = instagram_uploader or InstagramUploader()

    def publish_batch(
        self,
        batch_dir: Path,
        platforms: Optional[List[str]] = None,
        privacy_status: str = "public",
        delete_after_upload: bool = True,
        delete_unselected_clips: bool = True,
    ) -> Dict[str, Any]:
        """
        Publish Mode 1, Mode 2, and winning Mode 3 short from batch folder.
        platforms: ["youtube", "instagram"] or subset. Defaults to all authenticated.
        delete_after_upload: Automatically delete local MP4s once successfully published.
        delete_unselected_clips: Automatically purge Mode 3 runner-up clips that were not selected for upload.
        """
        manifest_file = batch_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found in {batch_dir}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Detect active platforms
        if platforms is None:
            platforms = []
            if self.yt.is_authenticated():
                platforms.append("youtube")
            if self.insta.is_authenticated():
                platforms.append("instagram")

        if not platforms:
            print("[BatchPublisher] Warning: Neither YouTube nor Instagram is authenticated.")
            print("  * For YouTube:   Run 'python -m src.publisher.auth_youtube'")
            print("  * For Instagram: Run 'python -m src.publisher.auth_instagram'")
            return {"status": "SKIPPED", "reason": "No authenticated platforms"}

        print("\n" + "=" * 70)
        print(f"🚀  PUBLISHING BATCH: {manifest.get('batch_id')}")
        print(f"    Target Platforms: {', '.join(platforms).upper()}")
        print(f"    Batch Directory:  {batch_dir}")
        print("=" * 70)

        # Prepare upload items:
        # Item 1: Mode 1 (Faceless Facts)
        # Item 2: Mode 2 (Smart Clipper Winning Clip)
        items_to_upload = []

        # 1. Mode 1
        m1 = manifest.get("mode1", {})
        if m1.get("status") == "SUCCESS" and m1.get("video_path"):
            items_to_upload.append({
                "mode": "mode1_facts",
                "label": "Mode 1 (Faceless Facts)",
                "video_path": Path(m1["video_path"]),
                "metadata_path": Path(m1["metadata_path"]) if m1.get("metadata_path") else None,
            })

        # 2. Mode 2 (Smart Clipper Winning Clip)
        m2 = manifest.get("mode2", {})
        selected_clip = m2.get("selected_clip")
        if not selected_clip:
            for cand_dir in ["mode2_clipper", "mode2"]:
                p_selected = batch_dir / cand_dir / "selected_for_upload.json"
                if p_selected.exists():
                    try:
                        with open(p_selected, "r", encoding="utf-8") as f:
                            selected_clip = json.load(f)
                        break
                    except Exception:
                        pass
            if not selected_clip and m2.get("video_path"):
                selected_clip = m2

        if selected_clip and selected_clip.get("video_path"):
            items_to_upload.append({
                "mode": "mode2_clipper_winner",
                "label": f"Mode 2 Winning Clip (#{selected_clip.get('rank', 1)})",
                "video_path": Path(selected_clip["video_path"]),
                "metadata_path": Path(selected_clip["metadata_path"]) if selected_clip.get("metadata_path") else None,
            })

        # 3. Mode 3 (ChatGPT Conversation Comedy Short)
        m3 = manifest.get("mode3", {})
        if m3.get("status") == "SUCCESS" and m3.get("video_path"):
            items_to_upload.append({
                "mode": "mode3_chatgpt",
                "label": "Mode 3 (ChatGPT Comedy Short)",
                "video_path": Path(m3["video_path"]),
                "metadata_path": Path(m3["metadata_path"]) if m3.get("metadata_path") else None,
            })

        print(f"\n[BatchPublisher] Identified {len(items_to_upload)} premier shorts to upload:")
        for item in items_to_upload:
            print(f"  * {item['label']}: {item['video_path'].name}")

        publish_log = []

        for idx, item in enumerate(items_to_upload, start=1):
            vpath = item["video_path"]
            mpath = item["metadata_path"]

            print("\n" + "-" * 70)
            print(f"[{idx}/{len(items_to_upload)}] Publishing {item['label']}...")
            print("-" * 70)

            item_result = {
                "mode": item["mode"],
                "video_name": vpath.name,
                "uploads": {},
            }

            # Upload to YouTube
            if "youtube" in platforms:
                try:
                    yt_res = self.yt.upload_from_metadata(
                        video_path=vpath,
                        metadata_path=mpath,
                        privacy_status=privacy_status,
                    )
                    item_result["uploads"]["youtube"] = yt_res
                except Exception as e:
                    print(f"  * [ERROR/YouTube] Upload failed: {e}")
                    item_result["uploads"]["youtube"] = {"status": "FAILED", "error": str(e)}

            # Upload to Instagram
            if "instagram" in platforms:
                try:
                    # Give brief breathing room between uploads
                    time.sleep(3)
                    insta_res = self.insta.upload_from_metadata(
                        video_path=vpath,
                        metadata_path=mpath,
                    )
                    item_result["uploads"]["instagram"] = insta_res
                except Exception as e:
                    print(f"  * [ERROR/Instagram] Upload failed: {e}")
                    item_result["uploads"]["instagram"] = {"status": "FAILED", "error": str(e)}

            # Clean up local video file if upload succeeded
            if delete_after_upload and item_result["uploads"]:
                has_success = any(up.get("status") == "SUCCESS" for up in item_result["uploads"].values())
                has_failure = any(up.get("status") == "FAILED" for up in item_result["uploads"].values())

                if has_success and not has_failure and vpath.exists():
                    try:
                        vpath.unlink()
                        item_result["local_video_deleted"] = True
                        print(f"  * [Cleanup] Purged published video from disk: {vpath.name}")
                    except Exception as e:
                        print(f"  * [Cleanup] Could not delete {vpath.name}: {e}")

            publish_log.append(item_result)

        # Clean up unselected runner-up clips from Mode 2 / Mode 3 to save disk
        if delete_unselected_clips:
            m2_clips = manifest.get("mode2", {}).get("clips", []) or manifest.get("mode3", {}).get("clips", [])
            for c in m2_clips:
                if not c.get("selected_for_upload") and c.get("video_path"):
                    p_clip = Path(c["video_path"])
                    if p_clip.exists():
                        try:
                            p_clip.unlink()
                            print(f"  * [Cleanup] Purged unselected runner-up clip: {p_clip.name}")
                        except Exception:
                            pass

        # Save report in batch directory
        report_file = batch_dir / "PUBLISH_REPORT.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(publish_log, f, indent=2, ensure_ascii=False)

        # Update manifest
        manifest["publish_report"] = publish_log
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 70)
        print("🎉  BATCH PUBLISHING COMPLETED!")
        print(f"    Report: {report_file.name}")
        print("=" * 70 + "\n")

        return {
            "status": "COMPLETED",
            "batch_id": manifest.get("batch_id"),
            "report_file": report_file,
            "uploads": publish_log,
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Publish AI Shorts batch to YouTube and Instagram")
    parser.add_argument(
        "--batch-dir",
        type=str,
        required=True,
        help="Path to output/batch_YYYYMMDD_HHMMSS folder",
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=["youtube", "instagram"],
        default=None,
        help="Platforms to publish to (default: all authenticated)",
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["public", "unlisted", "private"],
        default="public",
        help="YouTube privacy status (default: public)",
    )

    args = parser.parse_args()
    publisher = BatchPublisher()
    publisher.publish_batch(
        batch_dir=Path(args.batch_dir),
        platforms=args.platforms,
        privacy_status=args.privacy,
    )
