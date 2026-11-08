"""Unit and Integration Tests for Mode 2 Reddit & Story Gameplay Generator."""

import pytest
from pathlib import Path
from src.story.speech_normalizer import normalize_for_speech
from src.story.card_renderer import RedditCardRenderer
from src.story.story_fetcher import StoryFetcher
from src.story.pipeline import Mode2StoryPipeline, slugify


def test_speech_normalizer_acronyms():
    raw_text = "AITA for telling my MIL that my SIL cannot bring her BF to the wedding? TL;DR: OP is angry."
    normalized = normalize_for_speech(raw_text)

    assert "Am I the asshole" in normalized
    assert "Mother in law" in normalized
    assert "Sister in law" in normalized
    assert "boyfriend" in normalized
    assert "Too long didn't read" in normalized
    assert "the original poster" in normalized


def test_speech_normalizer_markdown_stripping():
    raw_text = "**Bold Title** with *italics* and ~~strike~~ and [link](https://reddit.com). > Quote here."
    normalized = normalize_for_speech(raw_text)

    assert "**" not in normalized
    assert "~~" not in normalized
    assert "https://" not in normalized
    assert "Bold Title" in normalized
    assert "Quote here." in normalized


def test_card_renderer_output(tmp_path):
    renderer = RedditCardRenderer()
    sample_story = {
        "subreddit": "r/AmItheAsshole",
        "author": "u/throwaway_tester",
        "title": "AITA for walking out of my sister's wedding rehearsal after what she said about my wife?",
        "score": "42.1k",
        "comments_count": "3.1k",
        "body": "My sister is getting married this Saturday and made a toast that shocked the room.",
    }

    out_png = tmp_path / "test_reddit_card.png"
    result = renderer.render_card(
        story=sample_story,
        output_png=out_png,
        canvas_width=1080,
        canvas_height=960,
        card_width=980,
    )

    assert result.exists()
    assert result.stat().st_size > 10000  # Non-trivial image file


def test_story_fetcher_count_formatting():
    fetcher = StoryFetcher(api_key="mock_key")
    assert fetcher._format_count(950) == "950"
    assert fetcher._format_count(15400) == "15.4k"
    assert fetcher._format_count(2500000) == "2.5M"


def test_slugify_helper():
    title = "AITA for telling my sister: 'No White Dresses!'?"
    slug = slugify(title)
    assert "aita" in slug
    assert ":" not in slug
    assert "'" not in slug


def test_mode2_pipeline_initialization():
    pipeline = Mode2StoryPipeline()
    assert pipeline.story_fetcher is not None
    assert pipeline.card_renderer is not None
    assert pipeline.gameplay_manager is not None
    assert pipeline.voice_engine is not None
    assert pipeline.transcriber is not None
    assert pipeline.editor is not None

