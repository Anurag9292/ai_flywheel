# ruff: noqa: E501
"""Policy Engine — evaluates governance policies and enforces rules.

Provides a centralized policy evaluation system that checks actions
against configurable rules for safety, compliance, rate limiting,
content filtering, and cost governance.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select, update

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import get_tracer
from ai_flywheel.modules.agent_runtime.policy_engine.models import (
    Policy,
    PolicyViolation,
)
from ai_flywheel.modules.agent_runtime.policy_engine.schemas import (
    PolicyCheckRequest,
    PolicyCheckResult,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
    ViolationDetail,
    ViolationResponse,
)

logger = structlog.get_logger()

MODULE_NAME = "policy_engine"


class PolicyEngine:
    """Evaluates governance policies and records violations."""

    async def create_policy(
        self,
        venture_id: str,
        data: PolicyCreate,
    ) -> PolicyResponse:
        """Create a new governance policy."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "create_policy"):
            async with get_session(venture_id) as session:
                policy = Policy(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description or None,
                    policy_type=data.policy_type,
                    rules=data.rules,
                    enforcement=data.enforcement,
                    scope=data.scope,
                    is_active=True,
                    violation_count=0,
                )
                session.add(policy)
                await session.flush()

                response = PolicyResponse.model_validate(policy)

            # Emit event
            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="policy.created",
                source_module=MODULE_NAME,
                payload={
                    "policy_id": response.id,
                    "name": data.name,
                    "policy_type": data.policy_type,
                    "enforcement": data.enforcement,
                },
                venture_id=venture_id,
            )

            logger.info(
                "policy_created",
                policy_id=response.id,
                venture_id=venture_id,
                policy_type=data.policy_type,
            )

            return response

    async def get_policy(
        self,
        venture_id: str,
        policy_id: str,
    ) -> PolicyResponse:
        """Get a single policy by ID."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "get_policy"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(Policy).where(
                        Policy.id == policy_id,
                        Policy.venture_id == venture_id,
                    )
                )
                policy = result.scalar_one_or_none()
                if policy is None:
                    raise ValueError(f"Policy {policy_id} not found")

                return PolicyResponse.model_validate(policy)

    async def list_policies(
        self,
        venture_id: str,
        policy_type: str | None = None,
    ) -> list[PolicyResponse]:
        """List all policies for a venture, optionally filtered by type."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "list_policies"):
            async with get_session(venture_id) as session:
                query = select(Policy).where(Policy.venture_id == venture_id)
                if policy_type:
                    query = query.where(Policy.policy_type == policy_type)

                result = await session.execute(query)
                policies = result.scalars().all()

                return [PolicyResponse.model_validate(p) for p in policies]

    async def update_policy(
        self,
        venture_id: str,
        policy_id: str,
        data: PolicyUpdate,
    ) -> PolicyResponse:
        """Update an existing policy."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "update_policy"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(Policy).where(
                        Policy.id == policy_id,
                        Policy.venture_id == venture_id,
                    )
                )
                policy = result.scalar_one_or_none()
                if policy is None:
                    raise ValueError(f"Policy {policy_id} not found")

                # Apply updates for non-None fields
                update_data = data.model_dump(exclude_none=True)
                for field, value in update_data.items():
                    setattr(policy, field, value)

                await session.flush()

                return PolicyResponse.model_validate(policy)

    async def check(
        self,
        venture_id: str,
        request: PolicyCheckRequest,
    ) -> PolicyCheckResult:
        """Evaluate all applicable policies against an action.

        Policy evaluation logic:
        1. Load active policies whose scope includes the requesting module/agent
        2. For each policy, evaluate each rule against the context
        3. If any rule violation + enforcement="block" → allowed=False
        4. Record violations in DB, increment policy violation_count
        5. Emit events
        """
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "check"):
            # Load applicable policies
            applicable_policies = await self._load_applicable_policies(
                venture_id, request.module_name, request.agent_id
            )

            violations: list[ViolationDetail] = []
            warnings: list[str] = []
            allowed = True

            for policy in applicable_policies:
                rule_violations = await self._evaluate_policy(
                    venture_id, policy, request
                )

                for violation in rule_violations:
                    if policy.enforcement == "block":
                        allowed = False
                        violations.append(violation)
                    elif policy.enforcement == "warn":
                        warnings.append(violation.message)
                        violations.append(violation)
                    else:
                        # log enforcement — record but don't block or warn
                        violations.append(violation)

            # Record violations in DB
            if violations:
                await self._record_violations(venture_id, request, violations)

                # Emit violation event
                event_bus = get_event_bus()
                await event_bus.publish(
                    event_type="policy.violated",
                    source_module=MODULE_NAME,
                    payload={
                        "module_name": request.module_name,
                        "agent_id": request.agent_id,
                        "action": request.action,
                        "violation_count": len(violations),
                        "blocked": not allowed,
                    },
                    venture_id=venture_id,
                )
            else:
                # Emit passed event
                event_bus = get_event_bus()
                await event_bus.publish(
                    event_type="policy.check.passed",
                    source_module=MODULE_NAME,
                    payload={
                        "module_name": request.module_name,
                        "agent_id": request.agent_id,
                        "action": request.action,
                        "policies_checked": len(applicable_policies),
                    },
                    venture_id=venture_id,
                )

            logger.info(
                "policy_check_complete",
                venture_id=venture_id,
                module_name=request.module_name,
                action=request.action,
                allowed=allowed,
                violations=len(violations),
            )

            return PolicyCheckResult(
                allowed=allowed,
                violations=violations,
                warnings=warnings,
            )

    async def get_violations(
        self,
        venture_id: str,
        policy_id: str | None = None,
        resolved: bool | None = None,
    ) -> list[ViolationResponse]:
        """Get recorded policy violations with optional filters."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "get_violations"):
            async with get_session(venture_id) as session:
                query = select(PolicyViolation).where(
                    PolicyViolation.venture_id == venture_id,
                )
                if policy_id:
                    query = query.where(PolicyViolation.policy_id == policy_id)
                if resolved is not None:
                    query = query.where(PolicyViolation.resolved == resolved)

                query = query.order_by(PolicyViolation.created_at.desc())

                result = await session.execute(query)
                violations = result.scalars().all()

                return [ViolationResponse.model_validate(v) for v in violations]

    async def resolve_violation(
        self,
        venture_id: str,
        violation_id: str,
    ) -> None:
        """Mark a violation as resolved."""
        tracer = get_tracer()
        async with tracer.span(MODULE_NAME, "resolve_violation"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(PolicyViolation).where(
                        PolicyViolation.id == violation_id,
                        PolicyViolation.venture_id == venture_id,
                    )
                )
                violation = result.scalar_one_or_none()
                if violation is None:
                    raise ValueError(f"Violation {violation_id} not found")

                violation.resolved = True
                await session.flush()

    async def _load_applicable_policies(
        self,
        venture_id: str,
        module_name: str,
        agent_id: str | None,
    ) -> list[Policy]:
        """Load all active policies whose scope covers the given module/agent."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Policy).where(
                    Policy.venture_id == venture_id,
                    Policy.is_active.is_(True),
                )
            )
            all_policies = result.scalars().all()

        applicable = []
        for policy in all_policies:
            scope = policy.scope

            # "all: true" means applies everywhere
            if scope.get("all"):
                applicable.append(policy)
                continue

            # Check if module is in scope
            scoped_modules = scope.get("modules", [])
            if module_name in scoped_modules:
                applicable.append(policy)
                continue

            # Check if agent is in scope
            scoped_agents = scope.get("agents", [])
            if agent_id and agent_id in scoped_agents:
                applicable.append(policy)
                continue

        return applicable

    async def _evaluate_policy(
        self,
        venture_id: str,
        policy: Policy,
        request: PolicyCheckRequest,
    ) -> list[ViolationDetail]:
        """Evaluate a single policy's rules against the request."""
        violations: list[ViolationDetail] = []

        for rule in policy.rules:
            rule_type = rule.get("type", "")
            violation = await self._evaluate_rule(
                venture_id, policy, rule, rule_type, request
            )
            if violation:
                violations.append(violation)

        return violations

    async def _evaluate_rule(
        self,
        venture_id: str,
        policy: Policy,
        rule: dict[str, Any],
        rule_type: str,
        request: PolicyCheckRequest,
    ) -> ViolationDetail | None:
        """Evaluate a single rule against the request context."""

        if rule_type == "keyword_block":
            return self._check_keyword_block(policy, rule, request)

        elif rule_type == "cost_limit":
            return self._check_cost_limit(policy, rule, request)

        elif rule_type == "rate_limit":
            return await self._check_rate_limit(venture_id, policy, rule, request)

        elif rule_type == "content_filter":
            return self._check_content_filter(policy, rule, request)

        elif rule_type == "require_approval":
            return self._check_require_approval(policy, rule, request)

        return None

    def _check_keyword_block(
        self,
        policy: Policy,
        rule: dict[str, Any],
        request: PolicyCheckRequest,
    ) -> ViolationDetail | None:
        """Block if action contains any of the prohibited keywords."""
        keywords = rule.get("keywords", [])
        action_lower = request.action.lower()

        for keyword in keywords:
            if keyword.lower() in action_lower:
                return ViolationDetail(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    rule_violated=f"keyword_block: '{keyword}'",
                    enforcement=policy.enforcement,
                    message=f"Action contains prohibited keyword: '{keyword}'",
                )

        return None

    def _check_cost_limit(
        self,
        policy: Policy,
        rule: dict[str, Any],
        request: PolicyCheckRequest,
    ) -> ViolationDetail | None:
        """Block if context.cost exceeds the maximum allowed."""
        max_usd = rule.get("max_usd")
        if max_usd is None:
            return None

        cost = request.context.get("cost")
        if cost is not None and cost > max_usd:
            return ViolationDetail(
                policy_id=policy.id,
                policy_name=policy.name,
                rule_violated=f"cost_limit: max ${max_usd}",
                enforcement=policy.enforcement,
                message=f"Cost ${cost} exceeds limit of ${max_usd}",
            )

        return None

    async def _check_rate_limit(
        self,
        venture_id: str,
        policy: Policy,
        rule: dict[str, Any],
        request: PolicyCheckRequest,
    ) -> ViolationDetail | None:
        """Block if rate of violations in the last hour exceeds threshold."""
        max_per_hour = rule.get("max_per_hour")
        if max_per_hour is None:
            return None

        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(func.count(PolicyViolation.id)).where(
                    PolicyViolation.venture_id == venture_id,
                    PolicyViolation.policy_id == policy.id,
                    PolicyViolation.created_at >= one_hour_ago,
                )
            )
            count = result.scalar() or 0

        if count >= max_per_hour:
            return ViolationDetail(
                policy_id=policy.id,
                policy_name=policy.name,
                rule_violated=f"rate_limit: max {max_per_hour}/hour",
                enforcement=policy.enforcement,
                message=f"Rate limit exceeded: {count} violations in last hour (max {max_per_hour})",
            )

        return None

    def _check_content_filter(
        self,
        policy: Policy,
        rule: dict[str, Any],
        request: PolicyCheckRequest,
    ) -> ViolationDetail | None:
        """Block if action matches any prohibited regex patterns."""
        patterns = rule.get("prohibited_patterns", [])

        for pattern in patterns:
            try:
                if re.search(pattern, request.action, re.IGNORECASE):
                    return ViolationDetail(
                        policy_id=policy.id,
                        policy_name=policy.name,
                        rule_violated=f"content_filter: pattern '{pattern}'",
                        enforcement=policy.enforcement,
                        message=f"Action matches prohibited content pattern: '{pattern}'",
                    )
            except re.error:
                logger.warning(
                    "invalid_regex_pattern",
                    policy_id=policy.id,
                    pattern=pattern,
                )
                continue

        return None

    def _check_require_approval(
        self,
        policy: Policy,
        rule: dict[str, Any],
        request: PolicyCheckRequest,
    ) -> ViolationDetail | None:
        """Flag action for review if it matches the for_actions list."""
        for_actions = rule.get("for_actions", [])

        for action_pattern in for_actions:
            if action_pattern.lower() in request.action.lower():
                return ViolationDetail(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    rule_violated=f"require_approval: for '{action_pattern}'",
                    enforcement=policy.enforcement,
                    message=f"Action '{request.action}' requires approval (matched '{action_pattern}')",
                )

        return None

    async def _record_violations(
        self,
        venture_id: str,
        request: PolicyCheckRequest,
        violations: list[ViolationDetail],
    ) -> None:
        """Record violations in DB and increment policy violation counts."""
        async with get_session(venture_id) as session:
            # Group violations by policy for count updates
            policy_ids = set()

            for violation in violations:
                policy_ids.add(violation.policy_id)

                record = PolicyViolation(
                    venture_id=venture_id,
                    policy_id=violation.policy_id,
                    agent_id=request.agent_id,
                    module_name=request.module_name,
                    action_attempted=request.action,
                    violation_details={
                        "rule_violated": violation.rule_violated,
                        "message": violation.message,
                        "context": request.context,
                    },
                    enforcement_action=_enforcement_to_action(violation.enforcement),
                    resolved=False,
                )
                session.add(record)

            # Increment violation counts on policies
            for policy_id in policy_ids:
                await session.execute(
                    update(Policy)
                    .where(Policy.id == policy_id)
                    .values(violation_count=Policy.violation_count + 1)
                )

            await session.flush()


def _enforcement_to_action(enforcement: str) -> str:
    """Map enforcement level to recorded action string."""
    mapping = {
        "block": "blocked",
        "warn": "warned",
        "log": "logged",
    }
    return mapping.get(enforcement, "logged")
