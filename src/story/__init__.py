"""Mode 2: Narrative, Reddit Stories & Gameplay Video Generator.
Supports Reddit URL scraping, trending subreddits, AI-generated dramatic stories,
Pillow dark-mode card rendering, gameplay looping, and 50/50 split-screen assembly.
"""

from .pipeline import Mode2StoryPipeline, run_story_generator

__all__ = ["Mode2StoryPipeline", "run_story_generator"]
