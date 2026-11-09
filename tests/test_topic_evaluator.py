import pytest
from src.pipeline.topic_evaluator import TopicEvaluator


def test_topic_evaluator_scoring():
    evaluator = TopicEvaluator()
    # A strong viral topic candidate
    topic = "Why supermarkets deliberately hide clocks and build mazes"
    res = evaluator.evaluate(topic)

    assert res.topic == topic
    assert res.total_score >= 0 and res.total_score <= 100
    assert len(res.criteria_breakdown) == 6
    assert res.format_type in ["counter_intuitive_truth", "mystery_breakdown", "psychological_dilemma"]
    assert len(res.angle) > 5


def test_topic_evaluator_rejects_generic_trivia():
    evaluator = TopicEvaluator()
    # Weak, passive, non-engaging generic textbook trivia
    weak_topic = "What is the chemical formula of table salt and how is it mined"
    res = evaluator.evaluate(weak_topic)

    assert res.approved is False or res.total_score < 75
