"""Agent Factory & Orchestration — Phase 1, Module #9.

Agents are defined as data (config), not code. Execution flows through Temporal
workflows for durability, retryability, and human-in-the-loop approval.

Usage:
    from ai_flywheel.modules.agent_runtime.agent_factory import (
        AgentFactory,
        AgentBlueprint,
        AgentBlueprintCreate,
        AgentBlueprintUpdate,
        AgentBlueprintResponse,
        AgentExecutionRequest,
        AgentExecutionResult,
    )

    factory = AgentFactory()
    agent = await factory.create_agent(venture_id, AgentBlueprintCreate(
        name="content-writer",
        system_prompt="You are a professional content writer...",
        agent_type="single",
    ))
    result = await factory.execute(venture_id, AgentExecutionRequest(
        agent_name="content-writer",
        task="Write a blog post about AI flywheels",
    ))
"""

from .execution import (
    AgentActivityInput,
    AgentActivityOutput,
    ApprovalAgentWorkflow,
    ApprovalWorkflowInput,
    ChainAgentWorkflow,
    ChainWorkflowInput,
    ParallelAgentWorkflow,
    ParallelWorkflowInput,
    SingleAgentWorkflow,
    SingleWorkflowInput,
    execute_agent_activity,
)
from .models import AgentBlueprint
from .schemas import (
    AgentBlueprintCreate,
    AgentBlueprintResponse,
    AgentBlueprintUpdate,
    AgentExecutionRequest,
    AgentExecutionResult,
)
from .service import AgentFactory

__all__ = [
    # Service
    "AgentFactory",
    # Models
    "AgentBlueprint",
    # Schemas
    "AgentBlueprintCreate",
    "AgentBlueprintUpdate",
    "AgentBlueprintResponse",
    "AgentExecutionRequest",
    "AgentExecutionResult",
    # Temporal workflows
    "SingleAgentWorkflow",
    "SingleWorkflowInput",
    "ChainAgentWorkflow",
    "ChainWorkflowInput",
    "ParallelAgentWorkflow",
    "ParallelWorkflowInput",
    "ApprovalAgentWorkflow",
    "ApprovalWorkflowInput",
    # Temporal activities
    "execute_agent_activity",
    "AgentActivityInput",
    "AgentActivityOutput",
]
