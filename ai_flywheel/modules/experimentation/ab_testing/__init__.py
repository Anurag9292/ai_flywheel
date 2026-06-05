"""A/B Test & Optimization Engine — Module #32 (Phase 3, Experimentation group).

Runs experiments (A/B tests, bandits, multivariate) with statistical rigor.
Handles variant assignment, observation recording, and significance testing.

Usage:
    from ai_flywheel.modules.experimentation.ab_testing import (
        ABTestEngine,
        Experiment,
        ExperimentObservation,
    )

    engine = ABTestEngine()
    experiment = await engine.create_experiment(venture_id, data)
    variant = await engine.assign_variant(venture_id, experiment.id, user_id)
    await engine.record_observation(venture_id, observation)
    results = await engine.get_results(venture_id, experiment.id)
"""

from .models import Experiment, ExperimentObservation
from .schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentResults,
    RecordObservationRequest,
    VariantStats,
)
from .service import ABTestEngine

__all__ = [
    "ABTestEngine",
    "Experiment",
    "ExperimentCreate",
    "ExperimentObservation",
    "ExperimentResponse",
    "ExperimentResults",
    "RecordObservationRequest",
    "VariantStats",
]
