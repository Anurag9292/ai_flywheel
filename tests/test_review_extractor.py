"""Tests for the review/ratings extractor + sentiment view (Phase 1)."""

from __future__ import annotations

from flywheel.nodes.knowledge_builder import (
    ReviewExtractor,
    StructuralExtractor,
    _extractor_for_kind,
    classify_sentiment,
)
from flywheel.persistence.models import RawRecord


def test_classify_sentiment_rating_dominates() -> None:
    assert classify_sentiment(1, "this is actually fine") == "negative"
    assert classify_sentiment(5, "ignore the text") == "positive"
    assert classify_sentiment(3, "") == "neutral"


def test_classify_sentiment_lexicon_fallback() -> None:
    assert classify_sentiment(None, "buggy, slow and terrible — want a refund") == "negative"
    assert classify_sentiment(None, "fast, reliable and intuitive, love it") == "positive"
    assert classify_sentiment(None, "it exists") == "neutral"


def test_extractor_selection_by_kind() -> None:
    assert isinstance(_extractor_for_kind("review-feed"), ReviewExtractor)
    assert isinstance(_extractor_for_kind("ratings"), ReviewExtractor)
    # Unknown / job kinds fall back to the structural (job) extractor.
    assert isinstance(_extractor_for_kind("ats-job-board"), StructuralExtractor)
    assert isinstance(_extractor_for_kind(""), StructuralExtractor)


def test_review_extractor_builds_graph() -> None:
    rec = RawRecord(
        source_id="reviews-acme",
        venture_id="v1",
        external_id="rv-1",
        raw={
            "company": "Acme",
            "product": "Acme Dashboard",
            "rating": 1,
            "body": "constant outages",
        },
    )
    entities, edges = ReviewExtractor().extract(rec)
    types = {e.type for e in entities}
    assert {"Review", "Company", "Product"} <= types
    review = next(e for e in entities if e.type == "Review")
    assert review.props["sentiment"] == "negative"
    edge_types = {e.type for e in edges}
    assert {"reviewed", "about_product"} <= edge_types
