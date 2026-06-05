"""Evaluation Framework — Module #22 (Phase 4).

Provides eval suites with configurable metrics, test case management,
automated scoring, and run comparison for ML/AI modules.
"""

from .models import EvalRun, EvalSuite
from .schemas import (
    AddTestCaseRequest,
    EvalRunResult,
    EvalSuiteCreate,
    EvalSuiteResponse,
    MetricConfig,
    RunEvalRequest,
)
from .service import EvaluationFramework

__all__ = [
    "AddTestCaseRequest",
    "EvalRun",
    "EvalRunResult",
    "EvalSuite",
    "EvalSuiteCreate",
    "EvalSuiteResponse",
    "EvaluationFramework",
    "MetricConfig",
    "RunEvalRequest",
]
