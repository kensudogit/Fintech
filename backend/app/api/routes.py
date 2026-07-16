from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_orchestration
from app.api.schemas import (
    BehaviorEventRequest,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    KnowledgeIngestRequest,
    SuggestResponse,
)
from app.config import get_settings
from app.db.models import KnowledgeDocument
from app.db.session import get_db
from app.personalization.engine import personalization_engine
from app.rag.pipeline import rag_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        llm_provider=settings.llm_provider,
        rag_documents=len(getattr(rag_service, "_docs", []) or []),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    result = await run_orchestration(
        db,
        external_id=body.external_id,
        query=body.message,
        session_id=body.session_id,
        channel=body.channel,
    )
    return ChatResponse(**result)


@router.post("/events")
async def create_event(body: BehaviorEventRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = await personalization_engine.ensure_user(db, body.external_id)
    event = await personalization_engine.record_event(db, user, body.event_type, body.payload)
    profile = await personalization_engine.rebuild_profile(db, user)
    return {
        "event_id": str(event.id),
        "user_id": str(user.id),
        "activity_score": profile.activity_score,
        "interests": profile.interests,
    }


@router.get("/users/{external_id}/suggestions", response_model=SuggestResponse)
async def suggestions(external_id: str, db: AsyncSession = Depends(get_db)) -> SuggestResponse:
    user = await personalization_engine.ensure_user(db, external_id)
    data = await personalization_engine.suggest(db, user)
    return SuggestResponse(**data)


@router.get("/users/{external_id}/profile")
async def get_profile(external_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    user = await personalization_engine.ensure_user(db, external_id)
    profile = await personalization_engine.rebuild_profile(db, user)
    return {
        "user_id": str(user.id),
        "external_id": user.external_id,
        "display_name": user.display_name,
        "segment": user.segment,
        "risk_tolerance": user.risk_tolerance,
        "summary": profile.summary,
        "interests": profile.interests,
        "preferred_products": profile.preferred_products,
        "activity_score": profile.activity_score,
        "features": profile.features,
    }


@router.get("/knowledge")
async def list_knowledge(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).limit(100))
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "category": r.category,
            "source": r.source,
            "content": r.content[:240],
        }
        for r in rows
    ]


@router.post("/knowledge")
async def ingest_knowledge(body: KnowledgeIngestRequest, db: AsyncSession = Depends(get_db)) -> dict:
    doc = KnowledgeDocument(
        source=body.source,
        title=body.title,
        content=body.content,
        category=body.category,
        metadata_=body.metadata,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    count = await rag_service.build_index(db)
    return {"id": str(doc.id), "indexed_documents": count}


@router.post("/rag/reindex")
async def reindex(db: AsyncSession = Depends(get_db)) -> dict:
    count = await rag_service.build_index(db)
    return {"indexed_documents": count}


@router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: UUID, db: AsyncSession = Depends(get_db)) -> list[dict]:
    from app.db.models import ConversationMessage

    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="session not found or empty")
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "agent_name": m.agent_name,
            "metadata": m.metadata_,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
