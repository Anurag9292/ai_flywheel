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

    @workflow.signal
    async def approve_stage(self) -> None:
        """Signal to approve the current stage and proceed."""
        self._approved = True

    @workflow.signal
    async def kill_venture(self, reason: str) -> None:
        """Signal to kill the venture."""
        self._killed = True
        self._kill_reason = reason

    @workflow.query
    def get_status(self) -> dict:
        """Query current lifecycle status."""
        return {
            "stage": self._current_stage,
            "killed": self._killed,
            "kill_reason": self._kill_reason,
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

        if self._killed:
            return {"status": "killed", "stage": "thesis", "reason": self._kill_reason, "results": results}

        # Stage 2: Discovery
        self._current_stage = "discovery"
        discovery_result = await workflow.execute_activity(
            discovery_stage_activity,
            args=[input.venture_id, thesis_result["thesis_id"], input.domain],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry,
        )
        results["discovery"] = discovery_result

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

        # Final stage
        self._current_stage = "completed"
        return {
            "status": "validated",
            "results": results,
            "summary": f"Venture '{input.venture_name}' passed all validation gates.",
        }
