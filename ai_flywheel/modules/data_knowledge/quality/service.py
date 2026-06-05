# ruff: noqa: E501
"""Data Quality Engine — core service.

Profiles datasets, applies validation rules, computes quality scores,
and persists reports. Pure Python implementation (no pandas/GE).
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer

from .models import QualityReport, QualityRule
from .schemas import (
    FieldProfile,
    QualityCheckRequest,
    QualityCheckResult,
    QualityIssue,
    QualityRuleCreate,
    QualityRuleResponse,
)

logger = structlog.get_logger()

# Maximum sample values to store in profiles/issues
_MAX_SAMPLES = 5


class DataQualityEngine:
    """Validates datasets against configurable rules and profiles field statistics."""

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    async def create_rule(
        self, venture_id: str, data: QualityRuleCreate
    ) -> QualityRuleResponse:
        """Persist a new quality rule for the given venture."""
        async with get_session(venture_id) as session:
            rule = QualityRule(
                venture_id=venture_id,
                name=data.name,
                rule_type=data.rule_type,
                field_name=data.field_name,
                config=data.config,
                severity=data.severity,
                is_active=True,
            )
            session.add(rule)
            await session.flush()
            await session.refresh(rule)

            logger.info(
                "quality_rule_created",
                venture_id=venture_id,
                rule_id=rule.id,
                rule_type=data.rule_type,
                field_name=data.field_name,
            )

            return QualityRuleResponse.model_validate(rule)

    async def list_rules(self, venture_id: str) -> list[QualityRuleResponse]:
        """List all active quality rules for a venture."""
        async with get_session(venture_id) as session:
            stmt = (
                select(QualityRule)
                .where(QualityRule.venture_id == venture_id)
                .where(QualityRule.is_active.is_(True))
                .where(QualityRule.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            rules = result.scalars().all()
            return [QualityRuleResponse.model_validate(r) for r in rules]

    # ------------------------------------------------------------------
    # Quality Check (main entry point)
    # ------------------------------------------------------------------

    async def check(
        self, venture_id: str, request: QualityCheckRequest
    ) -> QualityCheckResult:
        """Run a quality check: profile data, evaluate rules, persist report."""
        tracer = get_tracer()
        event_bus = get_event_bus()

        async with tracer.span(
            "data_quality", "check", input_data={"dataset_name": request.dataset_name}
        ):
            start = time.perf_counter()

            records = request.records
            total_records = len(records)

            # 1. Profile all fields (single pass)
            field_profiles = self.profile_dataset(records)

            # 2. Load applicable rules
            rules = await self._load_rules(venture_id, request.rules)

            # 3. Evaluate rules
            issues: list[QualityIssue] = []
            invalid_record_indices: set[int] = set()
            type_violation_count = 0
            total_checks = 0

            for rule in rules:
                rule_issues, violating_indices, type_violations, checks = (
                    self._evaluate_rule(rule, records)
                )
                issues.extend(rule_issues)
                invalid_record_indices.update(violating_indices)
                type_violation_count += type_violations
                total_checks += checks

            # 4. Compute scores
            completeness_score = self._compute_completeness(field_profiles, total_records)
            consistency_score = (
                1.0 - (type_violation_count / total_checks) if total_checks > 0 else 1.0
            )
            error_rate = (
                len(invalid_record_indices) / total_records if total_records > 0 else 0.0
            )
            quality_score = (
                0.4 * completeness_score
                + 0.3 * consistency_score
                + 0.3 * (1.0 - error_rate)
            )

            valid_records = total_records - len(invalid_record_indices)
            invalid_records = len(invalid_record_indices)

            elapsed_ms = (time.perf_counter() - start) * 1000

            # 5. Persist report
            report_id = await self._persist_report(
                venture_id=venture_id,
                source_id=request.source_id,
                dataset_name=request.dataset_name,
                total_records=total_records,
                valid_records=valid_records,
                invalid_records=invalid_records,
                quality_score=quality_score,
                completeness_score=completeness_score,
                consistency_score=consistency_score,
                issues=issues,
                field_profiles=field_profiles,
                run_duration_ms=elapsed_ms,
            )

            result = QualityCheckResult(
                report_id=report_id,
                dataset_name=request.dataset_name,
                total_records=total_records,
                valid_records=valid_records,
                invalid_records=invalid_records,
                quality_score=quality_score,
                completeness_score=completeness_score,
                consistency_score=consistency_score,
                issues=issues,
                field_profiles=field_profiles,
            )

            # 6. Emit events
            await event_bus.publish(
                event_type="quality.check.completed",
                source_module="data_quality",
                payload={
                    "report_id": report_id,
                    "dataset_name": request.dataset_name,
                    "quality_score": quality_score,
                    "total_records": total_records,
                    "invalid_records": invalid_records,
                },
                venture_id=venture_id,
            )

            if issues:
                await event_bus.publish(
                    event_type="quality.issue.detected",
                    source_module="data_quality",
                    payload={
                        "report_id": report_id,
                        "dataset_name": request.dataset_name,
                        "issue_count": len(issues),
                        "error_count": sum(
                            1 for i in issues if i.severity == "error"
                        ),
                    },
                    venture_id=venture_id,
                )

            logger.info(
                "quality_check_completed",
                venture_id=venture_id,
                report_id=report_id,
                dataset_name=request.dataset_name,
                quality_score=round(quality_score, 4),
                total_records=total_records,
                invalid_records=invalid_records,
                issues_found=len(issues),
                duration_ms=round(elapsed_ms, 2),
            )

            return result

    # ------------------------------------------------------------------
    # Report retrieval
    # ------------------------------------------------------------------

    async def get_report(self, venture_id: str, report_id: str) -> QualityCheckResult:
        """Retrieve a persisted quality report by ID."""
        async with get_session(venture_id) as session:
            stmt = (
                select(QualityReport)
                .where(QualityReport.id == report_id)
                .where(QualityReport.venture_id == venture_id)
                .where(QualityReport.deleted_at.is_(None))
            )
            result = await session.execute(stmt)
            report = result.scalar_one()

            return self._report_to_result(report)

    async def get_reports(
        self, venture_id: str, source_id: str | None = None
    ) -> list[QualityCheckResult]:
        """List quality reports, optionally filtered by source_id."""
        async with get_session(venture_id) as session:
            stmt = (
                select(QualityReport)
                .where(QualityReport.venture_id == venture_id)
                .where(QualityReport.deleted_at.is_(None))
                .order_by(QualityReport.created_at.desc())
            )
            if source_id is not None:
                stmt = stmt.where(QualityReport.source_id == source_id)

            result = await session.execute(stmt)
            reports = result.scalars().all()
            return [self._report_to_result(r) for r in reports]

    # ------------------------------------------------------------------
    # Profiling (static / classmethod — pure computation)
    # ------------------------------------------------------------------

    @staticmethod
    def profile_field(records: list[dict[str, Any]], field_name: str) -> FieldProfile:
        """Profile a single field across all records in one pass."""
        non_null_count = 0
        null_count = 0
        unique_values: set[Any] = set()
        numeric_values: list[float] = []
        samples: list[Any] = []

        min_val: Any = None
        max_val: Any = None
        inferred_dtype = "unknown"

        for record in records:
            value = record.get(field_name)

            if value is None or value == "":
                null_count += 1
                continue

            non_null_count += 1

            # Collect samples (up to _MAX_SAMPLES unique ones)
            if len(samples) < _MAX_SAMPLES and value not in samples:
                samples.append(value)

            # Track uniqueness (use repr for unhashable types)
            try:
                unique_values.add(value)
            except TypeError:
                unique_values.add(repr(value))

            # Numeric tracking for min/max/mean
            num = _try_numeric(value)
            if num is not None:
                numeric_values.append(num)
                if min_val is None or num < min_val:
                    min_val = num
                if max_val is None or num > max_val:
                    max_val = num
            else:
                # String comparison for non-numeric
                str_val = str(value)
                if min_val is None or str_val < str(min_val):
                    min_val = value
                if max_val is None or str_val > str(max_val):
                    max_val = value

        # Infer dtype from observed values
        if numeric_values and len(numeric_values) == non_null_count:
            # All non-null values are numeric
            if all(v == int(v) for v in numeric_values):
                inferred_dtype = "int"
            else:
                inferred_dtype = "float"
        elif non_null_count > 0:
            # Check first sample for type hint
            sample = samples[0] if samples else None
            if isinstance(sample, bool):
                inferred_dtype = "bool"
            elif isinstance(sample, int):
                inferred_dtype = "int"
            elif isinstance(sample, float):
                inferred_dtype = "float"
            elif isinstance(sample, (datetime, date)):
                inferred_dtype = "date"
            else:
                inferred_dtype = "str"

        mean_value = (
            sum(numeric_values) / len(numeric_values) if numeric_values else None
        )

        return FieldProfile(
            field_name=field_name,
            dtype=inferred_dtype,
            non_null_count=non_null_count,
            null_count=null_count,
            unique_count=len(unique_values),
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_value,
            sample_values=samples,
        )

    @staticmethod
    def profile_dataset(records: list[dict[str, Any]]) -> dict[str, FieldProfile]:
        """Profile all fields in a dataset. Single pass over records."""
        if not records:
            return {}

        # Gather all field names from all records
        all_fields: set[str] = set()
        for record in records:
            all_fields.update(record.keys())

        # Profile each field
        profiles: dict[str, FieldProfile] = {}
        for field_name in sorted(all_fields):
            profiles[field_name] = DataQualityEngine.profile_field(records, field_name)

        return profiles

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_rules(
        self, venture_id: str, rule_ids: list[str] | None
    ) -> list[QualityRule]:
        """Load rules from DB. If rule_ids specified, filter to those."""
        async with get_session(venture_id) as session:
            stmt = (
                select(QualityRule)
                .where(QualityRule.venture_id == venture_id)
                .where(QualityRule.is_active.is_(True))
                .where(QualityRule.deleted_at.is_(None))
            )
            if rule_ids is not None:
                stmt = stmt.where(QualityRule.id.in_(rule_ids))

            result = await session.execute(stmt)
            return list(result.scalars().all())

    def _evaluate_rule(
        self, rule: QualityRule, records: list[dict[str, Any]]
    ) -> tuple[list[QualityIssue], set[int], int, int]:
        """Evaluate a single rule against all records.

        Returns:
            (issues, violating_record_indices, type_violation_count, total_checks)
        """
        field = rule.field_name
        config = rule.config or {}
        violations: list[Any] = []
        violating_indices: set[int] = set()
        type_violation_count = 0
        total_checks = 0

        if rule.rule_type == "not_null":
            for idx, record in enumerate(records):
                total_checks += 1
                value = record.get(field)
                if value is None or value == "":
                    violations.append(value)
                    violating_indices.add(idx)

        elif rule.rule_type == "type_check":
            expected_type = config.get("expected_type", "str")
            for idx, record in enumerate(records):
                total_checks += 1
                value = record.get(field)
                if value is None:
                    continue  # type_check does not enforce presence
                if not _check_type(value, expected_type):
                    violations.append(value)
                    violating_indices.add(idx)
                    type_violation_count += 1

        elif rule.rule_type == "range":
            min_val = config.get("min")
            max_val = config.get("max")
            for idx, record in enumerate(records):
                total_checks += 1
                value = record.get(field)
                if value is None:
                    continue
                num = _try_numeric(value)
                if num is None:
                    violations.append(value)
                    violating_indices.add(idx)
                elif (min_val is not None and num < min_val) or (
                    max_val is not None and num > max_val
                ):
                    violations.append(value)
                    violating_indices.add(idx)

        elif rule.rule_type == "regex":
            pattern_str = config.get("pattern", "")
            try:
                pattern = re.compile(pattern_str)
            except re.error:
                logger.warning(
                    "invalid_regex_pattern",
                    rule_id=rule.id,
                    pattern=pattern_str,
                )
                return [], set(), 0, 0

            for idx, record in enumerate(records):
                total_checks += 1
                value = record.get(field)
                if value is None:
                    continue
                if not pattern.search(str(value)):
                    violations.append(value)
                    violating_indices.add(idx)

        elif rule.rule_type == "unique":
            seen: dict[Any, int] = {}
            for idx, record in enumerate(records):
                total_checks += 1
                value = record.get(field)
                if value is None:
                    continue
                key = value if isinstance(value, (str, int, float, bool)) else repr(value)
                if key in seen:
                    violations.append(value)
                    violating_indices.add(idx)
                    # Also mark the first occurrence as violating
                    violating_indices.add(seen[key])
                else:
                    seen[key] = idx

        elif rule.rule_type == "custom":
            expression = config.get("expression", "")
            for idx, record in enumerate(records):
                total_checks += 1
                value = record.get(field)
                if not _evaluate_custom_expression(expression, value, record):
                    violations.append(value)
                    violating_indices.add(idx)

        # Build issue if there are violations
        issues: list[QualityIssue] = []
        if violations:
            sample_values = violations[:_MAX_SAMPLES]
            issues.append(
                QualityIssue(
                    field=field,
                    rule=rule.name,
                    severity=rule.severity,
                    count=len(violations),
                    sample_values=sample_values,
                    message=_build_issue_message(rule, len(violations), len(records)),
                )
            )

        return issues, violating_indices, type_violation_count, total_checks

    @staticmethod
    def _compute_completeness(
        field_profiles: dict[str, FieldProfile], total_records: int
    ) -> float:
        """Completeness = avg(non_null_count / total) across all fields."""
        if not field_profiles or total_records == 0:
            return 1.0

        ratios: list[float] = []
        for profile in field_profiles.values():
            ratio = profile.non_null_count / total_records if total_records > 0 else 0.0
            ratios.append(ratio)

        return sum(ratios) / len(ratios) if ratios else 1.0

    async def _persist_report(
        self,
        venture_id: str,
        source_id: str | None,
        dataset_name: str,
        total_records: int,
        valid_records: int,
        invalid_records: int,
        quality_score: float,
        completeness_score: float,
        consistency_score: float,
        issues: list[QualityIssue],
        field_profiles: dict[str, FieldProfile],
        run_duration_ms: float,
    ) -> str:
        """Persist the quality report and return its ID."""
        async with get_session(venture_id) as session:
            report = QualityReport(
                venture_id=venture_id,
                source_id=source_id,
                dataset_name=dataset_name,
                total_records=total_records,
                valid_records=valid_records,
                invalid_records=invalid_records,
                quality_score=quality_score,
                completeness_score=completeness_score,
                consistency_score=consistency_score,
                freshness_score=1.0,
                issues=[issue.model_dump() for issue in issues],
                field_profiles={
                    name: profile.model_dump() for name, profile in field_profiles.items()
                },
                run_duration_ms=run_duration_ms,
            )
            session.add(report)
            await session.flush()
            await session.refresh(report)
            return report.id

    @staticmethod
    def _report_to_result(report: QualityReport) -> QualityCheckResult:
        """Convert a persisted QualityReport to a QualityCheckResult."""
        issues = [QualityIssue(**i) for i in (report.issues or [])]
        field_profiles = {
            name: FieldProfile(**data)
            for name, data in (report.field_profiles or {}).items()
        }

        return QualityCheckResult(
            report_id=report.id,
            dataset_name=report.dataset_name,
            total_records=report.total_records,
            valid_records=report.valid_records,
            invalid_records=report.invalid_records,
            quality_score=report.quality_score,
            completeness_score=report.completeness_score,
            consistency_score=report.consistency_score,
            issues=issues,
            field_profiles=field_profiles,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _try_numeric(value: Any) -> float | None:
    """Attempt to parse a value as a float. Returns None if not numeric."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def _check_type(value: Any, expected_type: str) -> bool:
    """Check if a value is parseable as the expected type."""
    if expected_type == "int":
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        return False

    elif expected_type == "float":
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        return False

    elif expected_type == "bool":
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            return value.lower() in ("true", "false", "1", "0", "yes", "no")
        return False

    elif expected_type == "date":
        if isinstance(value, (datetime, date)):
            return True
        if isinstance(value, str):
            # Try common date formats
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    continue
            return False
        return False

    # Default: str — everything is a valid string
    return True


def _evaluate_custom_expression(
    expression: str, value: Any, record: dict[str, Any]
) -> bool:
    """Evaluate a simple custom expression safely.

    Supports basic comparisons: value > 0, value != '', len(value) > 3, etc.
    Uses a restricted eval with only the value and record in scope.
    """
    if not expression:
        return True

    safe_globals: dict[str, Any] = {"__builtins__": {}}
    safe_locals: dict[str, Any] = {
        "value": value,
        "record": record,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "abs": abs,
        "min": min,
        "max": max,
        "isinstance": isinstance,
        "None": None,
        "True": True,
        "False": False,
    }

    try:
        result = eval(expression, safe_globals, safe_locals)  # noqa: S307
        return bool(result)
    except Exception:
        # If expression fails to evaluate, treat as passing
        logger.warning("custom_expression_error", expression=expression, value=value)
        return True


def _build_issue_message(rule: QualityRule, violation_count: int, total: int) -> str:
    """Build a human-readable issue message."""
    pct = (violation_count / total * 100) if total > 0 else 0

    messages = {
        "not_null": f"Field '{rule.field_name}' has {violation_count} null/empty values ({pct:.1f}% of records)",
        "type_check": f"Field '{rule.field_name}' has {violation_count} values that are not valid {rule.config.get('expected_type', 'type')} ({pct:.1f}%)",
        "range": f"Field '{rule.field_name}' has {violation_count} values outside allowed range ({pct:.1f}%)",
        "regex": f"Field '{rule.field_name}' has {violation_count} values not matching pattern ({pct:.1f}%)",
        "unique": f"Field '{rule.field_name}' has {violation_count} duplicate values ({pct:.1f}%)",
        "custom": f"Field '{rule.field_name}' has {violation_count} values failing custom rule '{rule.name}' ({pct:.1f}%)",
    }

    return messages.get(
        rule.rule_type,
        f"Rule '{rule.name}' found {violation_count} violations on field '{rule.field_name}' ({pct:.1f}%)",
    )
