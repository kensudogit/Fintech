from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_orchestration
from app.api.schemas import (
    BehaviorEventRequest,
    ChatRequest,
    ChatResponse,
    ConfirmActionRequest,
    DecisionTransformRequest,
    EvidenceFreeTextRequest,
    EvidenceIngestRequest,
    HealthResponse,
    KnowledgeIngestRequest,
    LoanAnalyzeRequest,
    MatchingSearchRequest,
    SuggestResponse,
    ValuationAnalyzeRequest,
)
from app.config import get_settings
from app.db.models import BehaviorEvent, ConversationMessage, ConversationSession, KnowledgeDocument, User
from app.db.session import get_db
from app.finance.tools import finance_toolkit
from app.personalization.engine import personalization_engine
from app.rag.pipeline import rag_service
from app.seed import seed_sample_data
from app.tempest import (
    decision_engine,
    evidence_store,
    list_packages,
    loan_engine,
    matching_engine,
    sales_engine,
    valuation_agent,
)


async def _persist_evidence(db: AsyncSession, item: dict) -> str | None:
    """Mirror evidence into knowledge_documents for RAG + durability."""
    body = item.get("narrative") or (
        f"{item.get('title')}: {item.get('value')}{item.get('unit', '')} trend={item.get('trend')}"
    )
    relevance = item.get("decision_relevance") or ""
    content = (
        f"【意思決定エビデンス】{item.get('title')}\n"
        f"種別: {item.get('kind')} / 案件: {item.get('case_id') or 'global'}\n"
        f"意思決定への寄与: {relevance}\n"
        f"{body}"
    )
    meta = {
        "evidence_id": item.get("evidence_id"),
        "kind": item.get("kind"),
        "case_id": item.get("case_id"),
        "decision_relevance": relevance,
        "submitted_by": item.get("submitted_by"),
        "value": item.get("value"),
        "unit": item.get("unit"),
        "trend": item.get("trend"),
        "polarity": item.get("polarity"),
        "confidence": item.get("confidence"),
        "weight": item.get("weight"),
        "narrative": item.get("narrative"),
        "title": item.get("title"),
        "source": item.get("source"),
        "created_at": item.get("created_at"),
    }
    doc = KnowledgeDocument(
        source=str(item.get("source") or "evidence_intake"),
        title=f"[Evidence] {item.get('title')}",
        content=content,
        category="decision_evidence",
        metadata_=meta,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    try:
        await rag_service.build_index(db)
    except Exception:  # noqa: BLE001
        # Evidence is already committed; RAG rebuild must not fail the API
        pass
    return str(doc.id)


async def _hydrate_evidence_from_db(db: AsyncSession) -> int:
    """Load persisted decision_evidence rows into the in-memory store (multi-worker safe)."""
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.category == "decision_evidence")
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(200)
    )
    count = 0
    for doc in result.scalars().all():
        meta = dict(doc.metadata_ or {})
        eid = meta.get("evidence_id") or f"EV-DB-{str(doc.id)[:8]}"
        kind = meta.get("kind") or "qualitative"
        payload = {
            "evidence_id": eid,
            "kind": kind,
            "title": meta.get("title") or doc.title.replace("[Evidence] ", "", 1),
            "case_id": meta.get("case_id"),
            "source": meta.get("source") or doc.source,
            "submitted_by": meta.get("submitted_by") or "demo-user-001",
            "decision_relevance": meta.get("decision_relevance") or "",
            "weight": meta.get("weight") or 1.0,
            "created_at": meta.get("created_at")
            or (doc.created_at.isoformat() if doc.created_at else None),
        }
        if kind == "quantitative":
            payload.update(
                {
                    "value": meta.get("value") if meta.get("value") is not None else 0,
                    "unit": meta.get("unit") or "index",
                    "trend": meta.get("trend") or "flat",
                }
            )
        else:
            payload.update(
                {
                    "narrative": meta.get("narrative") or doc.content,
                    "polarity": meta.get("polarity") or "mixed",
                    "confidence": meta.get("confidence") or 0.75,
                }
            )
        try:
            evidence_store.upsert(payload)
            count += 1
        except ValueError:
            continue
    return count

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        product="TempestAI｜金融AIパッケージ",
        llm_provider=settings.llm_provider,
        rag_documents=len(getattr(rag_service, "_docs", []) or []),
    )


@router.get("/tempest/packages")
async def tempest_packages() -> list[dict]:
    return list_packages()


@router.get("/tempest/valuation/universe")
async def tempest_valuation_universe() -> list[dict]:
    return valuation_agent.list_universe()


@router.post("/tempest/valuation/analyze")
async def tempest_valuation_analyze(body: ValuationAnalyzeRequest) -> dict:
    return valuation_agent.analyze(
        body.query,
        ticker=body.ticker,
        horizon_months=body.horizon_months,
    )


@router.get("/tempest/decision/cases")
async def tempest_decision_cases() -> list[dict]:
    return decision_engine.list_cases()


@router.post("/tempest/decision/transform")
async def tempest_decision_transform(
    body: DecisionTransformRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        await _hydrate_evidence_from_db(db)
    except Exception:  # noqa: BLE001
        pass
    return decision_engine.transform(body.query, case_id=body.case_id)


@router.get("/tempest/evidence")
async def list_evidence(
    case_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    try:
        await _hydrate_evidence_from_db(db)
    except Exception:  # noqa: BLE001
        pass
    return evidence_store.list(case_id=case_id, kind=kind, limit=limit)


@router.post("/tempest/evidence")
async def ingest_evidence(body: EvidenceIngestRequest, db: AsyncSession = Depends(get_db)) -> dict:
    data = body.model_dump(exclude={"persist"})
    # Allow title-only qualitative notes
    if data.get("kind") != "quantitative" and not data.get("narrative"):
        data["narrative"] = data.get("title") or data.get("decision_relevance") or "（本文なし）"
    try:
        item = evidence_store.add(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    doc_id = None
    persist_error = None
    if body.persist:
        try:
            doc_id = await _persist_evidence(db, item)
        except Exception as exc:  # noqa: BLE001
            persist_error = str(exc)
    return {
        "ok": True,
        "evidence": item,
        "knowledge_id": doc_id,
        "persist_error": persist_error,
    }


@router.post("/tempest/evidence/text")
async def ingest_evidence_text(body: EvidenceFreeTextRequest, db: AsyncSession = Depends(get_db)) -> dict:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="本文を入力してください")
    try:
        await _hydrate_evidence_from_db(db)
    except Exception:  # noqa: BLE001
        pass
    item = evidence_store.ingest_free_text(
        text=text,
        case_id=body.case_id,
        source=body.source,
        submitted_by=body.submitted_by,
        decision_relevance=body.decision_relevance,
    )
    doc_id = None
    persist_error = None
    if body.persist:
        try:
            doc_id = await _persist_evidence(db, item)
        except Exception as exc:  # noqa: BLE001
            persist_error = str(exc)
    result: dict = {
        "ok": True,
        "evidence": item,
        "knowledge_id": doc_id,
        "persist_error": persist_error,
    }
    if body.run_transform:
        result["transform"] = decision_engine.transform(
            text,
            case_id=body.case_id,
            include_ingested=True,
        )
    return result


@router.delete("/tempest/evidence/{evidence_id}")
async def delete_evidence(evidence_id: str) -> dict:
    ok = evidence_store.delete(evidence_id)
    if not ok:
        raise HTTPException(status_code=404, detail="evidence not found")
    return {"ok": True, "evidence_id": evidence_id}


@router.get("/tempest/loan/applications")
async def tempest_loan_applications() -> list[dict]:
    return loan_engine.list_applications()


@router.post("/tempest/loan/analyze")
async def tempest_loan_analyze(body: LoanAnalyzeRequest) -> dict:
    return loan_engine.analyze(body.query, application_id=body.application_id)


@router.get("/tempest/matching/companies")
async def tempest_matching_companies() -> list[dict]:
    return matching_engine.list_companies()


@router.post("/tempest/matching/search")
async def tempest_matching_search(body: MatchingSearchRequest) -> dict:
    return matching_engine.search(
        body.query,
        source_company_id=body.source_company_id,
        top_k=body.top_k,
    )


@router.post("/tempest/sales/support")
async def tempest_sales_support(body: MatchingSearchRequest) -> dict:
    return sales_engine.support(body.query)


@router.get("/accounts/{external_id}")
async def get_accounts(external_id: str) -> dict:
    return finance_toolkit.get_balances(external_id)


@router.get("/actions/pending")
async def pending_actions(external_id: str = Query(default="demo-user-001")) -> list[dict]:
    return finance_toolkit.list_pending(external_id)


@router.post("/actions/confirm")
async def confirm_action(body: ConfirmActionRequest) -> dict:
    return finance_toolkit.confirm(body.action_id)


@router.post("/actions/cancel")
async def cancel_action(body: ConfirmActionRequest) -> dict:
    return finance_toolkit.cancel(body.action_id)


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


@router.get("/events")
async def list_events(
    external_id: str = Query(default="demo-user-001"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    user = await personalization_engine.ensure_user(db, external_id)
    result = await db.execute(
        select(BehaviorEvent)
        .where(BehaviorEvent.user_id == user.id)
        .order_by(BehaviorEvent.occurred_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "payload": r.payload or {},
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
        }
        for r in rows
    ]


@router.get("/dashboard")
async def dashboard(
    external_id: str = Query(default="demo-user-001"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregate sample data from PostgreSQL for the service UI."""
    user = await personalization_engine.ensure_user(db, external_id)
    profile_data = await personalization_engine.suggest(db, user)

    knowledge = await db.execute(
        select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.asc()).limit(50)
    )
    events = await db.execute(
        select(BehaviorEvent)
        .where(BehaviorEvent.user_id == user.id)
        .order_by(BehaviorEvent.occurred_at.desc())
        .limit(15)
    )
    sessions = await db.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == user.id)
        .order_by(ConversationSession.created_at.desc())
        .limit(5)
    )
    session_rows = sessions.scalars().all()
    recent_messages: list[dict] = []
    if session_rows:
        msg_result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_rows[0].id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(20)
        )
        recent_messages = [
            {
                "role": m.role,
                "content": m.content,
                "agent_name": m.agent_name,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msg_result.scalars().all()
        ]

    users = await db.execute(select(User).order_by(User.created_at.asc()).limit(20))

    try:
        await _hydrate_evidence_from_db(db)
    except Exception:  # noqa: BLE001
        pass

    return {
        "user": {
            "id": str(user.id),
            "external_id": user.external_id,
            "display_name": user.display_name,
            "segment": user.segment,
            "risk_tolerance": user.risk_tolerance,
        },
        "profile": profile_data,
        "knowledge": [
            {
                "id": str(r.id),
                "title": r.title,
                "category": r.category,
                "source": r.source,
                "content": r.content,
            }
            for r in knowledge.scalars().all()
        ],
        "events": [
            {
                "id": str(r.id),
                "event_type": r.event_type,
                "payload": r.payload or {},
                "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            }
            for r in events.scalars().all()
        ],
        "recent_dialogue": recent_messages,
        "users": [
            {
                "external_id": u.external_id,
                "display_name": u.display_name,
                "segment": u.segment,
            }
            for u in users.scalars().all()
        ],
        "counts": {
            "knowledge": int(await db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0),
            "events": int(
                await db.scalar(
                    select(func.count()).select_from(BehaviorEvent).where(BehaviorEvent.user_id == user.id)
                )
                or 0
            ),
        },
        "tempest": {
            "packages": list_packages(),
            "valuation_universe": valuation_agent.list_universe(),
            "decision_cases": decision_engine.list_cases(),
            "loan_applications": loan_engine.list_applications(),
            "companies": matching_engine.list_companies(),
            "evidence": evidence_store.list(limit=30),
            "evidence_count": len(evidence_store.list(limit=200)),
        },
    }


@router.post("/seed")
async def seed(force: bool = Query(default=False), db: AsyncSession = Depends(get_db)) -> dict:
    stats = await seed_sample_data(db, force=force)
    indexed = await rag_service.build_index(db)
    return {"ok": True, "stats": stats, "indexed_documents": indexed}


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
