"""Unit tests for Meta-Learning & Flywheel Engine service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_flywheel.modules.cross_venture.meta_learning.schemas import RecordMetricRequest
from ai_flywheel.modules.cross_venture.meta_learning.service import MetaLearningEngine


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    bus = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def fake_metrics():
    """Create fake FlywheelMetric ORM objects."""
    metrics = []
    for i, (val, period) in enumerate(
        [(0.8, "2026-W22"), (0.7, "2026-W21"), (0.6, "2026-W20"), (0.5, "2026-W19")]
    ):
        m = MagicMock()
        m.id = f"metric-{i}"
        m.venture_id = "ven-001"
        m.metric_name = "velocity"
        m.value = val
        m.period = period
        m.recorded_at = datetime(2026, 5, 20 + i, tzinfo=UTC)
        metrics.append(m)
    return metrics


@patch("ai_flywheel.modules.cross_venture.meta_learning.service.get_event_bus")
@patch("ai_flywheel.modules.cross_venture.meta_learning.service.get_global_session")
async def test_record_metric(mock_get_session, mock_get_event_bus, mock_session, mock_event_bus):
    """record_metric should persist a metric and emit an event."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    def add_side_effect(obj):
        obj.id = "metric-new-001"
        obj.recorded_at = datetime(2026, 6, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect

    engine = MetaLearningEngine()
    request = RecordMetricRequest(
        venture_id="ven-001", metric_name="velocity", value=0.85, period="2026-W23"
    )
    result = await engine.record_metric(request)

    assert result.venture_id == "ven-001"
    assert result.metric_name == "velocity"
    assert result.value == 0.85
    mock_session.add.assert_called_once()
    mock_event_bus.publish.assert_awaited_once()
    assert mock_event_bus.publish.call_args[1]["event_type"] == "flywheel.metric.recorded"


@patch("ai_flywheel.modules.cross_venture.meta_learning.service.get_global_session")
async def test_get_velocity(mock_get_session, mock_session, fake_metrics):
    """get_velocity should compute velocity from last 4 metrics."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = fake_metrics
    mock_session.execute.return_value = result_mock

    engine = MetaLearningEngine()
    report = await engine.get_velocity("ven-001")

    # avg of [0.8, 0.7, 0.6, 0.5] = 0.65; latest = 0.8 > avg => accelerating
    assert report.venture_id == "ven-001"
    assert report.velocity_score == pytest.approx(0.65)
    assert report.trend == "accelerating"
    assert len(report.metrics) == 4


@patch("ai_flywheel.modules.cross_venture.meta_learning.service.get_global_session")
async def test_get_flywheel_report(mock_get_session, mock_session, fake_metrics):
    """get_flywheel_report should aggregate across ventures."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)

    # First call: distinct venture IDs
    ven_result = MagicMock()
    ven_result.all.return_value = [("ven-001",), ("ven-002",)]

    # Subsequent calls: metrics for get_velocity (called for each venture)
    metrics_result_1 = MagicMock()
    metrics_result_1.scalars.return_value.all.return_value = fake_metrics

    # ven-002 has lower metrics
    low_metrics = []
    for i, val in enumerate([0.3, 0.2, 0.2, 0.1]):
        m = MagicMock()
        m.id = f"metric-low-{i}"
        m.venture_id = "ven-002"
        m.metric_name = "velocity"
        m.value = val
        m.period = f"2026-W{19+i}"
        m.recorded_at = datetime(2026, 5, 20 + i, tzinfo=UTC)
        low_metrics.append(m)

    metrics_result_2 = MagicMock()
    metrics_result_2.scalars.return_value.all.return_value = low_metrics

    # Insights query
    insights_result = MagicMock()
    insights_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        ven_result,
        metrics_result_1,
        metrics_result_2,
        insights_result,
    ]

    engine = MetaLearningEngine()
    report = await engine.get_flywheel_report()

    assert report.total_ventures == 2
    # avg velocity: (0.65 + 0.2) / 2 = 0.425
    assert report.avg_velocity == pytest.approx(0.425)
    assert report.fastest_venture["venture_id"] == "ven-001"
    assert report.slowest_venture["venture_id"] == "ven-002"


@patch("ai_flywheel.modules.cross_venture.meta_learning.service.get_event_bus")
@patch("ai_flywheel.modules.cross_venture.meta_learning.service.get_global_session")
async def test_generate_insights(
    mock_get_session, mock_get_event_bus, mock_session, mock_event_bus
):
    """generate_insights should identify outlier ventures."""
    mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_session.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_get_event_bus.return_value = mock_event_bus

    # Create metrics where ven-001 is clearly outperforming
    all_metrics = []
    for val in [0.9, 0.85, 0.88]:
        m = MagicMock()
        m.venture_id = "ven-001"
        m.value = val
        m.metric_name = "velocity"
        m.period = "2026-W22"
        m.recorded_at = datetime(2026, 5, 20, tzinfo=UTC)
        all_metrics.append(m)

    for val in [0.2, 0.15, 0.18]:
        m = MagicMock()
        m.venture_id = "ven-002"
        m.value = val
        m.metric_name = "velocity"
        m.period = "2026-W22"
        m.recorded_at = datetime(2026, 5, 20, tzinfo=UTC)
        all_metrics.append(m)

    # First call: get all recent metrics
    metrics_result = MagicMock()
    metrics_result.scalars.return_value.all.return_value = all_metrics

    # Simulate insight being saved (set id and generated_at on add)
    def add_side_effect(obj):
        obj.id = "insight-001"
        obj.generated_at = datetime(2026, 6, 1, tzinfo=UTC)

    mock_session.add.side_effect = add_side_effect
    mock_session.execute.return_value = metrics_result

    engine = MetaLearningEngine()
    insights = await engine.generate_insights()

    # ven-001 avg=0.877, ven-002 avg=0.177 => overall avg ~0.527
    # ven-001 is 0.877 > 0.527*1.5=0.79 => acceleration_detected
    # ven-002 is 0.177 < 0.527*0.5=0.264 => bottleneck_identified
    assert len(insights) >= 1
    insight_types = [i.insight_type for i in insights]
    assert "acceleration_detected" in insight_types or "bottleneck_identified" in insight_types
