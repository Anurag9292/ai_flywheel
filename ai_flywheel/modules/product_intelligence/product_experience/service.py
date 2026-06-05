# ruff: noqa: E501
"""Product Experience Engine — designs AI-native product experiences.

This module assists in product experience design by:
1. Creating and managing product specifications with persona models
2. LLM-powered multi-criteria feature prioritization
3. Recommending AI interaction patterns per capability
4. Generating screen architecture and information hierarchy
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.llm import generate
from ai_flywheel.core.traces import get_tracer

from .models import ProductSpec
from .schemas import (
    AIInteractionRequest,
    AIInteractionResult,
    FeaturePrioritizationRequest,
    FeaturePrioritizationResult,
    ProductSpecCreate,
    ProductSpecResponse,
    ScreenArchitectureRequest,
    ScreenArchitectureResult,
)

logger = structlog.get_logger()

MODULE_NAME = "product_experience"


class ProductExperienceEngine:
    """Orchestrates AI-native product experience design workflows."""

    def __init__(self) -> None:
        self._tracer = get_tracer()
        self._event_bus = get_event_bus()

    # ------------------------------------------------------------------
    # Product Spec CRUD
    # ------------------------------------------------------------------

    async def create_product_spec(
        self, venture_id: str, data: ProductSpecCreate
    ) -> ProductSpecResponse:
        """Create a new product specification with initial persona and capability seeds."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "create_product_spec"):
            # Seed personas from target_personas list
            personas = [
                {"name": persona, "goals": [], "pain_points": [], "context": ""}
                for persona in data.target_personas
            ]

            # Seed features from core_capabilities
            features = [
                {"name": cap, "priority": "medium", "effort": "unknown", "impact": "unknown", "status": "proposed"}
                for cap in data.core_capabilities
            ]

            async with get_session(venture_id) as session:
                product = ProductSpec(
                    venture_id=venture_id,
                    name=data.name,
                    description=data.description,
                    personas=personas,
                    features=features,
                    ai_interaction_patterns=[],
                    screen_architecture=None,
                    ux_flows=[],
                    status="draft",
                )
                session.add(product)
                await session.flush()

                response = _spec_to_response(product)

            await self._event_bus.publish(
                event_type="product.spec.created",
                source_module=MODULE_NAME,
                payload={"product_id": response.id, "name": data.name},
                venture_id=venture_id,
            )

            logger.info(
                "product_spec_created",
                product_id=response.id,
                venture_id=venture_id,
                name=data.name,
                persona_count=len(personas),
                feature_count=len(features),
            )

            return response

    async def get_product_spec(
        self, venture_id: str, product_id: str
    ) -> ProductSpecResponse:
        """Retrieve a product specification by ID."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(ProductSpec).where(
                    ProductSpec.id == product_id,
                    ProductSpec.venture_id == venture_id,
                    ProductSpec.deleted_at.is_(None),
                )
            )
            product = result.scalar_one()
            return _spec_to_response(product)

    async def list_product_specs(
        self, venture_id: str
    ) -> list[ProductSpecResponse]:
        """List all product specifications for a venture."""
        self._tracer.set_venture_context(venture_id)

        async with get_session(venture_id) as session:
            result = await session.execute(
                select(ProductSpec).where(
                    ProductSpec.venture_id == venture_id,
                    ProductSpec.deleted_at.is_(None),
                ).order_by(ProductSpec.created_at.desc())
            )
            products = result.scalars().all()
            return [_spec_to_response(p) for p in products]

    # ------------------------------------------------------------------
    # Feature Prioritization (LLM-powered)
    # ------------------------------------------------------------------

    async def prioritize_features(
        self, venture_id: str, request: FeaturePrioritizationRequest
    ) -> FeaturePrioritizationResult:
        """Prioritize features using LLM-powered multi-criteria scoring."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "prioritize_features",
            input_data={"product_id": request.product_id, "feature_count": len(request.features)},
        ) as span:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a senior product strategist specializing in AI-native products. "
                        "Your job is to prioritize features using multi-criteria analysis.\n\n"
                        "For each feature, score on these dimensions (1-10):\n"
                        "- impact: How much does this move the north star metric?\n"
                        "- effort: Engineering complexity (1=trivial, 10=massive)\n"
                        "- risk: Technical and market risk (1=certain, 10=highly uncertain)\n"
                        "- ai_leverage: How much can AI amplify this feature's value?\n\n"
                        "Compute a weighted priority score: (impact * 3 + ai_leverage * 2 - effort - risk) / 5\n"
                        "Sort features by priority score descending.\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Prioritize the following features for optimal impact on the north star metric.\n\n"
                        f"North Star Metric: {request.north_star_metric}\n\n"
                        f"Features to prioritize:\n"
                        + json.dumps(request.features, indent=2)
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "prioritized_features": [\n'
                        "    {\n"
                        '      "name": "<feature name>",\n'
                        '      "impact": <1-10>,\n'
                        '      "effort": <1-10>,\n'
                        '      "risk": <1-10>,\n'
                        '      "ai_leverage": <1-10>,\n'
                        '      "priority_score": <computed score>,\n'
                        '      "priority": "<critical|high|medium|low>",\n'
                        '      "recommendation": "<one-line recommendation>"\n'
                        "    }\n"
                        "  ],\n"
                        '  "rationale": "<2-3 sentence overall prioritization strategy explanation>"\n'
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
                metadata={"product_id": request.product_id},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            result = FeaturePrioritizationResult(
                product_id=request.product_id,
                prioritized_features=parsed.get("prioritized_features", []),
                rationale=parsed.get("rationale", ""),
            )

            # Update product spec features with prioritization results
            async with get_session(venture_id) as session:
                db_result = await session.execute(
                    select(ProductSpec).where(
                        ProductSpec.id == request.product_id,
                        ProductSpec.venture_id == venture_id,
                    )
                )
                product = db_result.scalar_one()
                product.features = result.prioritized_features

            await self._event_bus.publish(
                event_type="product.features.prioritized",
                source_module=MODULE_NAME,
                payload={
                    "product_id": request.product_id,
                    "feature_count": len(result.prioritized_features),
                    "north_star_metric": request.north_star_metric,
                },
                venture_id=venture_id,
            )

            logger.info(
                "features_prioritized",
                product_id=request.product_id,
                feature_count=len(result.prioritized_features),
                north_star_metric=request.north_star_metric,
            )

            return result

    # ------------------------------------------------------------------
    # AI Interaction Pattern Recommendation
    # ------------------------------------------------------------------

    async def recommend_ai_patterns(
        self, venture_id: str, request: AIInteractionRequest
    ) -> AIInteractionResult:
        """Recommend AI interaction modality for each capability."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "recommend_ai_patterns",
            input_data={"product_id": request.product_id, "capability_count": len(request.capabilities)},
        ) as span:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI UX architect who designs human-AI interaction patterns. "
                        "For each product capability, recommend the optimal interaction modality.\n\n"
                        "Available modalities:\n"
                        "- chat: Conversational interface for exploratory, multi-turn tasks\n"
                        "- queue: Async task queue where AI works in background, user reviews results\n"
                        "- dashboard: AI surfaces insights proactively in monitoring views\n"
                        "- copilot: AI assists inline within user's existing workflow\n"
                        "- autonomous: AI acts independently with minimal human oversight\n\n"
                        "For each capability, also assess the autonomy level (1-5):\n"
                        "1 = Human does everything, AI suggests\n"
                        "2 = AI drafts, human approves every action\n"
                        "3 = AI acts with periodic human review\n"
                        "4 = AI acts independently, human reviews exceptions\n"
                        "5 = Fully autonomous, human sets policy only\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Recommend AI interaction patterns for the following capabilities.\n\n"
                        "Capabilities:\n"
                        + "\n".join(f"- {cap}" for cap in request.capabilities)
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "patterns": [\n'
                        "    {\n"
                        '      "capability": "<capability name>",\n'
                        '      "recommended_pattern": "<chat|queue|dashboard|copilot|autonomous>",\n'
                        '      "autonomy_level": <1-5>,\n'
                        '      "rationale": "<one-line explanation of why this pattern fits>"\n'
                        "    }\n"
                        "  ]\n"
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
                metadata={"product_id": request.product_id},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            result = AIInteractionResult(
                product_id=request.product_id,
                patterns=parsed.get("patterns", []),
            )

            # Persist patterns to product spec
            async with get_session(venture_id) as session:
                db_result = await session.execute(
                    select(ProductSpec).where(
                        ProductSpec.id == request.product_id,
                        ProductSpec.venture_id == venture_id,
                    )
                )
                product = db_result.scalar_one()
                product.ai_interaction_patterns = result.patterns

            await self._event_bus.publish(
                event_type="product.patterns.recommended",
                source_module=MODULE_NAME,
                payload={
                    "product_id": request.product_id,
                    "pattern_count": len(result.patterns),
                },
                venture_id=venture_id,
            )

            logger.info(
                "ai_patterns_recommended",
                product_id=request.product_id,
                pattern_count=len(result.patterns),
            )

            return result

    # ------------------------------------------------------------------
    # Screen Architecture Generation
    # ------------------------------------------------------------------

    async def generate_screen_architecture(
        self, venture_id: str, request: ScreenArchitectureRequest
    ) -> ScreenArchitectureResult:
        """Generate UI screen architecture from user goals."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(
            MODULE_NAME,
            "generate_screen_architecture",
            input_data={"product_id": request.product_id, "goal_count": len(request.user_goals)},
        ) as span:
            # Fetch product context for richer prompting
            async with get_session(venture_id) as session:
                db_result = await session.execute(
                    select(ProductSpec).where(
                        ProductSpec.id == request.product_id,
                        ProductSpec.venture_id == venture_id,
                    )
                )
                product = db_result.scalar_one()

            personas_context = ""
            if product.personas:
                personas_context = "\nTarget Personas:\n" + "\n".join(
                    f"- {p.get('name', 'Unknown')}" for p in product.personas
                )

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a senior UX architect specializing in AI-native product design. "
                        "Your job is to design screen architectures that elegantly surface AI capabilities "
                        "while maintaining clarity and discoverability.\n\n"
                        "Design principles:\n"
                        "1. Progressive disclosure — don't overwhelm; reveal complexity gradually\n"
                        "2. AI transparency — users should understand what AI is doing and why\n"
                        "3. Human control — every AI action should be reviewable and reversible\n"
                        "4. Context preservation — maintain user's mental model across screens\n"
                        "5. Goal-oriented navigation — organize around what users want to accomplish\n\n"
                        "Respond ONLY with valid JSON in the specified format."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Generate a screen architecture for the following product.\n\n"
                        f"Product: {product.name}\n"
                        f"Description: {product.description}\n"
                        + personas_context
                        + "\n\nUser Goals to support:\n"
                        + "\n".join(f"- {goal}" for goal in request.user_goals)
                        + "\n\nRespond with JSON:\n"
                        "{\n"
                        '  "screens": [\n'
                        "    {\n"
                        '      "id": "<screen_id>",\n'
                        '      "name": "<Screen Name>",\n'
                        '      "purpose": "<what this screen accomplishes>",\n'
                        '      "primary_actions": ["<key actions available>"],\n'
                        '      "ai_features": ["<AI capabilities surfaced here>"],\n'
                        '      "components": ["<major UI components>"]\n'
                        "    }\n"
                        "  ],\n"
                        '  "navigation": {\n'
                        '    "type": "<tabs|sidebar|hub-spoke|wizard>",\n'
                        '    "primary_items": ["<top-level nav items>"],\n'
                        '    "secondary_items": ["<secondary/contextual nav>"]\n'
                        "  },\n"
                        '  "information_hierarchy": ["<ordered list from most to least important info>"]\n'
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
                metadata={"product_id": request.product_id},
            )

            span.set_cost(
                cost_usd=llm_response.cost_usd,
                tokens_input=llm_response.tokens_input,
                tokens_output=llm_response.tokens_output,
                model=llm_response.model,
            )

            parsed = _parse_json_response(llm_response.content)

            result = ScreenArchitectureResult(
                product_id=request.product_id,
                screens=parsed.get("screens", []),
                navigation=parsed.get("navigation", {}),
                information_hierarchy=parsed.get("information_hierarchy", []),
            )

            # Persist screen architecture to product spec
            async with get_session(venture_id) as session:
                db_result = await session.execute(
                    select(ProductSpec).where(
                        ProductSpec.id == request.product_id,
                        ProductSpec.venture_id == venture_id,
                    )
                )
                product = db_result.scalar_one()
                product.screen_architecture = {
                    "screens": result.screens,
                    "navigation": result.navigation,
                    "information_hierarchy": result.information_hierarchy,
                }

            logger.info(
                "screen_architecture_generated",
                product_id=request.product_id,
                screen_count=len(result.screens),
            )

            return result

    # ------------------------------------------------------------------
    # Update Product Spec
    # ------------------------------------------------------------------

    async def update_product_spec(
        self, venture_id: str, product_id: str, updates: dict[str, Any]
    ) -> ProductSpecResponse:
        """Update fields on a product specification."""
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "update_product_spec"):
            allowed_fields = {
                "name", "description", "personas", "features",
                "ai_interaction_patterns", "screen_architecture",
                "ux_flows", "status",
            }

            async with get_session(venture_id) as session:
                result = await session.execute(
                    select(ProductSpec).where(
                        ProductSpec.id == product_id,
                        ProductSpec.venture_id == venture_id,
                        ProductSpec.deleted_at.is_(None),
                    )
                )
                product = result.scalar_one()

                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(product, field, value)

                await session.flush()
                response = _spec_to_response(product)

            logger.info(
                "product_spec_updated",
                product_id=product_id,
                venture_id=venture_id,
                updated_fields=list(updates.keys()),
            )

            return response


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _spec_to_response(product: ProductSpec) -> ProductSpecResponse:
    """Convert a ProductSpec ORM model to a response schema."""
    return ProductSpecResponse(
        id=product.id,
        venture_id=product.venture_id,
        name=product.name,
        description=product.description,
        personas=product.personas,
        features=product.features,
        ai_interaction_patterns=product.ai_interaction_patterns,
        screen_architecture=product.screen_architecture,
        ux_flows=product.ux_flows,
        status=product.status,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


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
