import os
from pathlib import Path
import pytest
from src.clipper.downloader import VideoDownloader
from src.config import config


def test_supadata_integration():
    """Verify that Supadata API extracts full word-level transcripts for YouTube long-form videos."""
    downloader = VideoDownloader()
    test_video_url = "https://www.youtube.com/watch?v=dNIef2fGLQY"

    meta, transcript_data = downloader.get_transcript_and_meta(test_video_url)

    assert meta["id"] == "dNIef2fGLQY"
    assert "How Money Is Created" in meta["title"]
    assert meta["duration"] > 3000.0

    assert "total_words" in transcript_data
    assert transcript_data["total_words"] > 5000
    assert len(transcript_data["segments"]) > 500
    assert "words" in transcript_data
    assert len(transcript_data["words"]) == transcript_data["total_words"]
