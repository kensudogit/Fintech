from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    external_id: str = Field(default="demo-user-001", min_length=1)
    session_id: UUID | None = None
    channel: str = "web"


class ChatResponse(BaseModel):
    session_id: str
    user_id: str
    external_id: str
    intent: str | None = None
    answer: str
    agents_used: list[str] = []
    routing_trace: list[str] = []
    rag_context: str = ""
    latency_ms: int = 0
    profile_summary: str | None = None


class BehaviorEventRequest(BaseModel):
    external_id: str = "demo-user-001"
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SuggestResponse(BaseModel):
    user_id: str
    external_id: str
    profile_summary: str | None
    interests: list[str]
    preferred_products: list[str]
    activity_score: float
    suggestions: list[str]


class KnowledgeIngestRequest(BaseModel):
    source: str
    title: str
    content: str
    category: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app: str
    llm_provider: str
    rag_documents: int
