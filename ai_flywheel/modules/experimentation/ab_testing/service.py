"""A/B Test & Optimization Engine service.

The ABTestEngine manages experiment lifecycle, variant assignment,
observation recording, and statistical significance testing.

Statistical methods:
- Conversion metrics: z-test (normal approximation to binomial)
- Continuous metrics: Welch's t-test
- All implemented in pure Python (no scipy dependency)
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import Experiment, ExperimentObservation
from .schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResults,
    RecordObservationRequest,
    VariantStats,
)

logger = structlog.get_logger()


# ─── Pure Python Statistical Helpers ─────────────────────────────────────────


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function using erfc."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _z_test_conversion(
    successes1: int, n1: int, successes2: int, n2: int
) -> float | None:
    """Two-proportion z-test for conversion metrics.

    Returns p-value or None if test cannot be performed.
    """
    if n1 == 0 or n2 == 0:
        return None

    p1 = successes1 / n1
    p2 = successes2 / n2

    # Pooled proportion
    p_pool = (successes1 + successes2) / (n1 + n2)

    # Avoid division by zero when p_pool is 0 or 1
    if p_pool == 0.0 or p_pool == 1.0:
        return None

    denominator = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if denominator == 0:
        return None

    z_score = (p1 - p2) / denominator
    p_value = 2 * (1 - _norm_cdf(abs(z_score)))
    return p_value


def _welch_t_test(
    mean1: float,
    var1: float,
    n1: int,
    mean2: float,
    var2: float,
    n2: int,
) -> float | None:
    """Welch's t-test for continuous metrics.

    Returns approximate p-value or None if test cannot be performed.
    Uses normal approximation for large samples.
    """
    if n1 < 2 or n2 < 2:
        return None

    se1 = var1 / n1
    se2 = var2 / n2
    denominator_sq = se1 + se2

    if denominator_sq == 0:
        return None

    t_stat = (mean1 - mean2) / math.sqrt(denominator_sq)

    # For large samples, t-distribution approximates normal
    # Use normal CDF as approximation (valid for df > 30)
    p_value = 2 * (1 - _norm_cdf(abs(t_stat)))
    return p_value


def _compute_variant_stats(
    name: str, values: list[float], metric_type: str, confidence_level: float
) -> VariantStats:
    """Compute statistics for a single variant's observations."""
    n = len(values)
    if n == 0:
        return VariantStats(
            name=name,
            observations=0,
            mean=0.0,
            std_dev=0.0,
            conversion_rate=None,
            confidence_interval=(0.0, 0.0),
        )

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n if n > 1 else 0.0
    std_dev = math.sqrt(variance)

    # Conversion rate (for binary metrics: value is 0 or 1)
    conversion_rate: float | None = None
    if metric_type == "conversion":
        conversion_rate = mean  # mean of 0/1 values = conversion rate

    # Confidence interval using normal approximation
    z_multiplier = _z_for_confidence(confidence_level)
    se = std_dev / math.sqrt(n) if n > 0 else 0.0
    ci_lower = mean - z_multiplier * se
    ci_upper = mean + z_multiplier * se

    return VariantStats(
        name=name,
        observations=n,
        mean=mean,
        std_dev=std_dev,
        conversion_rate=conversion_rate,
        confidence_interval=(ci_lower, ci_upper),
    )


def _z_for_confidence(confidence: float) -> float:
    """Get z-score for a given confidence level (two-tailed)."""
    # Common values to avoid computation
    z_table = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    if confidence in z_table:
        return z_table[confidence]

    # Approximate inverse normal using rational approximation
    alpha = 1 - confidence
    p = 1 - alpha / 2
    # Abramowitz & Stegun approximation for inverse normal
    t = math.sqrt(-2 * math.log(1 - p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    return t - (c0 + c1 * t + c2 * t**2) / (1 + d1 * t + d2 * t**2 + d3 * t**3)


# ─── Service Class ────────────────────────────────────────────────────────────


class ABTestEngine:
    """Manages A/B test experiments with statistical significance testing.

    Usage:
        engine = ABTestEngine()
        experiment = await engine.create_experiment(venture_id, data)
        await engine.start_experiment(venture_id, experiment.id)
        variant = await engine.assign_variant(venture_id, experiment.id, "user_123")
        await engine.record_observation(venture_id, observation)
        results = await engine.get_results(venture_id, experiment.id)
    """

    def __init__(self) -> None:
        self._event_bus = get_event_bus()
        self._tracer = get_tracer()

    async def create_experiment(
        self, venture_id: str, data: ExperimentCreate
    ) -> ExperimentResponse:
        """Create a new experiment in draft status."""
        # Compute even traffic split across variants
        num_variants = len(data.variants)
        traffic_split: dict[str, float] = {}
        if num_variants > 0:
            base_pct = 100.0 / num_variants
            for variant in data.variants:
                traffic_split[variant["name"]] = round(base_pct, 2)

        async with get_session(venture_id) as session:
            experiment = Experiment(
                venture_id=venture_id,
                name=data.name,
                hypothesis=data.hypothesis,
                status="draft",
                experiment_type=data.experiment_type,
                variants=data.variants,
                metric_name=data.metric_name,
                metric_type=data.metric_type,
                traffic_split=traffic_split,
                sample_size_target=data.sample_size_target,
                current_sample_size=0,
                confidence_level=data.confidence_level,
            )
            session.add(experiment)
            await session.flush()

            response = ExperimentResponse.model_validate(experiment)

        await self._event_bus.publish(
            event_type="experiment.created",
            source_module="ab_testing",
            payload={
                "experiment_id": response.id,
                "name": data.name,
                "experiment_type": data.experiment_type,
                "variants": [v["name"] for v in data.variants],
            },
            venture_id=venture_id,
        )

        logger.info(
            "experiment_created",
            venture_id=venture_id,
            experiment_id=response.id,
            name=data.name,
            experiment_type=data.experiment_type,
        )

        return response

    async def start_experiment(
        self, venture_id: str, experiment_id: str
    ) -> ExperimentResponse:
        """Start an experiment (transition from draft/paused to running)."""
        async with get_session(venture_id) as session:
            stmt = select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            experiment = result.scalar_one()

            if experiment.status not in ("draft", "paused"):
                raise ValueError(
                    f"Cannot start experiment in '{experiment.status}' status. "
                    f"Must be 'draft' or 'paused'."
                )

            experiment.status = "running"
            if experiment.started_at is None:
                experiment.started_at = datetime.now(UTC)

            await session.flush()
            response = ExperimentResponse.model_validate(experiment)

        await self._event_bus.publish(
            event_type="experiment.started",
            source_module="ab_testing",
            payload={
                "experiment_id": experiment_id,
                "name": response.name,
            },
            venture_id=venture_id,
        )

        logger.info(
            "experiment_started",
            venture_id=venture_id,
            experiment_id=experiment_id,
        )

        return response

    async def pause_experiment(
        self, venture_id: str, experiment_id: str
    ) -> ExperimentResponse:
        """Pause a running experiment."""
        async with get_session(venture_id) as session:
            stmt = select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            experiment = result.scalar_one()

            if experiment.status != "running":
                raise ValueError(
                    f"Cannot pause experiment in '{experiment.status}' status. "
                    f"Must be 'running'."
                )

            experiment.status = "paused"
            await session.flush()
            response = ExperimentResponse.model_validate(experiment)

        logger.info(
            "experiment_paused",
            venture_id=venture_id,
            experiment_id=experiment_id,
        )

        return response

    async def record_observation(
        self, venture_id: str, request: RecordObservationRequest
    ) -> None:
        """Record an observation for an experiment variant."""
        now = datetime.now(UTC)

        async with get_session(venture_id) as session:
            # Verify experiment exists and is running
            exp_stmt = select(Experiment).where(
                Experiment.id == request.experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            exp_result = await session.execute(exp_stmt)
            experiment = exp_result.scalar_one()

            if experiment.status != "running":
                raise ValueError(
                    f"Cannot record observation: experiment is '{experiment.status}', "
                    f"not 'running'."
                )

            # Validate variant name exists
            variant_names = [v["name"] for v in experiment.variants]
            if request.variant_name not in variant_names:
                raise ValueError(
                    f"Unknown variant '{request.variant_name}'. "
                    f"Valid variants: {variant_names}"
                )

            observation = ExperimentObservation(
                venture_id=venture_id,
                experiment_id=request.experiment_id,
                variant_name=request.variant_name,
                value=request.value,
                user_id=request.user_id,
                context=request.context,
                observed_at=now,
            )
            session.add(observation)

            # Increment sample size
            experiment.current_sample_size = experiment.current_sample_size + 1
            await session.flush()

        await self._event_bus.publish(
            event_type="experiment.observation.recorded",
            source_module="ab_testing",
            payload={
                "experiment_id": request.experiment_id,
                "variant_name": request.variant_name,
                "value": request.value,
                "user_id": request.user_id,
            },
            venture_id=venture_id,
        )

        logger.debug(
            "observation_recorded",
            venture_id=venture_id,
            experiment_id=request.experiment_id,
            variant_name=request.variant_name,
        )

    async def get_results(
        self, venture_id: str, experiment_id: str
    ) -> ExperimentResults:
        """Compute statistical results for an experiment."""
        async with get_session(venture_id) as session:
            # Load experiment
            exp_stmt = select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            exp_result = await session.execute(exp_stmt)
            experiment = exp_result.scalar_one()

            # Load all observations grouped by variant
            obs_stmt = select(ExperimentObservation).where(
                ExperimentObservation.experiment_id == experiment_id,
                ExperimentObservation.venture_id == venture_id,
                ExperimentObservation.deleted_at.is_(None),
            )
            obs_result = await session.execute(obs_stmt)
            observations = obs_result.scalars().all()

        # Group observations by variant
        variant_data: dict[str, list[float]] = {}
        for variant in experiment.variants:
            variant_data[variant["name"]] = []
        for obs in observations:
            if obs.variant_name in variant_data:
                variant_data[obs.variant_name].append(obs.value)

        # Compute stats per variant
        variant_stats: list[VariantStats] = []
        for name, values in variant_data.items():
            stats = _compute_variant_stats(
                name, values, experiment.metric_type, experiment.confidence_level
            )
            variant_stats.append(stats)

        # Determine significance and winner
        p_value: float | None = None
        is_significant = False
        winner: str | None = None
        recommendation = "Insufficient data to draw conclusions."

        # Find control variant
        control_name: str | None = None
        for variant in experiment.variants:
            if variant.get("is_control", False):
                control_name = variant["name"]
                break

        # If no explicit control, use the first variant
        if control_name is None and experiment.variants:
            control_name = experiment.variants[0]["name"]

        # Statistical testing (compare each variant against control)
        if control_name and len(variant_data) >= 2:
            control_values = variant_data.get(control_name, [])
            best_variant: str | None = None
            best_improvement = 0.0

            for name, values in variant_data.items():
                if name == control_name:
                    continue

                if experiment.metric_type == "conversion":
                    # Z-test for proportions
                    n1 = len(control_values)
                    n2 = len(values)
                    successes1 = sum(1 for v in control_values if v > 0)
                    successes2 = sum(1 for v in values if v > 0)
                    test_p_value = _z_test_conversion(successes1, n1, successes2, n2)
                else:
                    # Welch's t-test for continuous/count metrics
                    n1 = len(control_values)
                    n2 = len(values)
                    if n1 >= 2 and n2 >= 2:
                        mean1 = sum(control_values) / n1
                        mean2 = sum(values) / n2
                        var1 = sum((x - mean1) ** 2 for x in control_values) / (n1 - 1)
                        var2 = sum((x - mean2) ** 2 for x in values) / (n2 - 1)
                        test_p_value = _welch_t_test(mean1, var1, n1, mean2, var2, n2)
                    else:
                        test_p_value = None

                if test_p_value is not None:
                    # Track the lowest p-value (most significant result)
                    if p_value is None or test_p_value < p_value:
                        p_value = test_p_value

                    # Check if this variant beats control
                    if test_p_value < (1 - experiment.confidence_level):
                        control_mean = (
                            sum(control_values) / len(control_values)
                            if control_values
                            else 0
                        )
                        variant_mean = sum(values) / len(values) if values else 0
                        improvement = variant_mean - control_mean

                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_variant = name

            if p_value is not None and p_value < (1 - experiment.confidence_level):
                is_significant = True
                winner = best_variant
                recommendation = (
                    f"Variant '{winner}' shows statistically significant improvement "
                    f"over control (p={p_value:.4f}, confidence={experiment.confidence_level})."
                )
            elif p_value is not None:
                recommendation = (
                    f"No statistically significant difference detected "
                    f"(p={p_value:.4f}). Consider collecting more data."
                )

        return ExperimentResults(
            experiment_id=experiment_id,
            status=experiment.status,
            variants=variant_stats,
            winner=winner,
            is_significant=is_significant,
            p_value=p_value,
            confidence=experiment.confidence_level,
            recommendation=recommendation,
        )

    async def assign_variant(
        self, venture_id: str, experiment_id: str, user_id: str
    ) -> str:
        """Assign a user to a variant using consistent hashing.

        Ensures the same user always gets the same variant for a given experiment.
        """
        async with get_session(venture_id) as session:
            stmt = select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            experiment = result.scalar_one()

        if experiment.status != "running":
            raise ValueError(
                f"Cannot assign variant: experiment is '{experiment.status}', "
                f"not 'running'."
            )

        # Consistent hash assignment
        hash_value = hash(f"{experiment_id}:{user_id}") % 100
        traffic_split = experiment.traffic_split
        variant_names = list(traffic_split.keys())

        # Walk the cumulative distribution to find the assigned variant
        cumulative = 0.0
        for variant_name in variant_names:
            cumulative += traffic_split[variant_name]
            if hash_value < cumulative:
                return variant_name

        # Fallback to last variant (rounding edge case)
        return variant_names[-1] if variant_names else ""

    async def get_experiment(
        self, venture_id: str, experiment_id: str
    ) -> ExperimentResponse:
        """Get a single experiment by ID."""
        async with get_session(venture_id) as session:
            stmt = select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            experiment = result.scalar_one()
            return ExperimentResponse.model_validate(experiment)

    async def list_experiments(
        self, venture_id: str, status: str | None = None
    ) -> list[ExperimentResponse]:
        """List all experiments for a venture, optionally filtered by status."""
        async with get_session(venture_id) as session:
            stmt = select(Experiment).where(
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            if status:
                stmt = stmt.where(Experiment.status == status)
            stmt = stmt.order_by(Experiment.created_at.desc())

            result = await session.execute(stmt)
            experiments = result.scalars().all()

            return [
                ExperimentResponse.model_validate(exp) for exp in experiments
            ]

    async def conclude_experiment(
        self, venture_id: str, experiment_id: str
    ) -> ExperimentResults:
        """Conclude an experiment: compute final results and mark completed."""
        results = await self.get_results(venture_id, experiment_id)

        async with get_session(venture_id) as session:
            stmt = select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.venture_id == venture_id,
                Experiment.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            experiment = result.scalar_one()

            experiment.status = "completed"
            experiment.completed_at = datetime.now(UTC)
            if results.winner:
                experiment.winner = results.winner

            await session.flush()

        await self._event_bus.publish(
            event_type="experiment.completed",
            source_module="ab_testing",
            payload={
                "experiment_id": experiment_id,
                "winner": results.winner,
                "is_significant": results.is_significant,
                "p_value": results.p_value,
            },
            venture_id=venture_id,
        )

        logger.info(
            "experiment_concluded",
            venture_id=venture_id,
            experiment_id=experiment_id,
            winner=results.winner,
            is_significant=results.is_significant,
        )

        return results
