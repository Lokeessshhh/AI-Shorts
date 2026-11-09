import pytest
from src.visuals.multi_source_fetcher import MultiSourceFetcher
from src.visuals.diagram_engine import DiagramEngine
from src.config import config


def test_multi_source_fetcher_wikimedia():
    fetcher = MultiSourceFetcher()
    candidates = fetcher._search_wikimedia("De Havilland Comet 1953", limit=2)
    assert len(candidates) > 0
    c = candidates[0]
    assert c.source == "wikimedia_commons"
    assert c.full_download_url.startswith("http")
    assert len(c.attribution) > 0


def test_diagram_engine_render():
    engine = DiagramEngine()
    out_path = config.temp_dir / "unit_test_diagram.png"
    res = engine.render_technical_callout(
        title="Corner Stress Physics",
        flaw_label="Square Window",
        flaw_detail="Concentrated Stress (+70%)",
        solution_label="Rounded Window",
        solution_detail="Smooth Pressure Dissipation",
        output_path=out_path,
    )
    assert res.exists()
    assert res.stat().st_size > 10000


def test_muse_visual_reranker_evaluation():
    from src.visuals.visual_reranker import MuseVisualReranker
    from src.llm.prompts import VisualIntent
    from src.visuals.multi_source_fetcher import MultiSourceFetcher

    fetcher = MultiSourceFetcher()
    candidates = fetcher.discover_candidates(
        queries=["De Havilland Comet 1953 aircraft", "vintage airplane"],
        entity_type="historical_event",
        preferred_modality="archival_photo",
        max_total_candidates=2,
    )

    reranker = MuseVisualReranker()
    vi = VisualIntent(
        entity_type="historical_event",
        primary_entity="De Havilland Comet 1953",
        visual_action="aircraft inspection",
        temporal_era="1950s",
        preferred_modality="archival_photo",
    )
    result = reranker.rerank_and_verify(
        narration="In 1953, two passenger jets shattered mid-air because of square windows.",
        visual_intent=vi,
        candidates=candidates,
    )

    assert result.winning_score >= 0
    assert isinstance(result.evaluations, list)
