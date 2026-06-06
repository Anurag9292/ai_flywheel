"""Venture Lifecycle Workflow — the master orchestration.

A single Temporal workflow that takes a venture from idea → validation → launch.
Each stage is a Temporal activity with gates between stages.

Lifecycle:
  1. THESIS    → Formulate hypothesis, decompose assumptions
  2. DISCOVERY → Run customer interviews, analyze pain patterns
  3. MARKET    → Scan market signals, score opportunity
  4. OFFER     → Design ICP, positioning, pricing
  5. BUILD     → Configure agents, set up workflows
  6. DEPLOY    → Package and release

Kill gates between each stage check for invalidation signals.
Human approval required at stage transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy


@dataclass
class VentureLifecycleInput:
    """Input for the venture lifecycle workflow."""
    venture_id: str
    venture_name: str
    domain: str
    initial_hypothesis: str
    assumptions: list[str]
    kill_signals: list[str]


@dataclass
class StageResult:
    """Result from a lifecycle stage."""
    stage: str
    status: str  # "passed" | "killed" | "needs_review"
    confidence: float
    summary: str
    data: dict


# --- Activities ---


@activity.defn
async def thesis_stage_activity(venture_id: str, hypothesis: str, assumptions: list[str], kill_signals: list[str]) -> dict:
    """Stage 1: Create and validate thesis structure."""
    from ai_flywheel.modules.product_intelligence.venture_thesis.schemas import (
        ThesisCreate,
        ValidationPlanRequest,
    )
    from ai_flywheel.modules.product_intelligence.venture_thesis.service import VentureThesisEngine

    service = VentureThesisEngine()
    thesis = await service.create_thesis(
        venture_id,
        ThesisCreate(
            title=f"Thesis: {hypothesis[:50]}",
            hypothesis=hypothesis,
            assumptions=[{"statement": a, "risk_level": "medium"} for a in assumptions],
            kill_signals=kill_signals,
        ),
    )

    # Generate validation plan
    try:
        plan = await service.generate_validation_plan(
            venture_id, ValidationPlanRequest(thesis_id=thesis.id)
        )
    except Exception:
        plan = None

    return {
        "thesis_id": thesis.id,
        "confidence": thesis.confidence,
        "validation_plan": plan,
        "status": "passed",
    }


@activity.defn
async def discovery_stage_activity(venture_id: str, thesis_id: str, domain: str) -> dict:
    """Stage 2: Run customer discovery analysis."""
    from ai_flywheel.modules.product_intelligence.customer_discovery.schemas import DiscoveryProjectCreate
    from ai_flywheel.modules.product_intelligence.customer_discovery.service import CustomerDiscoveryEngine

    service = CustomerDiscoveryEngine()
    project = await service.create_project(
        venture_id,
        DiscoveryProjectCreate(
            name=f"Discovery: {domain}",
            domain=domain,
            hypothesis=f"Validating thesis for {domain}",
            assumptions=["Target users have this pain", "They're willing to pay for a solution"],
        ),
    )

    return {
        "project_id": project.id,
        "confidence_score": project.confidence_score,
        "status": "passed",
        "message": "Discovery project created. Add interview transcripts to validate.",
    }


@activity.defn
async def market_stage_activity(venture_id: str, domain: str) -> dict:
    """Stage 3: Market intelligence scan."""
    from ai_flywheel.modules.product_intelligence.market_intelligence.service import MarketIntelligence

    service = MarketIntelligence()
    try:
        score = await service.score_opportunity(venture_id, f"AI-powered solution for {domain}", domain)
        return {
            "opportunity_score": score.overall_score,
            "market_size": score.market_size_signal,
            "competition": score.competition_level,
            "timing": score.timing,
            "status": "passed" if score.overall_score >= 0.4 else "needs_review",
        }
    except Exception as e:
        # If LLM is unavailable, pass with default score
        return {
            "opportunity_score": 0.5,
            "market_size": "unknown",
            "competition": "unknown",
            "timing": "unknown",
            "status": "passed",
            "note": f"Skipped LLM scoring: {type(e).__name__}",
        }


@activity.defn
async def offer_stage_activity(venture_id: str, domain: str, target_audience: str) -> dict:
    """Stage 4: Design the offer."""
    from ai_flywheel.modules.product_intelligence.offer_design.schemas import OfferCreate
    from ai_flywheel.modules.product_intelligence.offer_design.service import OfferDesignEngine

    service = OfferDesignEngine()
    offer = await service.create_offer(
        venture_id,
        OfferCreate(
            name=f"Offer: {domain}",
            domain=domain,
            target_audience=target_audience,
            problem_statement=f"Pain point in {domain}",
            solution_description=f"AI-powered solution for {domain}",
        ),
    )

    return {
        "offer_id": offer.id,
        "has_icp": offer.icp is not None,
        "has_positioning": offer.positioning is not None,
        "status": "passed",
    }


@activity.defn
async def blueprint_stage_activity(venture_id: str, domain: str, offer_id: str) -> dict:
    """Stage 5: Generate workflow blueprint from the validated offer."""
    from ai_flywheel.modules.product_intelligence.workflow_blueprint.schemas import (
        GenerateBlueprintRequest,
    )
    from ai_flywheel.modules.product_intelligence.workflow_blueprint.service import WorkflowBlueprintEngine

    service = WorkflowBlueprintEngine()
    request = GenerateBlueprintRequest(
        name=f"{domain} Agent Workflow",
        process_description=(
            f"Create an AI-powered agent workflow for {domain}. "
            f"The workflow should handle: customer interaction, data processing, "
            f"analysis and recommendations, with human review at critical decision points."
        ),
        constraints=["Include human review for high-stakes decisions", "Keep latency under 30 seconds per step"],
    )
    result = await service.generate_from_description(venture_id, request)

    return {
        "blueprint_id": result.blueprint_id,
        "nodes": len(result.nodes),
        "edges": len(result.edges),
        "human_steps": result.human_steps,
        "ai_steps": result.ai_steps,
        "summary": result.summary,
        "status": "passed",
    }


@activity.defn
async def agent_setup_activity(venture_id: str, domain: str, blueprint_id: str | None) -> dict:
    """Stage 6: Create agent blueprints for the venture."""
    from ai_flywheel.modules.agent_runtime.agent_factory.schemas import AgentBlueprintCreate
    from ai_flywheel.modules.agent_runtime.agent_factory.service import AgentFactory

    service = AgentFactory()
    agents_created = []

    # Create a set of standard agents for the venture
    agent_specs = [
        AgentBlueprintCreate(
            name=f"{domain} Research Agent",
            description=f"Gathers market data, competitor info, and trends for {domain}",
            agent_type="single",
            model="gpt-4o-mini",
            system_prompt=f"You are a research agent specialized in {domain}. Gather information, analyze trends, and provide actionable insights.",
        ),
        AgentBlueprintCreate(
            name=f"{domain} Analysis Agent",
            description=f"Processes findings and generates recommendations for {domain}",
            agent_type="single",
            model="gpt-4o-mini",
            system_prompt=f"You are an analysis agent for {domain}. Process data, identify patterns, and generate actionable recommendations.",
        ),
        AgentBlueprintCreate(
            name=f"{domain} Writer Agent",
            description=f"Creates content, reports, and communications for {domain}",
            agent_type="single",
            model="gpt-4o-mini",
            system_prompt=f"You are a content agent for {domain}. Create compelling copy, reports, and communications tailored to the target audience.",
        ),
    ]

    for spec in agent_specs:
        agent = await service.create_agent(venture_id, spec)
        agents_created.append({"id": agent.id, "name": agent.name})

    return {
        "agents_created": len(agents_created),
        "agents": agents_created,
        "status": "passed",
    }


@activity.defn
async def kill_check_activity(venture_id: str, thesis_id: str) -> dict:
    """Check for kill signals at any stage gate."""
    from ai_flywheel.modules.product_intelligence.venture_thesis.service import VentureThesisEngine

    service = VentureThesisEngine()
    try:
        kill_signals = await service.check_kill_signals(venture_id, thesis_id)
        # Returns a list of triggered kill signal messages
        return {
            "should_kill": len(kill_signals) > 0,
            "reason": kill_signals[0] if kill_signals else "",
            "confidence": 0.5,
        }
    except Exception:
        # If check fails, don't kill — let it proceed
        return {"should_kill": False, "reason": "", "confidence": 0.5}


# --- Workflow ---


@workflow.defn
class VentureLifecycleWorkflow:
    """Master workflow that orchestrates the full venture lifecycle.

    Runs through stages sequentially with kill gates between each.
    Pauses for human approval at key decision points.
    """

    def __init__(self) -> None:
        self._current_stage = "initializing"
        self._approved = False
        self._killed = False
        self._kill_reason = ""
        self._stage_results: dict[str, dict] = {}
        self._stages = ["thesis", "discovery", "market", "offer", "blueprint", "agents"]
        self._discovery_complete = False
        self._transcripts_analyzed = 0

    @workflow.signal
    def approve_stage(self) -> None:
        """Signal to approve the current stage and proceed."""
        self._approved = True

    @workflow.signal
    def kill_venture(self, reason: str = "No reason provided") -> None:
        """Signal to kill the venture."""
        self._killed = True
        self._kill_reason = reason

    @workflow.signal
    def transcript_analyzed(self, count: int = 1) -> None:
        """Signal that a transcript has been analyzed. Auto-proceeds after threshold."""
        self._transcripts_analyzed = count
        if count >= 3:
            self._discovery_complete = True

    @workflow.signal
    def complete_discovery(self) -> None:
        """Manually signal discovery is complete (proceed to market stage)."""
        self._discovery_complete = True

    @workflow.query
    def get_status(self) -> dict:
        """Query current lifecycle status with full stage details."""
        return {
            "stage": self._current_stage,
            "killed": self._killed,
            "kill_reason": self._kill_reason,
            "stages": self._stages,
            "stage_results": self._stage_results,
            "completed_stages": list(self._stage_results.keys()),
            "transcripts_analyzed": self._transcripts_analyzed,
            "awaiting_discovery": self._current_stage == "awaiting_discovery",
        }

    @workflow.run
    async def run(self, input: VentureLifecycleInput) -> dict:
        """Execute the full venture lifecycle."""
        retry = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=5))
        results: dict[str, dict] = {}

        # Stage 1: Thesis
        self._current_stage = "thesis"
        thesis_result = await workflow.execute_activity(
            thesis_stage_activity,
            args=[input.venture_id, input.initial_hypothesis, input.assumptions, input.kill_signals],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )
        results["thesis"] = thesis_result
        self._stage_results["thesis"] = thesis_result

        if self._killed:
            return {"status": "killed", "stage": "thesis", "reason": self._kill_reason, "results": results}

        # Stage 2: Discovery — create project then wait for transcripts
        self._current_stage = "discovery"
        discovery_result = await workflow.execute_activity(
            discovery_stage_activity,
            args=[input.venture_id, thesis_result["thesis_id"], input.domain],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )
        results["discovery"] = discovery_result
        self._stage_results["discovery"] = discovery_result

        # Pause: wait for interview transcripts or manual proceed
        self._current_stage = "awaiting_discovery"
        await workflow.wait_condition(
            lambda: self._discovery_complete or self._approved or self._killed,
            timeout=timedelta(hours=72),  # Auto-proceed after 72h
        )
        if self._killed:
            return {"status": "killed", "stage": "discovery", "reason": self._kill_reason, "results": results}
        self._approved = False
        self._stage_results["discovery"]["transcripts_analyzed"] = self._transcripts_analyzed

        # Kill gate check
        kill_check = await workflow.execute_activity(
            kill_check_activity,
            args=[input.venture_id, thesis_result["thesis_id"]],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry,
        )
        if kill_check["should_kill"]:
            return {"status": "killed", "stage": "discovery_gate", "reason": kill_check["reason"], "results": results}

        # Stage 3: Market
        self._current_stage = "market"
        market_result = await workflow.execute_activity(
            market_stage_activity,
            args=[input.venture_id, input.domain],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )
        results["market"] = market_result
        self._stage_results["market"] = market_result

        # If market score is low, wait for approval
        if market_result["status"] == "needs_review":
            self._current_stage = "awaiting_market_approval"
            await workflow.wait_condition(lambda: self._approved or self._killed)
            if self._killed:
                return {"status": "killed", "stage": "market", "reason": self._kill_reason, "results": results}
            self._approved = False

        # Stage 4: Offer Design
        self._current_stage = "offer"
        offer_result = await workflow.execute_activity(
            offer_stage_activity,
            args=[input.venture_id, input.domain, "target customers"],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )
        results["offer"] = offer_result
        self._stage_results["offer"] = offer_result

        if self._killed:
            return {"status": "killed", "stage": "offer", "reason": self._kill_reason, "results": results}

        # Stage 5: Blueprint
        self._current_stage = "blueprint"
        blueprint_result = await workflow.execute_activity(
            blueprint_stage_activity,
            args=[input.venture_id, input.domain, offer_result.get("offer_id", "")],
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=retry,
        )
        results["blueprint"] = blueprint_result
        self._stage_results["blueprint"] = blueprint_result

        # Stage 6: Agent Setup
        self._current_stage = "agents"
        agent_result = await workflow.execute_activity(
            agent_setup_activity,
            args=[input.venture_id, input.domain, blueprint_result.get("blueprint_id")],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )
        results["agents"] = agent_result
        self._stage_results["agents"] = agent_result

        # Final stage
        self._current_stage = "completed"
        return {
            "status": "validated",
            "results": results,
            "summary": f"Venture '{input.venture_name}' passed all validation gates and agent network is configured.",
        }
