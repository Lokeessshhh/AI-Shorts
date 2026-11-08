import os
from pathlib import Path
import pytest
from src.clipper.downloader import VideoDownloader
from src.config import config


def test_rapidapi_download_slice():
    """Verify that RapidAPI trims and downloads a YouTube video slice directly."""
    downloader = VideoDownloader()
    test_video_url = "https://www.youtube.com/watch?v=dNIef2fGLQY"
    out_path = config.temp_dir / "test_rapidapi_unit_slice.mp4"

    res = downloader.download_slice(
        source=test_video_url,
        start_time=100.0,
        end_time=115.0,
        output_path=out_path,
    )

    assert res.exists(), "Downloaded slice file must exist"
    assert res.stat().st_size > 50000, "Slice file must not be empty"

    # Cleanup
    if res.exists():
        res.unlink()
