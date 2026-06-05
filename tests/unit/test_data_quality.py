# ruff: noqa: E501
"""Unit tests for Data Quality Engine — profiling, rules, scoring."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.data_knowledge.quality.schemas import (
    QualityCheckRequest,
)
from ai_flywheel.modules.data_knowledge.quality.service import DataQualityEngine

# ------------------------------------------------------------------
# Pure logic tests — profiling and rule evaluation
# ------------------------------------------------------------------


def test_profile_field_computes_stats():
    """profile_field should compute non_null_count, null_count, min, max, mean."""
    records = [
        {"value": 10},
        {"value": 20},
        {"value": 30},
        {"value": None},
        {"value": ""},
    ]
    profile = DataQualityEngine.profile_field(records, "value")

    assert profile.field_name == "value"
    assert profile.non_null_count == 3
    assert profile.null_count == 2
    assert profile.min_value == 10
    assert profile.max_value == 30
    assert profile.mean_value == 20.0
    assert profile.unique_count == 3


def test_not_null_rule_detects_nulls():
    """_evaluate_rule with not_null should detect null and empty values."""
    engine = DataQualityEngine()
    records = [
        {"name": "Alice"},
        {"name": ""},
        {"name": None},
        {"name": "Bob"},
    ]

    rule = MagicMock()
    rule.rule_type = "not_null"
    rule.field_name = "name"
    rule.config = {}
    rule.severity = "error"
    rule.name = "name_required"
    rule.id = "rule-001"

    issues, violating_indices, type_violations, total_checks = engine._evaluate_rule(
        rule, records
    )

    assert len(violating_indices) == 2  # empty string and None
    assert 1 in violating_indices
    assert 2 in violating_indices
    assert total_checks == 4


def test_range_rule_detects_out_of_range():
    """_evaluate_rule with range should flag values outside min/max."""
    engine = DataQualityEngine()
    records = [
        {"age": 25},
        {"age": 5},
        {"age": 150},
        {"age": 30},
        {"age": None},
    ]

    rule = MagicMock()
    rule.rule_type = "range"
    rule.field_name = "age"
    rule.config = {"min": 18, "max": 100}
    rule.severity = "error"
    rule.name = "age_range"
    rule.id = "rule-002"

    issues, violating_indices, type_violations, total_checks = engine._evaluate_rule(
        rule, records
    )

    assert len(violating_indices) == 2  # 5 (below min) and 150 (above max)
    assert 1 in violating_indices
    assert 2 in violating_indices


def test_quality_score_calculation():
    """Quality score should combine completeness, consistency, and error rate."""
    # quality_score = 0.4 * completeness + 0.3 * consistency + 0.3 * (1 - error_rate)
    completeness = 0.8
    consistency = 0.9
    error_rate = 0.1

    expected_score = 0.4 * completeness + 0.3 * consistency + 0.3 * (1.0 - error_rate)
    assert abs(expected_score - 0.86) < 0.001


def test_type_check_rule():
    """_evaluate_rule with type_check should flag values not matching expected type."""
    engine = DataQualityEngine()
    records = [
        {"score": 95},
        {"score": "not_a_number"},
        {"score": 88},
        {"score": None},  # None is skipped by type_check
    ]

    rule = MagicMock()
    rule.rule_type = "type_check"
    rule.field_name = "score"
    rule.config = {"expected_type": "int"}
    rule.severity = "warning"
    rule.name = "score_type"
    rule.id = "rule-003"

    issues, violating_indices, type_violations, total_checks = engine._evaluate_rule(
        rule, records
    )

    # "not_a_number" should violate
    assert 1 in violating_indices
    assert type_violations >= 1
    assert total_checks == 4


@patch("ai_flywheel.modules.data_knowledge.quality.service.get_tracer")
@patch("ai_flywheel.modules.data_knowledge.quality.service.get_event_bus")
@patch("ai_flywheel.modules.data_knowledge.quality.service.get_session")
@pytest.mark.asyncio
async def test_check_emits_event(mock_get_session, mock_get_event_bus, mock_get_tracer):
    """check should emit quality.check.completed event."""
    # Mock session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock DB returning no rules and generating a report ID
    added_objects = []

    def add_side_effect(obj):
        added_objects.append(obj)
        obj.id = "report-001"

    mock_session.add.side_effect = add_side_effect

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # No rules
    mock_session.execute = AsyncMock(return_value=mock_result)

    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mock_get_session.return_value = session_cm

    # Mock event bus
    mock_event_bus = AsyncMock()
    mock_event_bus.publish = AsyncMock()
    mock_get_event_bus.return_value = mock_event_bus

    # Mock tracer
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.set_cost = MagicMock()
    span_cm = AsyncMock()
    span_cm.__aenter__ = AsyncMock(return_value=mock_span)
    span_cm.__aexit__ = AsyncMock(return_value=False)
    mock_tracer.span.return_value = span_cm
    mock_get_tracer.return_value = mock_tracer

    engine = DataQualityEngine()
    request = QualityCheckRequest(
        records=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
        dataset_name="test_dataset",
    )
    result = await engine.check("ven-001", request)

    assert result.total_records == 2
    assert result.quality_score >= 0.0
    mock_event_bus.publish.assert_awaited()
    # Check that quality.check.completed event was published
    call_kwargs = mock_event_bus.publish.call_args_list[0][1]
    assert call_kwargs["event_type"] == "quality.check.completed"
