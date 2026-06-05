# ruff: noqa: E501
"""Workflow Blueprint Engine — designs, validates, and compiles workflow graphs.

This module assists in workflow design by:
1. Creating and managing workflow blueprints as directed graphs
2. LLM-powered generation of workflows from natural language descriptions
3. Structural validation (reachability, cycles, connectivity)
4. Compilation into Temporal workflow configurations
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import WorkflowBlueprint
from .schemas import (
    BlueprintCreate,
    BlueprintResponse,
    CompileRequest,
    CompileResult,
    EdgeSpec,
    GenerateBlueprintRequest,
    GenerateBlueprintResult,
    NodeSpec,
    ValidateBlueprintRequest,
    ValidateBlueprintResult,
)

logger = structlog.get_logger()

MODULE_NAME = "workflow_blueprint"


class WorkflowBlueprintEngine:
    """Orchestrates workflow blueprint design, validation, and compilation."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Blueprint CRUD
    # ------------------------------------------------------------------

    async def create_blueprint(
        self, venture_id: str, data: BlueprintCreate
    ) -> BlueprintResponse:
        """Create a new empty workflow blueprint."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "create_blueprint"):
            async with get_session(venture_id) as session:
                blueprint = WorkflowBlueprint(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description,
                    status="draft",
                    nodes=[],
                    edges=[],
                    sla_config=None,
                    fallback_config=None,
                    version=1,
                )
                session.add(blueprint)
                await session.flush()

                response = _blueprint_to_response(blueprint)

            await self._event_bus.publish(
                event_type="workflow.blueprint.created",
                source_module=MODULE_NAME,
                payload={"blueprint_id": response.id, "name": data.name},
                venture_id=venture_id,
            )

            logger.info(
                "workflow_blueprint_created",
                blueprint_id=response.id,
                venture_id=venture_id,
                name=data.name,
            )

            return response

    async def get_blueprint(
        self, venture_id: str, blueprint_id: str
    ) -> BlueprintResponse:
        """Retrieve a workflow blueprint by ID."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(WorkflowBlueprint).where(
                    WorkflowBlueprint.id == blueprint_id,
                    WorkflowBlueprint.venture_id == venture_id,
                    WorkflowBlueprint.deleted_at.is_(None),
                )
            )
            blueprint = result.scalar_one()
            return _blueprint_to_response(blueprint)

    async def list_blueprints(
        self, venture_id: str
    ) -> list[BlueprintResponse]:
        """List all workflow blueprints for a venture."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(WorkflowBlueprint).where(
                    WorkflowBlueprint.venture_id == venture_id,
                    WorkflowBlueprint.deleted_at.is_(None),
                ).order_by(WorkflowBlueprint.created_at.desc())
            )
            blueprints = result.scalars().all()
            return [_blueprint_to_response(b) for b in blueprints]

    # ------------------------------------------------------------------
    # Generate from Description (LLM-powered)
    # ------------------------------------------------------------------

    async def generate_from_description(
        self, venture_id: str, request: GenerateBlueprintRequest
    ) -> GenerateBlueprintResult:
        """Generate a workflow blueprint from a natural language process description."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "generate_from_description",
            input_data={"name": request.name},
        ) as span:
            constraints_section = ""
            if request.constraints:
                constraints_section = "\n\nConstraints:\n" + "\n".join(
                    f"- {c}" for c in request.constraints
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a workflow automation architect. Your job is to convert natural language "
                        "process descriptions into structured directed workflow graphs.\n\n"
                        "Node types:\n"
                        "- start: Entry point of the workflow (exactly one)\n"
                        "- end: Terminal node (exactly one)\n"
                        "- ai_agent: An AI agent performs a task (include agent_id in config)\n"
                        "- human: A human performs a task (may include approval_required, timeout_seconds in config)\n"
                        "- tool: An automated tool/API is called (include tool_id in config)\n"
                        "- decision: A branching point based on conditions\n\n"
                        "Rules:\n"
                        "1. Every workflow must have exactly one 'start' node and one 'end' node\n"
                        "2. All nodes must be reachable from the start node\n"
                        "3. All paths must eventually reach the end node\n"
                        "4. Decision nodes must have multiple outgoing edges with conditions\n"
                        "5. Human steps should have SLA timeouts\n"
                        "6. Generate unique IDs for each node (e.g., node_1, node_2, ...)\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Convert the following process description into a workflow graph.\n\n"
                        f"Workflow Name: {request.name}\n"
                        f"Process Description: {request.process_description}"
                        + constraints_section
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "nodes": [\n'
                        "    {\n"
                        '      "id": "<node_id>",\n'
                        '      "name": "<descriptive name>",\n'
                        '      "type": "<start|end|ai_agent|human|tool|decision>",\n'
                        '      "config": {"agent_id": "...", "tool_id": "...", "approval_required": true, "timeout_seconds": 3600},\n'
                        '      "inputs": ["<data this node needs>"],\n'
                        '      "outputs": ["<data this node produces>"],\n'
                        '      "sla_seconds": null\n'
                        "    }\n"
                        "  ],\n"
                        '  "edges": [\n'
                        "    {\n"
                        '      "source_node_id": "<from node>",\n'
                        '      "target_node_id": "<to node>",\n'
                        '      "condition": null\n'
                        "    }\n"
                        "  ],\n"
                        '  "summary": "<one-paragraph summary of the generated workflow>"\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.5,
                venture_id=venture_id,
                module_name=MODULE_NAME,
                metadata={"name": request.name},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            nodes = parsed.get("nodes", [])
            edges = parsed.get("edges", [])
            summary = parsed.get("summary", "")

            # Count step types
            human_steps = sum(1 for n in nodes if n.get("type") == "human")
            ai_steps = sum(1 for n in nodes if n.get("type") == "ai_agent")
            tool_steps = sum(1 for n in nodes if n.get("type") == "tool")

            # Persist as a new blueprint
            async with get_session(venture_id) as session:
                blueprint = WorkflowBlueprint(
                    venture_id=venture_id,
                    name=request.name,
                    description=request.process_description,
                    status="draft",
                    nodes=nodes,
                    edges=edges,
                    sla_config=None,
                    fallback_config=None,
                    version=1,
                )
                session.add(blueprint)
                await session.flush()
                blueprint_id = blueprint.id

            result = GenerateBlueprintResult(
                blueprint_id=blueprint_id,
                nodes=nodes,
                edges=edges,
                summary=summary,
                human_steps=human_steps,
                ai_steps=ai_steps,
                tool_steps=tool_steps,
            )

            await self._event_bus.publish(
                event_type="workflow.blueprint.generated",
                source_module=MODULE_NAME,
                payload={
                    "blueprint_id": blueprint_id,
                    "name": request.name,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "human_steps": human_steps,
                    "ai_steps": ai_steps,
                    "tool_steps": tool_steps,
                },
                venture_id=venture_id,
            )

            logger.info(
                "workflow_blueprint_generated",
                blueprint_id=blueprint_id,
                name=request.name,
                node_count=len(nodes),
                edge_count=len(edges),
                human_steps=human_steps,
                ai_steps=ai_steps,
                tool_steps=tool_steps,
            )

            return result

    # ------------------------------------------------------------------
    # Add Node / Edge
    # ------------------------------------------------------------------

    async def add_node(
        self, venture_id: str, blueprint_id: str, node: NodeSpec
    ) -> BlueprintResponse:
        """Add a node to an existing blueprint."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "add_node"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(WorkflowBlueprint).where(
                        WorkflowBlueprint.id == blueprint_id,
                        WorkflowBlueprint.venture_id == venture_id,
                        WorkflowBlueprint.deleted_at.is_(None),
                    )
                )
                blueprint = result.scalar_one()

                node_dict = {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type,
                    "config": node.config,
                    "inputs": node.inputs,
                    "outputs": node.outputs,
                    "sla_seconds": node.sla_seconds,
                }

                updated_nodes = list(blueprint.nodes)
                updated_nodes.append(node_dict)
                blueprint.nodes = updated_nodes

                await session.flush()
                response = _blueprint_to_response(blueprint)

            logger.info(
                "workflow_node_added",
                blueprint_id=blueprint_id,
                node_id=node.id,
                node_type=node.node_type,
            )

            return response

    async def add_edge(
        self, venture_id: str, blueprint_id: str, edge: EdgeSpec
    ) -> BlueprintResponse:
        """Add an edge to an existing blueprint."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "add_edge"):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(WorkflowBlueprint).where(
                        WorkflowBlueprint.id == blueprint_id,
                        WorkflowBlueprint.venture_id == venture_id,
                        WorkflowBlueprint.deleted_at.is_(None),
                    )
                )
                blueprint = result.scalar_one()

                edge_dict = {
                    "source_node_id": edge.source_node_id,
                    "target_node_id": edge.target_node_id,
                    "condition": edge.condition,
                }

                updated_edges = list(blueprint.edges)
                updated_edges.append(edge_dict)
                blueprint.edges = updated_edges

                await session.flush()
                response = _blueprint_to_response(blueprint)

            logger.info(
                "workflow_edge_added",
                blueprint_id=blueprint_id,
                source=edge.source_node_id,
                target=edge.target_node_id,
            )

            return response

    # ------------------------------------------------------------------
    # Validate Blueprint
    # ------------------------------------------------------------------

    async def validate(
        self, venture_id: str, request: ValidateBlueprintRequest
    ) -> ValidateBlueprintResult:
        """Validate a blueprint for structural correctness."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "validate",
            input_data={"blueprint_id": request.blueprint_id},
        ):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(WorkflowBlueprint).where(
                        WorkflowBlueprint.id == request.blueprint_id,
                        WorkflowBlueprint.venture_id == venture_id,
                        WorkflowBlueprint.deleted_at.is_(None),
                    )
                )
                blueprint = result.scalar_one()

            nodes = blueprint.nodes
            edges = blueprint.edges

            errors: list[str] = []
            warnings: list[str] = []

            # Build lookup structures
            node_ids = {n["id"] for n in nodes}
            _ = {n["id"]: n for n in nodes}  # node_map reserved for future use

            # Check for start and end nodes
            start_nodes = [n for n in nodes if n.get("type") == "start"]
            end_nodes = [n for n in nodes if n.get("type") == "end"]

            if len(start_nodes) == 0:
                errors.append("Workflow must have exactly one start node")
            elif len(start_nodes) > 1:
                errors.append(f"Workflow has {len(start_nodes)} start nodes; must have exactly one")

            if len(end_nodes) == 0:
                errors.append("Workflow must have exactly one end node")
            elif len(end_nodes) > 1:
                errors.append(f"Workflow has {len(end_nodes)} end nodes; must have exactly one")

            # Check edge references
            for edge in edges:
                if edge["source_node_id"] not in node_ids:
                    errors.append(f"Edge references unknown source node: {edge['source_node_id']}")
                if edge["target_node_id"] not in node_ids:
                    errors.append(f"Edge references unknown target node: {edge['target_node_id']}")

            # Build adjacency lists
            outgoing: dict[str, list[str]] = defaultdict(list)
            incoming: dict[str, list[str]] = defaultdict(list)
            for edge in edges:
                src = edge["source_node_id"]
                tgt = edge["target_node_id"]
                if src in node_ids and tgt in node_ids:
                    outgoing[src].append(tgt)
                    incoming[tgt].append(src)

            # Check reachability from start node (BFS)
            if start_nodes:
                start_id = start_nodes[0]["id"]
                reachable = _bfs_reachable(start_id, outgoing)
                unreachable = node_ids - reachable
                if unreachable:
                    errors.append(f"Nodes not reachable from start: {sorted(unreachable)}")

            # Check for cycles (topological sort attempt)
            has_cycle = _has_cycle(node_ids, outgoing)
            if has_cycle:
                errors.append("Workflow contains a cycle — directed acyclic graph required")

            # Check connectivity: every non-end node has at least one outgoing edge
            for node in nodes:
                nid = node["id"]
                ntype = node.get("type", "")
                if ntype != "end" and not outgoing.get(nid):
                    errors.append(f"Node '{nid}' ({node.get('name', '')}) has no outgoing edges")

            # Check connectivity: every non-start node has at least one incoming edge
            for node in nodes:
                nid = node["id"]
                ntype = node.get("type", "")
                if ntype != "start" and not incoming.get(nid):
                    errors.append(f"Node '{nid}' ({node.get('name', '')}) has no incoming edges")

            # Warn if SLAs missing on human steps
            for node in nodes:
                if node.get("type") == "human" and node.get("sla_seconds") is None:
                    warnings.append(f"Human step '{node['id']}' ({node.get('name', '')}) has no SLA configured")

            is_valid = len(errors) == 0

            summary = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "start_nodes": len(start_nodes),
                "end_nodes": len(end_nodes),
                "ai_agent_nodes": sum(1 for n in nodes if n.get("type") == "ai_agent"),
                "human_nodes": sum(1 for n in nodes if n.get("type") == "human"),
                "tool_nodes": sum(1 for n in nodes if n.get("type") == "tool"),
                "decision_nodes": sum(1 for n in nodes if n.get("type") == "decision"),
                "error_count": len(errors),
                "warning_count": len(warnings),
            }

            logger.info(
                "workflow_blueprint_validated",
                blueprint_id=request.blueprint_id,
                is_valid=is_valid,
                error_count=len(errors),
                warning_count=len(warnings),
            )

            return ValidateBlueprintResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                summary=summary,
            )

    # ------------------------------------------------------------------
    # Compile Blueprint
    # ------------------------------------------------------------------

    async def compile(
        self, venture_id: str, request: CompileRequest
    ) -> CompileResult:
        """Compile a validated blueprint into a Temporal workflow configuration."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "compile",
            input_data={"blueprint_id": request.blueprint_id},
        ):
            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(WorkflowBlueprint).where(
                        WorkflowBlueprint.id == request.blueprint_id,
                        WorkflowBlueprint.venture_id == venture_id,
                        WorkflowBlueprint.deleted_at.is_(None),
                    )
                )
                blueprint = result.scalar_one()

            nodes = blueprint.nodes
            edges = blueprint.edges

            # Extract required agents and tools
            agents_required: list[str] = []
            tools_required: list[str] = []

            for node in nodes:
                node_type = node.get("type", "")
                config = node.get("config", {})

                if node_type == "ai_agent":
                    agent_id = config.get("agent_id", node.get("name", "unknown_agent"))
                    if agent_id not in agents_required:
                        agents_required.append(agent_id)

                elif node_type == "tool":
                    tool_id = config.get("tool_id", node.get("name", "unknown_tool"))
                    if tool_id not in tools_required:
                        tools_required.append(tool_id)

            # Build Temporal workflow configuration
            # Build step execution order via topological sort
            outgoing: dict[str, list[str]] = defaultdict(list)
            for edge in edges:
                outgoing[edge["source_node_id"]].append(edge["target_node_id"])

            execution_order = _topological_sort(
                {n["id"] for n in nodes}, outgoing
            )

            steps = []
            for node_id in execution_order:
                node = next((n for n in nodes if n["id"] == node_id), None)
                if node is None:
                    continue
                node_type = node.get("type", "")
                if node_type in ("start", "end"):
                    continue

                config = node.get("config", {})
                step: dict[str, Any] = {
                    "step_id": node["id"],
                    "name": node.get("name", ""),
                    "type": node_type,
                    "config": config,
                    "dependencies": [
                        e["source_node_id"]
                        for e in edges
                        if e["target_node_id"] == node_id and _node_type(e["source_node_id"], nodes) not in ("start",)
                    ],
                }

                # Add timeout if specified
                sla = node.get("sla_seconds")
                if sla is not None:
                    step["timeout_seconds"] = sla
                elif config.get("timeout_seconds"):
                    step["timeout_seconds"] = config["timeout_seconds"]

                # Add approval requirement for human steps
                if config.get("approval_required"):
                    step["requires_approval"] = True

                steps.append(step)

            temporal_workflow_config: dict[str, Any] = {
                "workflow_name": blueprint.name,
                "version": blueprint.version,
                "steps": steps,
                "total_steps": len(steps),
                "agents_required": agents_required,
                "tools_required": tools_required,
            }

            compile_result = CompileResult(
                blueprint_id=request.blueprint_id,
                temporal_workflow_config=temporal_workflow_config,
                agents_required=agents_required,
                tools_required=tools_required,
            )

            await self._event_bus.publish(
                event_type="workflow.blueprint.compiled",
                source_module=MODULE_NAME,
                payload={
                    "blueprint_id": request.blueprint_id,
                    "step_count": len(steps),
                    "agents_required": agents_required,
                    "tools_required": tools_required,
                },
                venture_id=venture_id,
            )

            logger.info(
                "workflow_blueprint_compiled",
                blueprint_id=request.blueprint_id,
                step_count=len(steps),
                agent_count=len(agents_required),
                tool_count=len(tools_required),
            )

            return compile_result


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _blueprint_to_response(blueprint: WorkflowBlueprint) -> BlueprintResponse:
    """Convert a WorkflowBlueprint ORM model to a response schema."""
    return BlueprintResponse(
        id=blueprint.id,
        venture_id=blueprint.venture_id,
        name=blueprint.name,
        description=blueprint.description,
        status=blueprint.status,
        nodes=blueprint.nodes,
        edges=blueprint.edges,
        sla_config=blueprint.sla_config,
        fallback_config=blueprint.fallback_config,
        version=blueprint.version,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
    )


def _bfs_reachable(start_id: str, adjacency: dict[str, list[str]]) -> set[str]:
    """BFS to find all reachable nodes from a start node."""
    visited: set[str] = set()
    queue: deque[str] = deque([start_id])

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                queue.append(neighbor)

    return visited


def _has_cycle(node_ids: set[str], adjacency: dict[str, list[str]]) -> bool:
    """Detect cycles using Kahn's algorithm (topological sort attempt)."""
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    for src in adjacency:
        for tgt in adjacency[src]:
            if tgt in in_degree:
                in_degree[tgt] += 1

    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    processed = 0

    while queue:
        current = queue.popleft()
        processed += 1
        for neighbor in adjacency.get(current, []):
            if neighbor in in_degree:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    return processed < len(node_ids)


def _topological_sort(node_ids: set[str], adjacency: dict[str, list[str]]) -> list[str]:
    """Topological sort via Kahn's algorithm. Returns ordered node IDs."""
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    for src in adjacency:
        for tgt in adjacency[src]:
            if tgt in in_degree:
                in_degree[tgt] += 1

    queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        current = queue.popleft()
        result.append(current)
        for neighbor in adjacency.get(current, []):
            if neighbor in in_degree:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    return result


def _node_type(node_id: str, nodes: list[dict[str, Any]]) -> str:
    """Get the type of a node by ID."""
    for n in nodes:
        if n["id"] == node_id:
            return n.get("type", "")
    return ""


def _parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(
            "json_parse_failed",
            error=str(e),
            content_preview=text[:200],
        )
        return {}
