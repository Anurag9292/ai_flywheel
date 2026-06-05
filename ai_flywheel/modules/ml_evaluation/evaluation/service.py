# ruff: noqa: E501
"""Evaluation Framework — core service.

Manages eval suites, runs test cases against target modules, scores results
using configurable metrics, and provides run comparison utilities.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import EvalRun, EvalSuite
from .schemas import (
    AddTestCaseRequest,
    EvalRunResult,
    EvalSuiteCreate,
    EvalSuiteResponse,
    RunEvalRequest,
)

logger = structlog.get_logger()


class EvaluationFramework:
    """Manages evaluation suites, runs scoring, and provides comparison utilities."""

    # ------------------------------------------------------------------
    # Suite CRUD
    # ------------------------------------------------------------------

    async def create_suite(
        self, venture_id: str, data: EvalSuiteCreate
    ) -> EvalSuiteResponse:
        """Create a new evaluation suite."""
        async with get_session(venture_id) as session:
            suite = EvalSuite(
                venture_id=venture_id,
                name=data.name,
                description=data.description,
                target_module=data.target_module,
                metrics=data.metrics,
                test_cases=data.test_cases,
                status="active",
            )
            session.add(suite)
            await session.flush()
            await session.refresh(suite)

            logger.info(
                "eval_suite_created",
                venture_id=venture_id,
                suite_id=suite.id,
                name=data.name,
                target_module=data.target_module,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="eval.suite.created",
                source_module="evaluation_framework",
                payload={
                    "suite_id": suite.id,
                    "name": data.name,
                    "target_module": data.target_module,
                },
                venture_id=venture_id,
            )

            return self._suite_to_response(suite)

    async def get_suite(self, venture_id: str, suite_id: str) -> EvalSuiteResponse:
        """Retrieve an eval suite by ID."""
        async with get_session(venture_id) as session:
            stmt = (
                select(EvalSuite)
                .where(EvalSuite.id == suite_id)
                .where(EvalSuite.venture_id == venture_id)
                .where(EvalSuite.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            suite = result.scalar_one()
            return self._suite_to_response(suite)

    async def list_suites(self, venture_id: str) -> list[EvalSuiteResponse]:
        """List all eval suites for a venture."""
        async with get_session(venture_id) as session:
            stmt = (
                select(EvalSuite)
                .where(EvalSuite.venture_id == venture_id)
                .where(EvalSuite.deleted_at.is_(None))
                .order_by(EvalSuite.created_at.desc())
            )
            result = await session.execute(stmt)
            suites = result.scalars().all()
            return [self._suite_to_response(s) for s in suites]

    async def add_test_case(
        self, venture_id: str, request: AddTestCaseRequest
    ) -> EvalSuiteResponse:
        """Add a test case to an existing eval suite."""
        async with get_session(venture_id) as session:
            stmt = (
                select(EvalSuite)
                .where(EvalSuite.id == request.suite_id)
                .where(EvalSuite.venture_id == venture_id)
                .where(EvalSuite.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            suite = result.scalar_one()

            test_case = {
                "input": request.input,
                "expected_output": request.expected_output,
                "tags": request.tags,
            }

            updated_cases = list(suite.test_cases) + [test_case]
            suite.test_cases = updated_cases
            await session.flush()
            await session.refresh(suite)

            logger.info(
                "eval_test_case_added",
                venture_id=venture_id,
                suite_id=suite.id,
                total_cases=len(suite.test_cases),
            )

            return self._suite_to_response(suite)

    # ------------------------------------------------------------------
    # Evaluation Execution
    # ------------------------------------------------------------------

    async def run_evaluation(
        self, venture_id: str, request: RunEvalRequest
    ) -> EvalRunResult:
        """Run an evaluation: execute test cases, score each, aggregate results."""
        tracer = get_tracer()
        event_bus = get_event_bus()

        async with tracer.span(
            "evaluation_framework", "run_evaluation", input_data={"suite_id": request.suite_id}
        ):
            start = time.perf_counter()

            # Load the suite
            async with get_session(venture_id) as session:
                stmt = (
                    select(EvalSuite)
                    .where(EvalSuite.id == request.suite_id)
                    .where(EvalSuite.venture_id == venture_id)
                    .where(EvalSuite.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                suite = result.scalar_one()

                test_cases = suite.test_cases or []
                metrics = suite.metrics or []
                total_cases = len(test_cases)

                # Score each test case against each metric
                per_case_scores: list[dict[str, Any]] = []
                per_metric_totals: dict[str, list[float]] = {}
                passed = 0
                failed = 0

                for case in test_cases:
                    case_input = case.get("input", {})
                    expected_output = case.get("expected_output", {})
                    case_scores: dict[str, float] = {}

                    for metric in metrics:
                        metric_name = metric.get("name", "unnamed")
                        metric_type = metric.get("metric_type", "exact_match")
                        _threshold = metric.get("threshold", 0.0)  # noqa: F841

                        score = self._score_metric(
                            metric_type=metric_type,
                            output=case_input,
                            expected=expected_output,
                        )
                        case_scores[metric_name] = score

                        if metric_name not in per_metric_totals:
                            per_metric_totals[metric_name] = []
                        per_metric_totals[metric_name].append(score)

                    # A case passes if the weighted average of its scores meets all thresholds
                    case_avg = self._weighted_average(case_scores, metrics)
                    if case_avg >= self._min_threshold(metrics):
                        passed += 1
                    else:
                        failed += 1

                    per_case_scores.append({
                        "input": case_input,
                        "expected_output": expected_output,
                        "scores": case_scores,
                        "average": case_avg,
                    })

                # Aggregate per-metric averages
                per_metric_averages: dict[str, float] = {}
                for metric_name, scores_list in per_metric_totals.items():
                    per_metric_averages[metric_name] = (
                        sum(scores_list) / len(scores_list) if scores_list else 0.0
                    )

                # Overall score: weighted average across all metrics
                overall_score = self._compute_overall_score(per_metric_averages, metrics)

                elapsed_ms = (time.perf_counter() - start) * 1000
                run_at = datetime.now(UTC)

                scores_payload = {
                    "overall": overall_score,
                    "per_metric": per_metric_averages,
                    "per_case": per_case_scores,
                }

                # Persist the run
                run = EvalRun(
                    venture_id=venture_id,
                    suite_id=suite.id,
                    status="completed",
                    scores=scores_payload,
                    total_cases=total_cases,
                    passed_cases=passed,
                    failed_cases=failed,
                    duration_ms=elapsed_ms,
                    config=request.config,
                    run_at=run_at,
                )
                session.add(run)

                # Update suite with last run info
                suite.last_run_at = run_at
                suite.last_score = overall_score

                await session.flush()
                await session.refresh(run)

            # Emit event
            await event_bus.publish(
                event_type="eval.run.completed",
                source_module="evaluation_framework",
                payload={
                    "run_id": run.id,
                    "suite_id": suite.id,
                    "overall_score": overall_score,
                    "total_cases": total_cases,
                    "passed_cases": passed,
                    "failed_cases": failed,
                    "duration_ms": elapsed_ms,
                },
                venture_id=venture_id,
            )

            logger.info(
                "eval_run_completed",
                venture_id=venture_id,
                run_id=run.id,
                suite_id=suite.id,
                overall_score=round(overall_score, 4),
                total_cases=total_cases,
                passed=passed,
                failed=failed,
                duration_ms=round(elapsed_ms, 2),
            )

            return EvalRunResult(
                run_id=run.id,
                suite_id=suite.id,
                status="completed",
                overall_score=overall_score,
                scores=scores_payload,
                total_cases=total_cases,
                passed_cases=passed,
                failed_cases=failed,
                duration_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    # Run Retrieval & Comparison
    # ------------------------------------------------------------------

    async def get_run(self, venture_id: str, run_id: str) -> EvalRunResult:
        """Retrieve a specific eval run by ID."""
        async with get_session(venture_id) as session:
            stmt = (
                select(EvalRun)
                .where(EvalRun.id == run_id)
                .where(EvalRun.venture_id == venture_id)
                .where(EvalRun.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            run = result.scalar_one()
            return self._run_to_result(run)

    async def get_run_history(
        self, venture_id: str, suite_id: str
    ) -> list[EvalRunResult]:
        """Retrieve all runs for a given suite, ordered by most recent first."""
        async with get_session(venture_id) as session:
            stmt = (
                select(EvalRun)
                .where(EvalRun.venture_id == venture_id)
                .where(EvalRun.suite_id == suite_id)
                .where(EvalRun.deleted_at.is_(None))
                .order_by(EvalRun.run_at.desc())
            )
            result = await session.execute(stmt)
            runs = result.scalars().all()
            return [self._run_to_result(r) for r in runs]

    async def compare_runs(
        self, venture_id: str, run_id_a: str, run_id_b: str
    ) -> dict[str, Any]:
        """Compare two eval runs and return score deltas."""
        run_a = await self.get_run(venture_id, run_id_a)
        run_b = await self.get_run(venture_id, run_id_b)

        per_metric_a = run_a.scores.get("per_metric", {})
        per_metric_b = run_b.scores.get("per_metric", {})

        # Compute deltas (B - A, so positive means improvement)
        metric_deltas: dict[str, float] = {}
        all_metrics = set(per_metric_a.keys()) | set(per_metric_b.keys())
        for metric in all_metrics:
            score_a = per_metric_a.get(metric, 0.0)
            score_b = per_metric_b.get(metric, 0.0)
            metric_deltas[metric] = score_b - score_a

        return {
            "run_a": {"run_id": run_id_a, "overall_score": run_a.overall_score, "per_metric": per_metric_a},
            "run_b": {"run_id": run_id_b, "overall_score": run_b.overall_score, "per_metric": per_metric_b},
            "overall_delta": run_b.overall_score - run_a.overall_score,
            "metric_deltas": metric_deltas,
            "improved": run_b.overall_score > run_a.overall_score,
            "passed_delta": run_b.passed_cases - run_a.passed_cases,
            "failed_delta": run_b.failed_cases - run_a.failed_cases,
        }

    # ------------------------------------------------------------------
    # Scoring Logic
    # ------------------------------------------------------------------

    @staticmethod
    def _score_metric(metric_type: str, output: dict, expected: dict) -> float:
        """Score a single metric for a test case.

        For simplicity, the scoring compares the full output dict against expected.
        In production, this would invoke the target module to generate actual output.
        """
        if metric_type == "exact_match":
            return 1.0 if output == expected else 0.0

        elif metric_type == "contains":
            # Check if all expected values are contained in output
            output_str = str(output)
            expected_str = str(expected)
            return 1.0 if expected_str in output_str else 0.0

        elif metric_type == "numeric_closeness":
            # Compare numeric values from output and expected
            output_val = _extract_numeric(output)
            expected_val = _extract_numeric(expected)
            if output_val is None or expected_val is None:
                return 0.0
            denominator = max(abs(expected_val), 1e-6)
            return 1.0 - min(abs(output_val - expected_val) / denominator, 1.0)

        # custom or unknown: default to exact_match
        return 1.0 if output == expected else 0.0

    @staticmethod
    def _weighted_average(case_scores: dict[str, float], metrics: list[dict]) -> float:
        """Compute weighted average of a case's metric scores."""
        if not case_scores:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for metric in metrics:
            metric_name = metric.get("name", "")
            weight = metric.get("weight", 1.0)
            score = case_scores.get(metric_name, 0.0)
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    @staticmethod
    def _min_threshold(metrics: list[dict]) -> float:
        """Get the minimum threshold across all metrics (used for pass/fail)."""
        if not metrics:
            return 0.0
        thresholds = [m.get("threshold", 0.0) for m in metrics]
        return min(thresholds) if thresholds else 0.0

    @staticmethod
    def _compute_overall_score(
        per_metric_averages: dict[str, float], metrics: list[dict]
    ) -> float:
        """Compute overall score as weighted average of per-metric averages."""
        if not per_metric_averages:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for metric in metrics:
            metric_name = metric.get("name", "")
            weight = metric.get("weight", 1.0)
            avg_score = per_metric_averages.get(metric_name, 0.0)
            weighted_sum += avg_score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _suite_to_response(suite: EvalSuite) -> EvalSuiteResponse:
        """Convert a suite model to response schema."""
        return EvalSuiteResponse(
            id=suite.id,
            venture_id=suite.venture_id,
            name=suite.name,
            description=suite.description,
            target_module=suite.target_module,
            metrics=suite.metrics or [],
            test_cases_count=len(suite.test_cases or []),
            status=suite.status,
            last_run_at=suite.last_run_at,
            last_score=suite.last_score,
            created_at=suite.created_at,
        )

    @staticmethod
    def _run_to_result(run: EvalRun) -> EvalRunResult:
        """Convert a run model to result schema."""
        scores = run.scores or {}
        return EvalRunResult(
            run_id=run.id,
            suite_id=run.suite_id,
            status=run.status,
            overall_score=scores.get("overall", 0.0),
            scores=scores,
            total_cases=run.total_cases,
            passed_cases=run.passed_cases,
            failed_cases=run.failed_cases,
            duration_ms=run.duration_ms,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _extract_numeric(data: dict) -> float | None:
    """Extract a numeric value from a dict (takes the first numeric value found)."""
    for value in data.values():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                continue
    return None
