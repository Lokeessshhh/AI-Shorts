"""Mode 3: Long-Form Video & Podcast Smart Clipper.
Automated viral highlight detection, OpenCV active-speaker reframing, dynamic ASS subtitles, and FFmpeg polish.
"""

from .pipeline import Mode3ClipperPipeline, run_clipper

__all__ = ["Mode3ClipperPipeline", "run_clipper"]
