"""Cost Optimizer service — budget enforcement, spend tracking, and alerting.

The CostOptimizer is the primary interface for:
- Recording costs from LLM operations and other billable actions
- Managing budgets per venture per period
- Generating cost reports and trend analysis
- Checking budgets and creating alerts when thresholds are breached
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.models.costs import CostRecord
from ai_flywheel.core.traces import get_tracer

from .models import Budget, CostAlert
from .schemas import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CostAlertResponse,
    CostReport,
    CostTrend,
)

logger = structlog.get_logger()


def _get_period_start(period_type: str, now: datetime | None = None) -> datetime:
    """Calculate the start of the current period."""
    now = now or datetime.now(UTC)
    if period_type == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == "weekly":
        # Start of the week (Monday)
        days_since_monday = now.weekday()
        start = now - timedelta(days=days_since_monday)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Invalid period_type: {period_type}")


def _get_period_label(period_type: str, now: datetime | None = None) -> str:
    """Generate a human-readable label for the current period."""
    now = now or datetime.now(UTC)
    if period_type == "daily":
        return now.strftime("%Y-%m-%d")
    elif period_type == "weekly":
        start = _get_period_start("weekly", now)
        end = start + timedelta(days=6)
        return f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
    elif period_type == "monthly":
        return now.strftime("%Y-%m")
    else:
        return now.isoformat()


def _get_previous_period_starts(
    period_type: str, num_periods: int, now: datetime | None = None
) -> list[tuple[datetime, datetime]]:
    """Get start/end pairs for previous periods (most recent first)."""
    now = now or datetime.now(UTC)
    periods: list[tuple[datetime, datetime]] = []

    for i in range(num_periods):
        if period_type == "daily":
            period_end = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            period_start = period_end - timedelta(days=1)
            if i == 0:
                period_end = now
                period_start = _get_period_start("daily", now)
        elif period_type == "weekly":
            current_start = _get_period_start("weekly", now)
            period_start = current_start - timedelta(weeks=i)
            period_end = period_start + timedelta(weeks=1)
            if i == 0:
                period_end = now
        elif period_type == "monthly":
            # Step back i months
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            period_start = datetime(year, month, 1, tzinfo=UTC)
            # End is start of next month
            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year += 1
            period_end = datetime(next_year, next_month, 1, tzinfo=UTC)
            if i == 0:
                period_end = now
        else:
            raise ValueError(f"Invalid period_type: {period_type}")

        periods.append((period_start, period_end))

    return periods


class CostOptimizer:
    """Tracks spending, enforces budgets, and generates cost insights.

    Usage:
        optimizer = CostOptimizer()
        await optimizer.record_cost(venture_id, "agent_factory", "llm_call", 0.03, ...)
        report = await optimizer.get_report(venture_id, "monthly")
    """

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._tracer = get_tracer()

    async def record_cost(
        self,
        venture_id: str,
        module_name: str,
        operation: str,
        amount_usd: float,
        provider: str,
        model_name: str | None = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a cost entry and check budgets.

        This method is called on every billable operation, so it must be fast.
        Budget checking is done inline but alert creation is lightweight.
        """
        now = datetime.now(UTC)

        async with get_session(venture_id) as session:
            record = CostRecord(
                venture_id=venture_id,
                module_name=module_name,
                operation=operation,
                amount_usd=amount_usd,
                provider=provider,
                model_name=model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                recorded_at=now,
                extra=metadata,
            )
            session.add(record)

        # Emit event (non-blocking to keep record_cost fast)
        await self._event_bus.publish(
            event_type="cost.recorded",
            source_module="cost_optimizer",
            payload={
                "module_name": module_name,
                "operation": operation,
                "amount_usd": amount_usd,
                "provider": provider,
                "model_name": model_name,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
            },
            venture_id=venture_id,
        )

        logger.debug(
            "cost_recorded",
            venture_id=venture_id,
            module_name=module_name,
            operation=operation,
            amount_usd=amount_usd,
            provider=provider,
        )

        # Check budgets after recording
        await self.check_budget(venture_id)

    async def set_budget(self, data: BudgetCreate) -> BudgetResponse:
        """Create or replace a budget for a venture + period_type."""
        async with get_session(data.venture_id) as session:
            # Deactivate any existing budget for this venture + period_type
            existing_stmt = select(Budget).where(
                Budget.venture_id == data.venture_id,
                Budget.period_type == data.period_type,
                Budget.is_active.is_(True),
                Budget.deleted_at.is_(None),
            )
            result = await session.execute(existing_stmt)
            existing = result.scalars().all()
            for old_budget in existing:
                old_budget.is_active = False

            # Create new budget
            budget = Budget(
                venture_id=data.venture_id,
                period_type=data.period_type,
                limit_usd=data.limit_usd,
                alert_threshold_pct=data.alert_threshold_pct,
                is_active=True,
            )
            session.add(budget)
            await session.flush()

            # Get current spend for response
            current_spend = await self._get_current_spend(
                session, data.venture_id, data.period_type
            )

            response = BudgetResponse(
                id=budget.id,
                venture_id=budget.venture_id,
                period_type=budget.period_type,
                limit_usd=budget.limit_usd,
                alert_threshold_pct=budget.alert_threshold_pct,
                current_spend_usd=current_spend,
                is_active=budget.is_active,
                created_at=budget.created_at,
            )

        logger.info(
            "budget_set",
            venture_id=data.venture_id,
            period_type=data.period_type,
            limit_usd=data.limit_usd,
        )
        return response

    async def get_budget(
        self, venture_id: str, period_type: str
    ) -> BudgetResponse | None:
        """Get the active budget for a venture + period_type."""
        async with get_session(venture_id) as session:
            stmt = select(Budget).where(
                Budget.venture_id == venture_id,
                Budget.period_type == period_type,
                Budget.is_active.is_(True),
                Budget.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            budget = result.scalar_one_or_none()

            if not budget:
                return None

            current_spend = await self._get_current_spend(
                session, venture_id, period_type
            )

            return BudgetResponse(
                id=budget.id,
                venture_id=budget.venture_id,
                period_type=budget.period_type,
                limit_usd=budget.limit_usd,
                alert_threshold_pct=budget.alert_threshold_pct,
                current_spend_usd=current_spend,
                is_active=budget.is_active,
                created_at=budget.created_at,
            )

    async def update_budget(
        self, venture_id: str, budget_id: str, data: BudgetUpdate
    ) -> BudgetResponse:
        """Update an existing budget."""
        async with get_session(venture_id) as session:
            stmt = select(Budget).where(
                Budget.id == budget_id,
                Budget.venture_id == venture_id,
                Budget.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            budget = result.scalar_one()

            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(budget, field, value)

            await session.flush()

            current_spend = await self._get_current_spend(
                session, venture_id, budget.period_type
            )

            response = BudgetResponse(
                id=budget.id,
                venture_id=budget.venture_id,
                period_type=budget.period_type,
                limit_usd=budget.limit_usd,
                alert_threshold_pct=budget.alert_threshold_pct,
                current_spend_usd=current_spend,
                is_active=budget.is_active,
                created_at=budget.created_at,
            )

        logger.info(
            "budget_updated",
            venture_id=venture_id,
            budget_id=budget_id,
            updates=list(update_data.keys()),
        )
        return response

    async def get_report(
        self, venture_id: str, period_type: str = "monthly"
    ) -> CostReport:
        """Generate an aggregated cost report for the current period."""
        period_start = _get_period_start(period_type)
        period_label = _get_period_label(period_type)

        async with get_session(venture_id) as session:
            base_filter = [
                CostRecord.venture_id == venture_id,
                CostRecord.recorded_at >= period_start,
                CostRecord.deleted_at.is_(None),
            ]

            # Total spend
            total_stmt = select(func.coalesce(func.sum(CostRecord.amount_usd), 0.0)).where(
                *base_filter
            )
            total_result = await session.execute(total_stmt)
            total_usd = float(total_result.scalar_one())

            # By module
            by_module_stmt = (
                select(
                    CostRecord.module_name,
                    func.sum(CostRecord.amount_usd).label("total"),
                )
                .where(*base_filter)
                .group_by(CostRecord.module_name)
            )
            by_module_result = await session.execute(by_module_stmt)
            by_module = {row[0]: float(row[1]) for row in by_module_result.all()}

            # By provider
            by_provider_stmt = (
                select(
                    CostRecord.provider,
                    func.sum(CostRecord.amount_usd).label("total"),
                )
                .where(*base_filter)
                .group_by(CostRecord.provider)
            )
            by_provider_result = await session.execute(by_provider_stmt)
            by_provider = {row[0]: float(row[1]) for row in by_provider_result.all()}

            # By model
            by_model_stmt = (
                select(
                    CostRecord.model_name,
                    func.sum(CostRecord.amount_usd).label("total"),
                )
                .where(*base_filter, CostRecord.model_name.isnot(None))
                .group_by(CostRecord.model_name)
            )
            by_model_result = await session.execute(by_model_stmt)
            by_model = {row[0]: float(row[1]) for row in by_model_result.all()}

            # Top operations
            top_ops_stmt = (
                select(
                    CostRecord.operation,
                    CostRecord.module_name,
                    func.sum(CostRecord.amount_usd).label("total"),
                    func.count().label("count"),
                )
                .where(*base_filter)
                .group_by(CostRecord.operation, CostRecord.module_name)
                .order_by(func.sum(CostRecord.amount_usd).desc())
                .limit(10)
            )
            top_ops_result = await session.execute(top_ops_stmt)
            top_operations = [
                {
                    "operation": row[0],
                    "module": row[1],
                    "total_usd": float(row[2]),
                    "count": int(row[3]),
                }
                for row in top_ops_result.all()
            ]

            # Budget utilization
            budget_utilization: float | None = None
            budget_stmt = select(Budget).where(
                Budget.venture_id == venture_id,
                Budget.period_type == period_type,
                Budget.is_active.is_(True),
                Budget.deleted_at.is_(None),
            )
            budget_result = await session.execute(budget_stmt)
            budget = budget_result.scalar_one_or_none()
            if budget and budget.limit_usd > 0:
                budget_utilization = (total_usd / budget.limit_usd) * 100.0

        return CostReport(
            venture_id=venture_id,
            period=period_label,
            total_usd=total_usd,
            by_module=by_module,
            by_provider=by_provider,
            by_model=by_model,
            top_operations=top_operations,
            budget_utilization_pct=budget_utilization,
        )

    async def get_trend(
        self, venture_id: str, periods: int = 6
    ) -> CostTrend:
        """Analyze spending trend over multiple periods."""
        # Default to monthly periods for trend analysis
        period_type = "monthly"
        period_ranges = _get_previous_period_starts(period_type, periods)

        period_data: list[dict[str, Any]] = []

        async with get_session(venture_id) as session:
            for period_start, period_end in period_ranges:
                total_stmt = select(
                    func.coalesce(func.sum(CostRecord.amount_usd), 0.0)
                ).where(
                    CostRecord.venture_id == venture_id,
                    CostRecord.recorded_at >= period_start,
                    CostRecord.recorded_at < period_end,
                    CostRecord.deleted_at.is_(None),
                )
                result = await session.execute(total_stmt)
                total = float(result.scalar_one())

                period_data.append({
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "label": _get_period_label(period_type, period_start),
                    "total_usd": total,
                })

        # Determine trend direction from the data
        amounts = [p["total_usd"] for p in period_data]
        trend_direction = _calculate_trend_direction(amounts)

        # Project monthly spend based on recent data
        projected_monthly = _project_monthly_spend(amounts, period_type)

        return CostTrend(
            venture_id=venture_id,
            periods=period_data,
            trend_direction=trend_direction,
            projected_monthly=projected_monthly,
        )

    async def check_budget(self, venture_id: str) -> list[CostAlertResponse]:
        """Check all active budgets and create alerts if thresholds are breached."""
        alerts: list[CostAlertResponse] = []

        async with get_session(venture_id) as session:
            # Get all active budgets
            budget_stmt = select(Budget).where(
                Budget.venture_id == venture_id,
                Budget.is_active.is_(True),
                Budget.deleted_at.is_(None),
            )
            budget_result = await session.execute(budget_stmt)
            budgets = budget_result.scalars().all()

            for budget in budgets:
                current_spend = await self._get_current_spend(
                    session, venture_id, budget.period_type
                )

                if budget.limit_usd <= 0:
                    continue

                utilization = current_spend / budget.limit_usd
                period_label = _get_period_label(budget.period_type)

                if utilization >= 1.0:
                    # Budget exceeded
                    alert = await self._create_alert(
                        session=session,
                        venture_id=venture_id,
                        alert_type="exceeded",
                        budget_id=budget.id,
                        message=(
                            f"Budget exceeded for {budget.period_type} period "
                            f"({period_label}): ${current_spend:.2f} / "
                            f"${budget.limit_usd:.2f} ({utilization * 100:.1f}%)"
                        ),
                        current_spend_usd=current_spend,
                        limit_usd=budget.limit_usd,
                        period=period_label,
                    )
                    if alert:
                        alerts.append(alert)
                        await self._event_bus.publish(
                            event_type="cost.alert.exceeded",
                            source_module="cost_optimizer",
                            payload={
                                "budget_id": budget.id,
                                "period_type": budget.period_type,
                                "current_spend_usd": current_spend,
                                "limit_usd": budget.limit_usd,
                                "utilization_pct": utilization * 100,
                            },
                            venture_id=venture_id,
                        )

                elif utilization >= budget.alert_threshold_pct:
                    # Approaching threshold
                    alert = await self._create_alert(
                        session=session,
                        venture_id=venture_id,
                        alert_type="threshold",
                        budget_id=budget.id,
                        message=(
                            f"Approaching budget limit for {budget.period_type} "
                            f"period ({period_label}): ${current_spend:.2f} / "
                            f"${budget.limit_usd:.2f} ({utilization * 100:.1f}%)"
                        ),
                        current_spend_usd=current_spend,
                        limit_usd=budget.limit_usd,
                        period=period_label,
                    )
                    if alert:
                        alerts.append(alert)
                        await self._event_bus.publish(
                            event_type="cost.alert.threshold",
                            source_module="cost_optimizer",
                            payload={
                                "budget_id": budget.id,
                                "period_type": budget.period_type,
                                "current_spend_usd": current_spend,
                                "limit_usd": budget.limit_usd,
                                "utilization_pct": utilization * 100,
                                "threshold_pct": budget.alert_threshold_pct * 100,
                            },
                            venture_id=venture_id,
                        )

        return alerts

    async def get_alerts(
        self, venture_id: str, unacknowledged_only: bool = True
    ) -> list[CostAlertResponse]:
        """Get alerts for a venture."""
        async with get_session(venture_id) as session:
            stmt = select(CostAlert).where(
                CostAlert.venture_id == venture_id,
                CostAlert.deleted_at.is_(None),
            )
            if unacknowledged_only:
                stmt = stmt.where(CostAlert.acknowledged.is_(False))

            stmt = stmt.order_by(CostAlert.created_at.desc())
            result = await session.execute(stmt)
            alert_records = result.scalars().all()

            return [
                CostAlertResponse.model_validate(alert) for alert in alert_records
            ]

    async def acknowledge_alert(self, venture_id: str, alert_id: str) -> None:
        """Acknowledge a cost alert."""
        async with get_session(venture_id) as session:
            stmt = select(CostAlert).where(
                CostAlert.id == alert_id,
                CostAlert.venture_id == venture_id,
                CostAlert.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            alert = result.scalar_one()

            alert.acknowledged = True
            alert.acknowledged_at = datetime.now(UTC)

        logger.info(
            "alert_acknowledged",
            venture_id=venture_id,
            alert_id=alert_id,
        )

    # ─── Private helpers ──────────────────────────────────────────────

    async def _get_current_spend(
        self,
        session: Any,
        venture_id: str,
        period_type: str,
    ) -> float:
        """Get total spend for the current period within an existing session."""
        period_start = _get_period_start(period_type)

        stmt = select(func.coalesce(func.sum(CostRecord.amount_usd), 0.0)).where(
            CostRecord.venture_id == venture_id,
            CostRecord.recorded_at >= period_start,
            CostRecord.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        return float(result.scalar_one())

    async def _create_alert(
        self,
        session: Any,
        venture_id: str,
        alert_type: str,
        budget_id: str,
        message: str,
        current_spend_usd: float,
        limit_usd: float,
        period: str,
    ) -> CostAlertResponse | None:
        """Create an alert if one doesn't already exist for this budget+type+period."""
        # Avoid duplicate alerts for the same budget/type/period
        existing_stmt = select(CostAlert).where(
            CostAlert.venture_id == venture_id,
            CostAlert.budget_id == budget_id,
            CostAlert.alert_type == alert_type,
            CostAlert.period == period,
            CostAlert.acknowledged.is_(False),
            CostAlert.deleted_at.is_(None),
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            return None  # Alert already exists

        alert = CostAlert(
            venture_id=venture_id,
            alert_type=alert_type,
            budget_id=budget_id,
            message=message,
            current_spend_usd=current_spend_usd,
            limit_usd=limit_usd,
            period=period,
            acknowledged=False,
        )
        session.add(alert)
        await session.flush()

        logger.warning(
            "cost_alert_created",
            venture_id=venture_id,
            alert_type=alert_type,
            current_spend_usd=current_spend_usd,
            limit_usd=limit_usd,
            period=period,
        )

        return CostAlertResponse.model_validate(alert)


def _calculate_trend_direction(amounts: list[float]) -> str:
    """Determine trend direction from a list of amounts (most recent first)."""
    if len(amounts) < 2:
        return "stable"

    # Compare recent half to older half
    mid = len(amounts) // 2
    recent_avg = sum(amounts[:mid]) / mid if mid > 0 else 0
    older_avg = sum(amounts[mid:]) / (len(amounts) - mid) if (len(amounts) - mid) > 0 else 0

    if older_avg == 0:
        return "increasing" if recent_avg > 0 else "stable"

    change_pct = (recent_avg - older_avg) / older_avg

    if change_pct > 0.1:
        return "increasing"
    elif change_pct < -0.1:
        return "decreasing"
    else:
        return "stable"


def _project_monthly_spend(amounts: list[float], period_type: str) -> float:
    """Project monthly spend based on recent trend data."""
    if not amounts:
        return 0.0

    # Use the average of the most recent 3 periods (or fewer if not available)
    recent = amounts[: min(3, len(amounts))]
    avg_per_period = sum(recent) / len(recent)

    if period_type == "daily":
        return avg_per_period * 30
    elif period_type == "weekly":
        return avg_per_period * 4.33
    elif period_type == "monthly":
        return avg_per_period
    else:
        return avg_per_period
