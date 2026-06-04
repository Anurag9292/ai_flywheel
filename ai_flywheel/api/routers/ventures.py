"""Venture management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ai_flywheel.core.database import get_global_session
from ai_flywheel.core.models import Venture

router = APIRouter()


class CreateVentureRequest(BaseModel):
    name: str
    domain: str
    config: dict = {}


class VentureResponse(BaseModel):
    id: str
    name: str
    domain: str
    status: str
    config: dict
    created_at: str


@router.post("/", response_model=VentureResponse)
async def create_venture(request: CreateVentureRequest) -> VentureResponse:
    """Create a new venture."""
    async with get_global_session() as session:
        venture = Venture(
            name=request.name,
            domain=request.domain,
            config=request.config,
        )
        session.add(venture)
        await session.flush()
        await session.refresh(venture)

        return VentureResponse(
            id=venture.id,
            name=venture.name,
            domain=venture.domain,
            status=venture.status,
            config=venture.config,
            created_at=venture.created_at.isoformat(),
        )


@router.get("/", response_model=list[VentureResponse])
async def list_ventures() -> list[VentureResponse]:
    """List all ventures."""
    async with get_global_session() as session:
        result = await session.execute(select(Venture).where(Venture.deleted_at.is_(None)))
        ventures = result.scalars().all()

        return [
            VentureResponse(
                id=v.id,
                name=v.name,
                domain=v.domain,
                status=v.status,
                config=v.config,
                created_at=v.created_at.isoformat(),
            )
            for v in ventures
        ]


@router.get("/{venture_id}", response_model=VentureResponse)
async def get_venture(venture_id: str) -> VentureResponse:
    """Get a venture by ID."""
    async with get_global_session() as session:
        venture = await session.get(Venture, venture_id)
        if not venture or venture.is_deleted:
            raise HTTPException(status_code=404, detail="Venture not found")

        return VentureResponse(
            id=venture.id,
            name=venture.name,
            domain=venture.domain,
            status=venture.status,
            config=venture.config,
            created_at=venture.created_at.isoformat(),
        )
