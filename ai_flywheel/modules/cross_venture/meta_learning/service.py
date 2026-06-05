"""Meta-Learning Engine service — velocity tracking, insights, cross-venture analysis."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import distinct, select

from ai_flywheel.core.database import get_global_session
from ai_flywheel.core.events import get_event_bus

from .models import CrossVentureInsight, FlywheelMetric
from .schemas import (
    FlywheelMetricResponse,
    FlywheelReport,
    InsightResponse,
    RecordMetricRequest,
    VelocityReport,
)

logger = structlog.get_logger()


def _metric_to_response(metric: FlywheelMetric) -> FlywheelMetricResponse:
    """Convert a FlywheelMetric ORM object to a response."""
    return FlywheelMetricResponse(
        id=metric.id,
        venture_id=metric.venture_id,
        metric_name=metric.metric_name,
        value=metric.value,
        period=metric.period,
        recorded_at=metric.recorded_at,
    )


def _insight_to_response(insight: CrossVentureInsight) -> InsightResponse:
    """Convert a CrossVentureInsight ORM object to a response."""
    return InsightResponse(
        id=insight.id,
        insight_type=insight.insight_type,
        title=insight.title,
        description=insight.description,
        evidence=insight.evidence,
        confidence=insight.confidence,
        affected_ventures=insight.affected_ventures,
        generated_at=insight.generated_at,
    )


class MetaLearningEngine:
    """Service for flywheel velocity tracking and cross-venture insights."""

    async def record_metric(self, request: RecordMetricRequest) -> FlywheelMetricResponse:
        """Record a flywheel metric for a venture."""
        async with get_global_session() as session:
            metric = FlywheelMetric(
                venture_id=request.venture_id,
                metric_name=request.metric_name,
                value=request.value,
                period=request.period,
                recorded_at=datetime.now(UTC),
            )
            session.add(metric)
            await session.flush()

            response = _metric_to_response(metric)

        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="flywheel.metric.recorded",
            source_module="meta_learning",
            payload={
                "venture_id": request.venture_id,
                "metric_name": request.metric_name,
                "value": request.value,
                "period": request.period,
            },
        )

        logger.info(
            "flywheel_metric_recorded",
            venture_id=request.venture_id,
            metric=request.metric_name,
            value=request.value,
        )
        return response

    async def get_velocity(self, venture_id: str) -> VelocityReport:
        """Compute flywheel velocity from recent metrics.

        Velocity = average of last 4 period metrics.
        Trend: "accelerating" if latest > avg, "decelerating" if below, else "stable".
        """
        async with get_global_session() as session:
            result = await session.execute(
                select(FlywheelMetric)
                .where(FlywheelMetric.venture_id == venture_id)
                .order_by(FlywheelMetric.recorded_at.desc())
                .limit(4)
            )
            metrics = result.scalars().all()

        if not metrics:
            return VelocityReport(
                venture_id=venture_id,
                metrics=[],
                velocity_score=0.0,
                trend="stable",
                comparison_to_previous=None,
            )

        values = [m.value for m in metrics]
        avg = sum(values) / len(values)
        latest = values[0]

        if latest > avg:
            trend = "accelerating"
        elif latest < avg:
            trend = "decelerating"
        else:
            trend = "stable"

        comparison = (latest - avg) / avg if avg != 0 else None

        return VelocityReport(
            venture_id=venture_id,
            metrics=[
                {"metric_name": m.metric_name, "value": m.value, "period": m.period}
                for m in metrics
            ],
            velocity_score=avg,
            trend=trend,
            comparison_to_previous=comparison,
        )

    async def get_flywheel_report(self) -> FlywheelReport:
        """Generate a cross-venture flywheel summary."""
        async with get_global_session() as session:
            # Get distinct venture IDs
            ven_result = await session.execute(
                select(distinct(FlywheelMetric.venture_id))
            )
            venture_ids = [row[0] for row in ven_result.all()]

        total_ventures = len(venture_ids)

        # Get velocity for each venture
        velocities: dict[str, float] = {}
        for vid in venture_ids:
            report = await self.get_velocity(vid)
            velocities[vid] = report.velocity_score

        avg_velocity = sum(velocities.values()) / max(len(velocities), 1)

        fastest = None
        slowest = None
        if velocities:
            fastest_id = max(velocities, key=velocities.get)
            slowest_id = min(velocities, key=velocities.get)
            fastest = {"venture_id": fastest_id, "velocity": velocities[fastest_id]}
            slowest = {"venture_id": slowest_id, "velocity": velocities[slowest_id]}

        # Get recent insights
        insights = await self.get_insights(limit=5)

        # Determine overall trend
        if avg_velocity > 0.5:
            acceleration_trend = "accelerating"
        elif avg_velocity < 0.3:
            acceleration_trend = "decelerating"
        else:
            acceleration_trend = "stable"

        return FlywheelReport(
            total_ventures=total_ventures,
            avg_velocity=avg_velocity,
            fastest_venture=fastest,
            slowest_venture=slowest,
            recent_insights=insights,
            acceleration_trend=acceleration_trend,
        )

    async def generate_insights(self) -> list[InsightResponse]:
        """Analyze patterns across ventures and generate insights."""
        async with get_global_session() as session:
            # Get all recent metrics grouped by venture
            result = await session.execute(
                select(FlywheelMetric)
                .order_by(FlywheelMetric.recorded_at.desc())
                .limit(100)
            )
            metrics = result.scalars().all()

        if not metrics:
            return []

        # Group by venture
        venture_metrics: dict[str, list[float]] = {}
        for m in metrics:
            venture_metrics.setdefault(m.venture_id, []).append(m.value)

        insights: list[InsightResponse] = []

        # Find outliers (ventures significantly above/below average)
        if len(venture_metrics) >= 2:
            averages = {vid: sum(vals) / len(vals) for vid, vals in venture_metrics.items()}
            overall_avg = sum(averages.values()) / len(averages)

            for vid, avg in averages.items():
                if avg > overall_avg * 1.5:
                    insight = CrossVentureInsight(
                        insight_type="acceleration_detected",
                        title=f"Venture {vid} is outperforming",
                        description=(
                            f"Venture {vid} has average metric {avg:.2f}, "
                            f"{(avg / overall_avg - 1) * 100:.0f}% above fleet average."
                        ),
                        evidence={"venture_id": vid, "avg": avg, "fleet_avg": overall_avg},
                        confidence=0.7,
                        affected_ventures=[vid],
                        generated_at=datetime.now(UTC),
                    )
                    async with get_global_session() as session:
                        session.add(insight)
                        await session.flush()
                        insights.append(_insight_to_response(insight))

                elif avg < overall_avg * 0.5:
                    insight = CrossVentureInsight(
                        insight_type="bottleneck_identified",
                        title=f"Venture {vid} is underperforming",
                        description=(
                            f"Venture {vid} has average metric {avg:.2f}, "
                            f"{(1 - avg / overall_avg) * 100:.0f}% below fleet average."
                        ),
                        evidence={"venture_id": vid, "avg": avg, "fleet_avg": overall_avg},
                        confidence=0.6,
                        affected_ventures=[vid],
                        generated_at=datetime.now(UTC),
                    )
                    async with get_global_session() as session:
                        session.add(insight)
                        await session.flush()
                        insights.append(_insight_to_response(insight))

        if insights:
            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="flywheel.insight.generated",
                source_module="meta_learning",
                payload={"count": len(insights)},
            )

        logger.info("insights_generated", count=len(insights))
        return insights

    async def get_insights(self, limit: int = 20) -> list[InsightResponse]:
        """Get recent cross-venture insights."""
        async with get_global_session() as session:
            result = await session.execute(
                select(CrossVentureInsight)
                .order_by(CrossVentureInsight.generated_at.desc())
                .limit(limit)
            )
            insights = result.scalars().all()
            return [_insight_to_response(i) for i in insights]

    async def compare_ventures(self, venture_ids: list[str]) -> dict:
        """Side-by-side metric comparison of specified ventures."""
        comparison: dict[str, dict] = {}

        for vid in venture_ids:
            velocity = await self.get_velocity(vid)
            comparison[vid] = {
                "velocity_score": velocity.velocity_score,
                "trend": velocity.trend,
                "metrics": velocity.metrics,
            }

        return comparison
