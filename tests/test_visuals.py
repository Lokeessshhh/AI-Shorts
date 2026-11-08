import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.visuals.pexels import PexelsVisualFetcher
from src.visuals.motion import get_ken_burns_filter


def test_visuals_fetch_and_fallback():
    fetcher = PexelsVisualFetcher()
    clip = fetcher.fetch_clip_for_scene(
        scene_id=1,
        keywords=["casino neon lights", "las vegas night"],
        duration=3.5,
    )

    assert clip.file_path.exists()
    assert clip.file_path.stat().st_size > 1000
    print(f"\n[PASSED] Visual clip prepared: {clip.file_path.name}")
    print(f"Size: {clip.file_path.stat().st_size} bytes | Keyword: {clip.keyword}")

    # Test Ken Burns filter generation
    filter_str = get_ken_burns_filter(duration_seconds=3.5)
    assert "zoompan=" in filter_str
    print(f"[PASSED] Ken Burns filter verified: {filter_str[:40]}...")


def test_visual_deduplication():
    fetcher = PexelsVisualFetcher()
    fetcher.reset_session()

    # Request 4 clips with potentially overlapping keywords
    c1 = fetcher.fetch_clip_for_scene(1, ["brain"], 2.0)
    c2 = fetcher.fetch_clip_for_scene(2, ["brain"], 2.0)
    c3 = fetcher.fetch_clip_for_scene(3, ["thinking"], 2.0)
    c4 = fetcher.fetch_clip_for_scene(4, ["microscope"], 2.0)

    # Verify that session tracked distinct clips
    assert len(fetcher.session_used_files) >= 4 or len(fetcher.session_used_urls) >= 4
    print(f"\n[PASSED] Deduplication verified across {len(fetcher.session_used_files)} unique clips in session.")


if __name__ == "__main__":
    test_visuals_fetch_and_fallback()
    test_visual_deduplication()
