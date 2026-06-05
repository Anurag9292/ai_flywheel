"""Embedding Engine endpoints."""

from fastapi import APIRouter

from ai_flywheel.modules.data_knowledge.embeddings.schemas import (
    CollectionCreate,
    CollectionResponse,
    EmbedRequest,
    EmbedResult,
    SearchRequest,
    SearchResult,
)
from ai_flywheel.modules.data_knowledge.embeddings.service import EmbeddingEngine

router = APIRouter()
service = EmbeddingEngine()


@router.post("/collections", response_model=CollectionResponse)
async def create_collection(venture_id: str, data: CollectionCreate):
    return await service.create_collection(venture_id, data)


@router.get("/collections", response_model=list[CollectionResponse])
async def list_collections(venture_id: str):
    return await service.list_collections(venture_id)


@router.post("/embed", response_model=EmbedResult)
async def embed(venture_id: str, request: EmbedRequest):
    return await service.embed(venture_id, request)


@router.post("/search", response_model=SearchResult)
async def search(venture_id: str, request: SearchRequest):
    return await service.search(venture_id, request)
