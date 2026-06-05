"""Deployment Engine + Reliability endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.deployment.deployment_engine.schemas import (
    DeploymentCreate,
    DeploymentResponse,
    DeployRequest,
    DeployResult,
    HealthCheckResult,
    RollbackRequest,
    RollbackResult,
)
from ai_flywheel.modules.deployment.deployment_engine.service import DeploymentEngine
from ai_flywheel.modules.deployment.reliability.schemas import (
    IncidentCreate,
    IncidentResponse,
    RecordMetricRequest,
    ReliabilityReport,
)
from ai_flywheel.modules.deployment.reliability.service import ReliabilityEngine

router = APIRouter()
deployment_service = DeploymentEngine()
reliability_service = ReliabilityEngine()


# ─── Deployments ──────────────────────────────────────────────────────────────


@router.post("/", response_model=DeploymentResponse)
async def create_deployment(venture_id: str, data: DeploymentCreate):
    return await deployment_service.create_deployment(venture_id, data)


@router.get("/", response_model=list[DeploymentResponse])
async def list_deployments(venture_id: str):
    return await deployment_service.list_deployments(venture_id)


@router.post("/deploy", response_model=DeployResult)
async def deploy(venture_id: str, request: DeployRequest):
    return await deployment_service.deploy(venture_id, request)


@router.post("/rollback", response_model=RollbackResult)
async def rollback(venture_id: str, request: RollbackRequest):
    return await deployment_service.rollback(venture_id, request)


@router.get("/health-check/{deployment_id}", response_model=HealthCheckResult)
async def health_check(venture_id: str, deployment_id: str):
    return await deployment_service.health_check(venture_id, deployment_id)


# ─── Reliability ──────────────────────────────────────────────────────────────


@router.post("/incidents", response_model=IncidentResponse)
async def create_incident(venture_id: str, data: IncidentCreate):
    return await reliability_service.create_incident(venture_id, data)


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(venture_id: str):
    return await reliability_service.list_incidents(venture_id)


@router.post("/metrics")
async def record_metric(venture_id: str, request: RecordMetricRequest):
    return await reliability_service.record_metric(venture_id, request)


@router.get("/reliability-report", response_model=ReliabilityReport)
async def get_report(venture_id: str):
    return await reliability_service.get_report(venture_id)
