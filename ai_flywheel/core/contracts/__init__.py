"""Typed contracts for inter-module communication.

All data exchanged between modules must use schemas defined here.
This ensures type safety without coupling modules to each other.
"""

from ai_flywheel.core.contracts.events import (
    AgentCompletedEvent,
    CostThresholdBreachedEvent,
    LLMCallCompletedEvent,
    VentureCreatedEvent,
    WorkflowCompletedEvent,
)
from ai_flywheel.core.contracts.schemas import (
    CostSummary,
    HealthStatus,
    LLMRequest,
    LLMResponse,
    VentureInfo,
)

__all__ = [
    "AgentCompletedEvent",
    "CostSummary",
    "CostThresholdBreachedEvent",
    "HealthStatus",
    "LLMCallCompletedEvent",
    "LLMRequest",
    "LLMResponse",
    "VentureCreatedEvent",
    "VentureInfo",
    "WorkflowCompletedEvent",
]
