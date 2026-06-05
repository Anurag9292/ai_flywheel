"""Cost Optimizer — Module #35 (Phase 1, Experimentation group).

Tracks spending across the platform, enforces budgets per venture,
and alerts when spending approaches or exceeds limits.

Usage:
    from ai_flywheel.modules.experimentation.cost_optimizer import (
        CostOptimizer,
        setup_cost_listener,
    )

    optimizer = CostOptimizer()
    await optimizer.record_cost(venture_id, "agent_factory", "llm_call", 0.03, "openai")
    report = await optimizer.get_report(venture_id, "monthly")
"""

from .listener import setup_cost_listener
from .models import Budget, CostAlert
from .schemas import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    CostAlertResponse,
    CostReport,
    CostTrend,
)
from .service import CostOptimizer

__all__ = [
    "Budget",
    "BudgetCreate",
    "BudgetResponse",
    "BudgetUpdate",
    "CostAlert",
    "CostAlertResponse",
    "CostOptimizer",
    "CostReport",
    "CostTrend",
    "setup_cost_listener",
]
