"""Policy Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.agent_runtime.policy_engine.schemas import (
    PolicyCheckRequest,
    PolicyCheckResult,
    PolicyCreate,
    PolicyResponse,
    ViolationResponse,
)
from ai_flywheel.modules.agent_runtime.policy_engine.service import PolicyEngine

router = APIRouter()
service = PolicyEngine()


@router.post("/", response_model=PolicyResponse)
async def create_policy(venture_id: str, data: PolicyCreate):
    return await service.create_policy(venture_id, data)


@router.get("/", response_model=list[PolicyResponse])
async def list_policies(venture_id: str, policy_type: str | None = None):
    return await service.list_policies(venture_id, policy_type)


@router.post("/check", response_model=PolicyCheckResult)
async def check(venture_id: str, request: PolicyCheckRequest):
    return await service.check(venture_id, request)


@router.get("/violations", response_model=list[ViolationResponse])
async def get_violations(venture_id: str):
    return await service.get_violations(venture_id)
