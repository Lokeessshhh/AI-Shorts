"""Unit and Integration Tests for Mode 3 Smart Clipper Engine."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.clipper.downloader import VideoDownloader
from src.clipper.highlight_detector import HighlightDetector
from src.clipper.reframe import SmartReframer, DetectionSmoother
from src.clipper.editor import ShortEditor


def test_downloader_url_detection():
    dl = VideoDownloader()
    assert dl.is_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert dl.is_url("http://youtu.be/test") is True
    assert dl.is_url("assets/test_video.mp4") is False
    assert dl.is_url("C:\\Users\\video.mp4") is False


def test_detection_smoother():
    smoother = DetectionSmoother(alpha=0.1)
    x1, y1 = smoother.update(100.0, 200.0)
    assert (x1, y1) == (100, 200)

    # Next update should smoothly interpolate
    x2, y2 = smoother.update(200.0, 300.0)
    assert x2 == 110  # 100 + 0.1 * (200 - 100) = 110
    assert y2 == 210  # 200 + 0.1 * (300 - 200) = 210


def test_reframe_filtergraph_solo():
    reframer = SmartReframer()
    analysis = {
        "layout": "solo",
        "src_w": 1920,
        "src_h": 1080,
        "crop": {"x": 400, "y": 0, "w": 607, "h": 1080},
    }
    fg = reframer.generate_ffmpeg_filtergraph(analysis, out_w=1080, out_h=1920)
    assert "crop=607:1080:400:0" in fg
    assert "scale=1080:1920" in fg
    assert "v_reframe" in fg


def test_reframe_filtergraph_split_screen():
    reframer = SmartReframer()
    analysis = {
        "layout": "split_screen",
        "src_w": 1920,
        "src_h": 1080,
        "speaker_1_crop": {"x": 100, "y": 0, "w": 607, "h": 1080},
        "speaker_2_crop": {"x": 1200, "y": 0, "w": 607, "h": 1080},
    }
    fg = reframer.generate_ffmpeg_filtergraph(analysis, out_w=1080, out_h=1920)
    assert "vstack" in fg
    assert "scale=1080:960" in fg
    assert "drawbox=" in fg


def test_reframe_filtergraph_blurred_fallback():
    reframer = SmartReframer()
    analysis = {
        "layout": "blurred_fallback",
        "src_w": 1920,
        "src_h": 1080,
    }
    fg = reframer.generate_ffmpeg_filtergraph(analysis, out_w=1080, out_h=1920)
    assert "boxblur=" in fg
    assert "overlay=" in fg


def test_snap_and_enrich_highlights():
    detector = HighlightDetector(api_key="mock_key")
    all_words = [
        {"word": "Why", "start": 10.1, "end": 10.4},
        {"word": "people", "start": 10.5, "end": 10.8},
        {"word": "fail", "start": 10.9, "end": 11.3},
        {"word": "is", "start": 11.4, "end": 11.6},
        {"word": "simple.", "start": 11.7, "end": 12.2},
        {"word": "They", "start": 12.5, "end": 12.8},
        {"word": "give", "start": 12.9, "end": 13.2},
        {"word": "up", "start": 13.3, "end": 13.5},
        {"word": "early.", "start": 13.6, "end": 42.0},  # span 32 seconds
    ]
    raw = [
        {
            "rank": 1,
            "title": "Why People Fail",
            "start_time": 10.0,
            "end_time": 41.5,
            "viral_score": 92,
            "hook_sentence": "Why people fail is simple.",
            "virality_reason": "High retention hook.",
            "hashtags": ["#success", "#shorts"],
        }
    ]
    snapped = detector._snap_and_enrich_highlights(
        raw_highlights=raw,
        all_words=all_words,
        min_duration=30.0,
        max_duration=60.0,
        num_clips=1,
    )
    assert len(snapped) == 1
    clip = snapped[0]
    assert clip["start_time"] == 10.1  # snapped to 'Why'
    assert clip["end_time"] == 42.0    # snapped to 'early.'
    assert clip["duration"] == 31.9
    assert len(clip["words"]) == len(all_words)
    assert clip["words"][0]["start"] == 0.0  # relative to cut start
