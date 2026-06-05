"""Knowledge Graph Builder endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.data_knowledge.knowledge_graph.schemas import (
    ExtractRequest,
    ExtractResult,
    GraphCreate,
    GraphResponse,
    QueryRequest,
    QueryResult,
)
from ai_flywheel.modules.data_knowledge.knowledge_graph.service import KnowledgeGraphBuilder

router = APIRouter()
service = KnowledgeGraphBuilder()


@router.post("/graphs", response_model=GraphResponse)
async def create_graph(venture_id: str, data: GraphCreate):
    return await service.create_graph(venture_id, data)


@router.get("/graphs", response_model=list[GraphResponse])
async def list_graphs(venture_id: str):
    return await service.list_graphs(venture_id)


@router.post("/extract", response_model=ExtractResult)
async def extract(venture_id: str, request: ExtractRequest):
    return await service.extract(venture_id, request)


@router.post("/query", response_model=QueryResult)
async def query(venture_id: str, request: QueryRequest):
    return await service.query(venture_id, request)
