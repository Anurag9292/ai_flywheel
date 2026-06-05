# ruff: noqa: E501
"""Offer Design Engine — Service layer.

Orchestrates LLM-powered offer design: ICP profiling, positioning strategy,
pricing optimization, landing page copy generation, and objection handling.
"""

from __future__ import annotations

import json
import re

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import Offer
from .schemas import (
    ICPRequest,
    ICPResult,
    LandingCopyRequest,
    LandingCopyResult,
    OfferCreate,
    OfferResponse,
    PositioningRequest,
    PositioningResult,
    PricingRequest,
    PricingResult,
)

logger = structlog.get_logger()

MODULE_NAME = "offer_design"


def _parse_json_response(text: str) -> dict | list:
    """Safely parse JSON from LLM response, handling code fences."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return json.loads(cleaned)


class OfferDesignEngine:
    """AI-powered offer design engine for ICP, positioning, pricing, and copy."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Offer CRUD
    # ------------------------------------------------------------------

    async def create_offer(
        self, venture_id: str, data: OfferCreate
    ) -> OfferResponse:
        """Create a new offer and auto-generate initial ICP + positioning via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "create_offer",
            input_data={"name": data.name, "domain": data.domain},
        ) as span:
            # Persist draft offer
            async with get_session(venture_id) as session:
                offer = Offer(
                    venture_id=venture_id,
                    name=data.name,
                    status="draft",
                    version=1,
                )
                session.add(offer)
                await session.flush()
                offer_id = offer.id

            # Auto-generate ICP
            await self.generate_icp(
                venture_id,
                ICPRequest(
                    offer_id=offer_id,
                    domain=data.domain,
                    initial_description=f"Target audience: {data.target_audience}. Problem: {data.problem_statement}. Solution: {data.solution_description}",
                ),
            )

            # Auto-generate positioning
            await self.generate_positioning(
                venture_id,
                PositioningRequest(
                    offer_id=offer_id,
                    domain=data.domain,
                    competitors=[],
                    differentiators=[],
                ),
            )

            # Load final state
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                response = OfferResponse.model_validate(offer)

            span.output_data = {"offer_id": offer_id}

            await self._event_bus.publish(
                event_type="offer.created",
                source_module=MODULE_NAME,
                payload={
                    "offer_id": offer_id,
                    "name": data.name,
                    "domain": data.domain,
                },
                venture_id=venture_id,
            )

            logger.info(
                "offer_created",
                venture_id=venture_id,
                offer_id=offer_id,
                name=data.name,
            )
            return response

    async def get_offer(self, venture_id: str, offer_id: str) -> OfferResponse:
        """Retrieve a single offer by ID."""
        async with self._tracer.span(MODULE_NAME, "get_offer"):
            async with get_session(venture_id) as session:
                stmt = (
                    select(Offer)
                    .where(Offer.id == offer_id)
                    .where(Offer.venture_id == venture_id)
                    .where(Offer.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                offer = result.scalar_one()
                return OfferResponse.model_validate(offer)

    async def list_offers(self, venture_id: str) -> list[OfferResponse]:
        """List all offers for a venture."""
        async with self._tracer.span(MODULE_NAME, "list_offers"):
            async with get_session(venture_id) as session:
                stmt = (
                    select(Offer)
                    .where(Offer.venture_id == venture_id)
                    .where(Offer.deleted_at.is_(None))
                    .order_by(Offer.created_at.desc())
                )
                result = await session.execute(stmt)
                offers = result.scalars().all()
                return [OfferResponse.model_validate(o) for o in offers]

    # ------------------------------------------------------------------
    # ICP Generation
    # ------------------------------------------------------------------

    async def generate_icp(
        self, venture_id: str, request: ICPRequest
    ) -> ICPResult:
        """Generate an Ideal Customer Profile via LLM analysis."""
        async with self._tracer.span(
            MODULE_NAME,
            "generate_icp",
            input_data={"offer_id": request.offer_id, "domain": request.domain},
        ) as span:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a world-class product strategist specializing in customer segmentation and "
                        "ideal customer profiling. Generate a detailed Ideal Customer Profile (ICP) based on "
                        "the provided domain and target description.\n\n"
                        "Your ICP must include behavioral, firmographic, and psychographic attributes that "
                        "are specific, actionable, and useful for targeting.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Domain: {request.domain}\n"
                        f"Description: {request.initial_description}\n\n"
                        "Generate a comprehensive Ideal Customer Profile in this exact JSON format:\n"
                        "{\n"
                        '  "behavioral": {\n'
                        '    "buying_triggers": ["trigger1", "trigger2", ...],\n'
                        '    "decision_process": "description of how they decide",\n'
                        '    "usage_patterns": ["pattern1", "pattern2", ...],\n'
                        '    "pain_indicators": ["indicator1", "indicator2", ...]\n'
                        "  },\n"
                        '  "firmographic": {\n'
                        '    "company_size": "range or description",\n'
                        '    "industry": ["industry1", "industry2"],\n'
                        '    "revenue_range": "range",\n'
                        '    "tech_stack": ["tech1", "tech2"],\n'
                        '    "growth_stage": "stage description"\n'
                        "  },\n"
                        '  "psychographic": {\n'
                        '    "values": ["value1", "value2"],\n'
                        '    "frustrations": ["frustration1", "frustration2"],\n'
                        '    "aspirations": ["aspiration1", "aspiration2"],\n'
                        '    "risk_tolerance": "low|medium|high",\n'
                        '    "innovation_mindset": "description"\n'
                        "  },\n"
                        '  "summary": "One-paragraph ICP summary"\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.4,
                venture_id=venture_id,
                module_name=MODULE_NAME,
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            # Update offer with ICP
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                offer.icp = parsed

            result = ICPResult(offer_id=request.offer_id, icp=parsed)

            await self._event_bus.publish(
                event_type="offer.icp.generated",
                source_module=MODULE_NAME,
                payload={"offer_id": request.offer_id, "domain": request.domain},
                venture_id=venture_id,
            )

            logger.info(
                "icp_generated",
                venture_id=venture_id,
                offer_id=request.offer_id,
                domain=request.domain,
            )
            return result

    # ------------------------------------------------------------------
    # Positioning Generation
    # ------------------------------------------------------------------

    async def generate_positioning(
        self, venture_id: str, request: PositioningRequest
    ) -> PositioningResult:
        """Generate competitive positioning strategy via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "generate_positioning",
            input_data={"offer_id": request.offer_id, "domain": request.domain},
        ) as span:
            # Load offer context for richer prompting
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                icp_context = json.dumps(offer.icp) if offer.icp else "Not yet defined"

            competitors_section = ""
            if request.competitors:
                competitors_section = f"\nKnown competitors: {', '.join(request.competitors)}"

            differentiators_section = ""
            if request.differentiators:
                differentiators_section = f"\nKey differentiators: {', '.join(request.differentiators)}"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a positioning strategist with deep expertise in competitive strategy and "
                        "brand differentiation. Create a clear, defensible positioning strategy.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Domain: {request.domain}\n"
                        f"Offer: {offer.name}\n"
                        f"ICP Context: {icp_context}\n"
                        f"{competitors_section}"
                        f"{differentiators_section}\n\n"
                        "Generate a positioning strategy in this exact JSON format:\n"
                        "{\n"
                        '  "category": "The market category this offer competes in",\n'
                        '  "value_proposition": "Clear, concise value proposition statement",\n'
                        '  "competitive_frame": {\n'
                        '    "frame_of_reference": "What buyers compare this to",\n'
                        '    "key_differentiators": ["diff1", "diff2", "diff3"],\n'
                        '    "defensibility": "Why this position is hard to copy"\n'
                        "  },\n"
                        '  "positioning_statement": "For [target] who [need], [product] is a [category] that [benefit]. Unlike [alternative], we [key differentiator].",\n'
                        '  "messaging_pillars": ["pillar1", "pillar2", "pillar3"],\n'
                        '  "proof_points": ["proof1", "proof2", "proof3"]\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.4,
                venture_id=venture_id,
                module_name=MODULE_NAME,
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            # Update offer with positioning
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                offer.positioning = parsed

            positioning_result = PositioningResult(
                offer_id=request.offer_id, positioning=parsed
            )

            await self._event_bus.publish(
                event_type="offer.positioning.generated",
                source_module=MODULE_NAME,
                payload={"offer_id": request.offer_id, "domain": request.domain},
                venture_id=venture_id,
            )

            logger.info(
                "positioning_generated",
                venture_id=venture_id,
                offer_id=request.offer_id,
                domain=request.domain,
            )
            return positioning_result

    # ------------------------------------------------------------------
    # Pricing Generation
    # ------------------------------------------------------------------

    async def generate_pricing(
        self, venture_id: str, request: PricingRequest
    ) -> PricingResult:
        """Generate pricing strategy with tiers and rationale via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "generate_pricing",
            input_data={"offer_id": request.offer_id, "target_segment": request.target_segment},
        ) as span:
            # Load offer for context
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                positioning_context = json.dumps(offer.positioning) if offer.positioning else "Not yet defined"
                icp_context = json.dumps(offer.icp) if offer.icp else "Not yet defined"

            competitor_pricing_section = ""
            if request.competitor_pricing:
                competitor_pricing_section = f"\nCompetitor pricing data: {json.dumps(request.competitor_pricing)}"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a pricing strategist with expertise in SaaS/product pricing, value-based "
                        "pricing, and competitive positioning. Design a pricing strategy that maximizes "
                        "revenue while aligning with the target segment's willingness to pay.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Offer: {offer.name}\n"
                        f"Value delivered: {request.value_delivered}\n"
                        f"Target segment: {request.target_segment}\n"
                        f"ICP: {icp_context}\n"
                        f"Positioning: {positioning_context}\n"
                        f"{competitor_pricing_section}\n\n"
                        "Design a pricing strategy in this exact JSON format:\n"
                        "{\n"
                        '  "model": "subscription|usage_based|tiered|freemium|one_time|hybrid",\n'
                        '  "rationale": "Why this pricing model fits",\n'
                        '  "tiers": [\n'
                        "    {\n"
                        '      "name": "Tier name",\n'
                        '      "price": "$X/period",\n'
                        '      "target_user": "Who this tier is for",\n'
                        '      "features": ["feature1", "feature2"],\n'
                        '      "limits": "Any usage limits"\n'
                        "    }\n"
                        "  ],\n"
                        '  "price_points": {\n'
                        '    "anchor_price": "$X",\n'
                        '    "recommended_price": "$X",\n'
                        '    "entry_price": "$X"\n'
                        "  },\n"
                        '  "value_metrics": ["metric1", "metric2"],\n'
                        '  "psychological_triggers": ["trigger1", "trigger2"],\n'
                        '  "discount_strategy": "How and when to discount"\n'
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.4,
                venture_id=venture_id,
                module_name=MODULE_NAME,
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            # Update offer with pricing
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                offer.pricing = parsed

            pricing_result = PricingResult(offer_id=request.offer_id, pricing=parsed)

            await self._event_bus.publish(
                event_type="offer.pricing.generated",
                source_module=MODULE_NAME,
                payload={"offer_id": request.offer_id, "target_segment": request.target_segment},
                venture_id=venture_id,
            )

            logger.info(
                "pricing_generated",
                venture_id=venture_id,
                offer_id=request.offer_id,
                target_segment=request.target_segment,
            )
            return pricing_result

    # ------------------------------------------------------------------
    # Landing Page Copy Generation
    # ------------------------------------------------------------------

    async def generate_landing_copy(
        self, venture_id: str, request: LandingCopyRequest
    ) -> LandingCopyResult:
        """Generate conversion-optimized landing page copy via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "generate_landing_copy",
            input_data={"offer_id": request.offer_id, "persona": request.persona, "tone": request.tone},
        ) as span:
            # Load offer for full context
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()

            offer_context = {
                "name": offer.name,
                "icp": offer.icp or {},
                "positioning": offer.positioning or {},
                "pricing": offer.pricing or {},
            }

            persona_section = ""
            if request.persona:
                persona_section = f"\nTarget persona for this copy: {request.persona}"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an elite conversion copywriter who creates landing pages that convert. "
                        "You combine direct-response principles with modern SaaS copywriting best practices. "
                        f"Write in a {request.tone} tone.\n\n"
                        "Your copy must be specific, benefit-driven, and create urgency without being pushy.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Offer context: {json.dumps(offer_context)}\n"
                        f"{persona_section}\n\n"
                        "Generate complete landing page copy in this exact JSON format:\n"
                        "{\n"
                        '  "headline": "Primary headline (max 10 words, benefit-driven)",\n'
                        '  "subheadline": "Supporting subheadline expanding on the promise",\n'
                        '  "hero_body": "2-3 sentences of hero section body copy",\n'
                        '  "benefits": ["benefit1 with specifics", "benefit2 with specifics", "benefit3", "benefit4"],\n'
                        '  "social_proof_frame": "Framework for social proof section (e.g. testimonial angle, stats to highlight)",\n'
                        '  "cta_primary": "Primary call-to-action text",\n'
                        '  "cta_secondary": "Secondary/softer CTA text",\n'
                        '  "full_page_structure": [\n'
                        "    {\n"
                        '      "section": "section_name",\n'
                        '      "purpose": "what this section achieves",\n'
                        '      "content": "copy for this section"\n'
                        "    }\n"
                        "  ]\n"
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.7,
                venture_id=venture_id,
                module_name=MODULE_NAME,
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            # Update offer messaging
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == request.offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                offer.messaging = {
                    "headline": parsed.get("headline", ""),
                    "subheadline": parsed.get("subheadline", ""),
                    "benefits": parsed.get("benefits", []),
                    "cta_primary": parsed.get("cta_primary", ""),
                    "cta_secondary": parsed.get("cta_secondary", ""),
                }

            copy_result = LandingCopyResult(
                offer_id=request.offer_id,
                headline=parsed.get("headline", ""),
                subheadline=parsed.get("subheadline", ""),
                hero_body=parsed.get("hero_body", ""),
                benefits=parsed.get("benefits", []),
                social_proof_frame=parsed.get("social_proof_frame", ""),
                cta_primary=parsed.get("cta_primary", ""),
                cta_secondary=parsed.get("cta_secondary", ""),
                full_page_structure=parsed.get("full_page_structure", []),
            )

            await self._event_bus.publish(
                event_type="offer.copy.generated",
                source_module=MODULE_NAME,
                payload={"offer_id": request.offer_id, "tone": request.tone},
                venture_id=venture_id,
            )

            logger.info(
                "landing_copy_generated",
                venture_id=venture_id,
                offer_id=request.offer_id,
                tone=request.tone,
            )
            return copy_result

    # ------------------------------------------------------------------
    # Objection Rebuttals
    # ------------------------------------------------------------------

    async def generate_objection_rebuttals(
        self, venture_id: str, offer_id: str, objections: list[str]
    ) -> list[dict]:
        """Generate persuasive rebuttals for common objections via LLM."""
        async with self._tracer.span(
            MODULE_NAME,
            "generate_objection_rebuttals",
            input_data={"offer_id": offer_id, "objection_count": len(objections)},
        ) as span:
            # Load offer context
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()

            offer_context = {
                "name": offer.name,
                "positioning": offer.positioning or {},
                "pricing": offer.pricing or {},
            }

            objections_text = "\n".join(f"- {obj}" for obj in objections)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a sales psychology expert who crafts empathetic yet persuasive objection "
                        "rebuttals. Each rebuttal should acknowledge the concern, reframe it, and provide "
                        "a compelling response that moves the prospect forward.\n\n"
                        "Respond with valid JSON only, no markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Offer context: {json.dumps(offer_context)}\n\n"
                        f"Objections to address:\n{objections_text}\n\n"
                        "Generate rebuttals in this exact JSON format:\n"
                        "{\n"
                        '  "rebuttals": [\n'
                        "    {\n"
                        '      "objection": "The original objection",\n'
                        '      "type": "price|trust|timing|need|competition|complexity",\n'
                        '      "acknowledge": "Empathetic acknowledgment",\n'
                        '      "reframe": "How to reframe the concern",\n'
                        '      "response": "Full rebuttal response",\n'
                        '      "proof_point": "Evidence or example to support"\n'
                        "    }\n"
                        "  ]\n"
                        "}"
                    ),
                },
            ]

            llm_response = await generate(
                messages=messages,
                model="gpt-4o-mini",
                temperature=0.7,
                venture_id=venture_id,
                module_name=MODULE_NAME,
            )

            span.set_cost(
                llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)
            rebuttals = parsed.get("rebuttals", []) if isinstance(parsed, dict) else parsed

            # Update offer with rebuttals
            async with get_session(venture_id) as session:
                stmt = select(Offer).where(Offer.id == offer_id)
                result = await session.execute(stmt)
                offer = result.scalar_one()
                offer.objection_rebuttals = rebuttals

            await self._event_bus.publish(
                event_type="offer.copy.generated",
                source_module=MODULE_NAME,
                payload={"offer_id": offer_id, "rebuttals_count": len(rebuttals)},
                venture_id=venture_id,
            )

            logger.info(
                "objection_rebuttals_generated",
                venture_id=venture_id,
                offer_id=offer_id,
                rebuttals_count=len(rebuttals),
            )
            return rebuttals
