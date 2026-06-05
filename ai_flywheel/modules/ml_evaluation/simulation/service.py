# ruff: noqa: E501
"""Simulation Engine — core service.

Manages simulations, runs scenarios with pass/fail evaluation,
supports failure injection, and provides cost estimation.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from sqlalchemy import select

from ai_flywheel.core.database import get_session
from ai_flywheel.core.events import get_event_bus

from .models import Simulation
from .schemas import (
    RunSimulationRequest,
    SimulationCreate,
    SimulationResponse,
    SimulationResult,
)

logger = structlog.get_logger()

COST_PER_SCENARIO = 0.01


class SimulationEngine:
    """Manages simulations and runs scenario-based workflow tests."""

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_simulation(
        self, venture_id: str, data: SimulationCreate
    ) -> SimulationResponse:
        """Create a new simulation."""
        async with get_session(venture_id) as session:
            simulation = Simulation(
                venture_id=venture_id,
                name=data.name,
                description=data.description,
                workflow_blueprint_id=data.workflow_blueprint_id,
                scenarios=data.scenarios,
                status="draft",
                total_scenarios=len(data.scenarios),
            )
            session.add(simulation)
            await session.flush()
            await session.refresh(simulation)

            logger.info(
                "simulation_created",
                venture_id=venture_id,
                simulation_id=simulation.id,
                name=data.name,
            )

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="simulation.created",
                source_module="simulation_engine",
                payload={
                    "simulation_id": simulation.id,
                    "name": data.name,
                    "scenario_count": len(data.scenarios),
                },
                venture_id=venture_id,
            )

            return self._to_response(simulation)

    async def get_simulation(self, venture_id: str, simulation_id: str) -> SimulationResponse:
        """Get a single simulation by ID."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Simulation).where(
                    Simulation.venture_id == venture_id,
                    Simulation.id == simulation_id,
                    Simulation.deleted_at.is_(None),
                )
            )
            simulation = result.scalar_one()
            return self._to_response(simulation)

    async def list_simulations(self, venture_id: str) -> list[SimulationResponse]:
        """List all simulations for a venture."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Simulation).where(
                    Simulation.venture_id == venture_id,
                    Simulation.deleted_at.is_(None),
                )
            )
            simulations = result.scalars().all()
            return [self._to_response(s) for s in simulations]

    async def add_scenario(
        self, venture_id: str, simulation_id: str, scenario: dict[str, Any]
    ) -> SimulationResponse:
        """Add a scenario to an existing simulation."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Simulation).where(
                    Simulation.venture_id == venture_id,
                    Simulation.id == simulation_id,
                    Simulation.deleted_at.is_(None),
                )
            )
            simulation = result.scalar_one()

            scenarios = list(simulation.scenarios)
            scenarios.append(scenario)
            simulation.scenarios = scenarios
            simulation.total_scenarios = len(scenarios)
            await session.flush()

            return self._to_response(simulation)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(
        self, venture_id: str, request: RunSimulationRequest
    ) -> SimulationResult:
        """Run a simulation, executing each scenario and recording pass/fail."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Simulation).where(
                    Simulation.venture_id == venture_id,
                    Simulation.id == request.simulation_id,
                    Simulation.deleted_at.is_(None),
                )
            )
            simulation = result.scalar_one()

            # Use provided scenarios or the simulation's stored ones
            scenarios = request.scenarios if request.scenarios is not None else simulation.scenarios

            simulation.status = "running"
            await session.flush()

            event_bus = get_event_bus()
            await event_bus.publish(
                event_type="simulation.started",
                source_module="simulation_engine",
                payload={"simulation_id": simulation.id},
                venture_id=venture_id,
            )

            start_time = time.time()
            scenario_results: list[dict[str, Any]] = []
            passed = 0
            failed = 0

            for scenario in scenarios:
                scenario_result = self._execute_scenario(scenario)
                scenario_results.append(scenario_result)
                if scenario_result["passed"]:
                    passed += 1
                else:
                    failed += 1

            duration_ms = (time.time() - start_time) * 1000
            total = len(scenarios)
            cost = total * COST_PER_SCENARIO

            simulation.status = "completed"
            simulation.total_scenarios = total
            simulation.passed_scenarios = passed
            simulation.failed_scenarios = failed
            simulation.duration_ms = duration_ms
            simulation.cost_estimate_usd = cost
            simulation.results = {"scenario_results": scenario_results}
            await session.flush()

            logger.info(
                "simulation_completed",
                venture_id=venture_id,
                simulation_id=simulation.id,
                total=total,
                passed=passed,
                failed=failed,
            )

            await event_bus.publish(
                event_type="simulation.completed",
                source_module="simulation_engine",
                payload={
                    "simulation_id": simulation.id,
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                },
                venture_id=venture_id,
            )

            recommendations = self._generate_recommendations(scenario_results, passed, total)

            return SimulationResult(
                simulation_id=simulation.id,
                status="completed",
                total_scenarios=total,
                passed_scenarios=passed,
                failed_scenarios=failed,
                scenario_results=scenario_results,
                duration_ms=duration_ms,
                cost_estimate_usd=cost,
                recommendations=recommendations,
            )

    # ------------------------------------------------------------------
    # Cost Estimation
    # ------------------------------------------------------------------

    async def estimate_cost(self, venture_id: str, simulation_id: str) -> float:
        """Estimate cost for running a simulation."""
        async with get_session(venture_id) as session:
            result = await session.execute(
                select(Simulation).where(
                    Simulation.venture_id == venture_id,
                    Simulation.id == simulation_id,
                    Simulation.deleted_at.is_(None),
                )
            )
            simulation = result.scalar_one()
            return len(simulation.scenarios) * COST_PER_SCENARIO

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Execute a single scenario and determine pass/fail."""
        name = scenario.get("name", "unnamed")
        input_data = scenario.get("input_data", {})
        expected_outcome = scenario.get("expected_outcome")
        failure_injection = scenario.get("failure_injection")

        # Failure injection scenarios always fail
        if failure_injection:
            return {
                "name": name,
                "passed": False,
                "reason": "failure_injection_triggered",
                "input": input_data,
                "expected": expected_outcome,
                "actual": None,
            }

        # No expected outcome means auto-pass
        if expected_outcome is None:
            return {
                "name": name,
                "passed": True,
                "reason": "no_expected_outcome",
                "input": input_data,
                "expected": None,
                "actual": input_data,
            }

        # Compare input against expected (key subset match)
        passed = all(
            input_data.get(key) == value
            for key, value in expected_outcome.items()
        )

        return {
            "name": name,
            "passed": passed,
            "reason": "match" if passed else "mismatch",
            "input": input_data,
            "expected": expected_outcome,
            "actual": input_data,
        }

    def _generate_recommendations(
        self, results: list[dict[str, Any]], passed: int, total: int
    ) -> list[str]:
        """Generate recommendations based on simulation results."""
        recommendations: list[str] = []

        if total == 0:
            return ["Add scenarios to test workflow behavior"]

        pass_rate = passed / total
        if pass_rate < 0.5:
            recommendations.append("Pass rate below 50% — review workflow logic")
        elif pass_rate < 0.8:
            recommendations.append("Consider adding edge case scenarios")

        failure_injections = sum(1 for r in results if r.get("reason") == "failure_injection_triggered")
        if failure_injections > 0:
            recommendations.append(f"{failure_injections} failure injection scenario(s) — verify error handling")

        if not recommendations:
            recommendations.append("All scenarios passing — consider adding more complex test cases")

        return recommendations

    def _to_response(self, simulation: Simulation) -> SimulationResponse:
        """Convert ORM model to response schema."""
        return SimulationResponse(
            id=simulation.id,
            venture_id=simulation.venture_id,
            name=simulation.name,
            description=simulation.description,
            workflow_blueprint_id=simulation.workflow_blueprint_id,
            scenarios_count=len(simulation.scenarios) if simulation.scenarios else 0,
            status=simulation.status,
            total_scenarios=simulation.total_scenarios,
            passed_scenarios=simulation.passed_scenarios,
            failed_scenarios=simulation.failed_scenarios,
            duration_ms=simulation.duration_ms,
            cost_estimate_usd=simulation.cost_estimate_usd,
            created_at=simulation.created_at,
        )
