"""Learning Loop — closes the flywheel feedback cycle.

When an experiment concludes (winner found), this module:
1. Extracts the winning pattern (what worked + why)
2. Stores it in the Pattern Library
3. Updates the venture's flywheel velocity metrics
4. Emits events for cross-venture learning

This is the mechanism that makes each venture faster than the last.

Event Flow:
  experiment.concluded → learning_loop.extract_pattern → pattern.created
  pattern.created → meta_learning.update_velocity
"""

from __future__ import annotations

import structlog

from ai_flywheel.core.database import get_session, get_global_session
from ai_flywheel.core.events import get_event_bus
from ai_flywheel.core.traces import Tracer

logger = structlog.get_logger()

MODULE_NAME = "learning_loop"


class LearningLoop:
    """Automated feedback loop that extracts patterns from experiment results."""

    def __init__(self) -> None:
        self._tracer = Tracer()
        self._event_bus = get_event_bus()

    async def on_experiment_concluded(self, venture_id: str, experiment_id: str) -> dict:
        """React to an experiment concluding — extract and store the winning pattern.

        Called when experiment.concluded event fires.
        """
        self._tracer.set_venture_context(venture_id)

        async with self._tracer.span(MODULE_NAME, "extract_pattern", input_data={"experiment_id": experiment_id}):
            # 1. Get experiment results
            from ai_flywheel.modules.experimentation.ab_testing.service import ABTestEngine
            ab_service = ABTestEngine()
            experiment = await ab_service.get_experiment(venture_id, experiment_id)

            if not experiment or experiment.get("status") != "concluded":
                return {"status": "skipped", "reason": "experiment not concluded"}

            winner = experiment.get("winner")
            if not winner:
                return {"status": "skipped", "reason": "no winner determined"}

            # 2. Extract the pattern
            pattern_data = {
                "name": f"Winning: {experiment.get('name', 'unnamed')}",
                "description": f"Experiment '{experiment.get('name')}' concluded with winner: {winner.get('name', 'variant')}. "
                               f"Effect size: {winner.get('effect_size', 'unknown')}. "
                               f"Sample size: {experiment.get('total_observations', 0)}.",
                "pattern_type": experiment.get("experiment_type", "general"),
                "source_experiment_id": experiment_id,
                "source_venture_id": venture_id,
                "confidence": min(0.95, experiment.get("statistical_significance", 0.5)),
                "context": {
                    "domain": experiment.get("domain", ""),
                    "variant_config": winner.get("config", {}),
                    "metric_improvement": winner.get("metric_value", 0),
                },
                "tags": experiment.get("tags", []),
            }

            # 3. Store in Pattern Library (global scope)
            from ai_flywheel.modules.cross_venture.pattern_library.service import PatternLibrary
            pattern_service = PatternLibrary()
            pattern = await pattern_service.create_pattern(pattern_data)

            # 4. Update flywheel velocity
            from ai_flywheel.modules.cross_venture.meta_learning.service import MetaLearningEngine
            meta_service = MetaLearningEngine()
            await meta_service.record_metric({
                "venture_id": venture_id,
                "metric_type": "pattern_extracted",
                "value": 1.0,
                "metadata": {"pattern_id": pattern.get("id", ""), "experiment_id": experiment_id},
            })

            # 5. Emit events
            await self._event_bus.publish(
                event_type="pattern.created",
                source_module=MODULE_NAME,
                payload={
                    "pattern_id": pattern.get("id", ""),
                    "source_experiment": experiment_id,
                    "venture_id": venture_id,
                    "pattern_type": pattern_data["pattern_type"],
                },
                venture_id=venture_id,
            )

            await self._event_bus.publish(
                event_type="flywheel.cycle_completed",
                source_module=MODULE_NAME,
                payload={
                    "venture_id": venture_id,
                    "experiment_id": experiment_id,
                    "pattern_id": pattern.get("id", ""),
                    "phase": "experiment → pattern",
                },
                venture_id=venture_id,
            )

            logger.info(
                "learning_loop_pattern_extracted",
                venture_id=venture_id,
                experiment_id=experiment_id,
                pattern_id=pattern.get("id", ""),
            )

            return {
                "status": "pattern_extracted",
                "pattern_id": pattern.get("id", ""),
                "pattern_name": pattern_data["name"],
                "confidence": pattern_data["confidence"],
            }

    async def on_feedback_received(self, venture_id: str, feedback_id: str, experiment_id: str | None) -> dict:
        """React to feedback — route it to the correct experiment.

        When feedback comes in, check if it relates to an active experiment
        and record it as an observation.
        """
        if not experiment_id:
            return {"status": "skipped", "reason": "no experiment_id"}

        from ai_flywheel.modules.experimentation.ab_testing.service import ABTestEngine
        ab_service = ABTestEngine()

        # Check if experiment should conclude
        experiment = await ab_service.get_experiment(venture_id, experiment_id)
        if experiment and experiment.get("status") == "running":
            # Check for statistical significance
            result = await ab_service.check_significance(venture_id, experiment_id)
            if result.get("significant"):
                # Auto-conclude and trigger pattern extraction
                await ab_service.conclude_experiment(venture_id, experiment_id)
                await self.on_experiment_concluded(venture_id, experiment_id)
                return {"status": "experiment_concluded", "experiment_id": experiment_id}

        return {"status": "feedback_recorded"}

    async def recommend_patterns(self, venture_id: str, context: dict) -> list[dict]:
        """Recommend applicable patterns for a venture based on context.

        This is the "compounding" mechanism — patterns learned in venture A
        are recommended for venture B when the context matches.
        """
        from ai_flywheel.modules.cross_venture.pattern_library.service import PatternLibrary
        pattern_service = PatternLibrary()

        patterns = await pattern_service.recommend_for_venture(venture_id)
        return patterns

    async def get_flywheel_status(self, venture_id: str) -> dict:
        """Get the current flywheel status for a venture.

        Returns velocity, patterns extracted, experiments completed,
        and comparison to previous ventures.
        """
        from ai_flywheel.modules.cross_venture.meta_learning.service import MetaLearningEngine
        meta_service = MetaLearningEngine()

        velocity = await meta_service.get_velocity(venture_id)
        insights = await meta_service.get_insights(venture_id)

        return {
            "venture_id": venture_id,
            "velocity": velocity,
            "insights": insights,
            "flywheel_phase": "active" if velocity.get("current_velocity", 0) > 0 else "warming_up",
        }
