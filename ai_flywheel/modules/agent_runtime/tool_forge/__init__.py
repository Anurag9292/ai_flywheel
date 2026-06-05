"""Tool Forge — Phase 3, Module #10.

Registry, invocation engine, and observability for agent tools.
Tools are external capabilities (APIs, webhooks, services) that agents can invoke
at runtime. The Tool Forge handles registration, schema validation, HTTP execution,
reliability tracking, and keyword search.

Usage:
    from ai_flywheel.modules.agent_runtime.tool_forge import (
        ToolForge,
        ToolDefinition,
        ToolExecution,
        ToolCreate,
        ToolUpdate,
        ToolResponse,
        ToolInvokeRequest,
        ToolInvokeResult,
        ToolSearchRequest,
        ToolSearchResult,
    )

    forge = ToolForge()
    tool = await forge.register_tool(venture_id, ToolCreate(
        name="slack-notify",
        description="Send a Slack notification",
        category="communication",
        config={"base_url": "https://hooks.slack.com", "method": "POST", "path": "/services/..."},
    ))
    result = await forge.invoke(venture_id, ToolInvokeRequest(
        tool_name="slack-notify",
        parameters={"text": "Hello from AI Flywheel!"},
    ))
"""

from .models import ToolDefinition, ToolExecution
from .schemas import (
    ToolCreate,
    ToolInvokeRequest,
    ToolInvokeResult,
    ToolResponse,
    ToolSearchRequest,
    ToolSearchResult,
    ToolUpdate,
)
from .service import ToolForge

__all__ = [
    # Service
    "ToolForge",
    # Models
    "ToolDefinition",
    "ToolExecution",
    # Schemas
    "ToolCreate",
    "ToolUpdate",
    "ToolResponse",
    "ToolInvokeRequest",
    "ToolInvokeResult",
    "ToolSearchRequest",
    "ToolSearchResult",
]
