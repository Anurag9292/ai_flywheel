"""Cost Optimizer endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.experimentation.cost_optimizer.schemas import (
    BudgetCreate,
    BudgetResponse,
    CostAlertResponse,
    CostReport,
)
from ai_flywheel.modules.experimentation.cost_optimizer.service import CostOptimizer

router = APIRouter()
service = CostOptimizer()


@router.post("/budgets", response_model=BudgetResponse)
async def set_budget(data: BudgetCreate):
    return await service.set_budget(data)


@router.get("/report", response_model=CostReport)
async def get_report(venture_id: str, period_type: str = "monthly"):
    return await service.get_report(venture_id, period_type)


@router.get("/alerts", response_model=list[CostAlertResponse])
async def get_alerts(venture_id: str):
    return await service.get_alerts(venture_id)


@router.post("/check", response_model=list[CostAlertResponse])
async def check_budget(venture_id: str):
    return await service.check_budget(venture_id)
