"""Universal Ingestor endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.data_knowledge.ingestor.schemas import (
    DataSourceCreate,
    DataSourceResponse,
    IngestRequest,
    IngestResult,
)
from ai_flywheel.modules.data_knowledge.ingestor.service import UniversalIngestor

router = APIRouter()
service = UniversalIngestor()


@router.post("/sources", response_model=DataSourceResponse)
async def create_source(venture_id: str, data: DataSourceCreate):
    return await service.create_source(venture_id, data)


@router.get("/sources", response_model=list[DataSourceResponse])
async def list_sources(venture_id: str):
    return await service.list_sources(venture_id)


@router.post("/ingest", response_model=IngestResult)
async def ingest(venture_id: str, request: IngestRequest):
    return await service.ingest(venture_id, request)
