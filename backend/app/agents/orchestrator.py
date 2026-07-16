from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes import classify_intent, run_specialists, synthesize
from app.agents.state import AgentState
from app.db.models import AgentRun, ConversationMessage, ConversationSession
from app.personalization.engine import personalization_engine


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("run_specialists", run_specialists)
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("classify_intent")
    graph.add_edge("classify_intent", "run_specialists")
    graph.add_edge("run_specialists", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


async def run_orchestration(
    session: AsyncSession,
    *,
    external_id: str,
    query: str,
    session_id: UUID | None = None,
    channel: str = "web",
) -> dict[str, Any]:
    started = time.perf_counter()
    user = await personalization_engine.ensure_user(session, external_id)
    profile = await personalization_engine.rebuild_profile(session, user)

    if session_id is None:
        conv = ConversationSession(user_id=user.id, title=query[:80], channel=channel)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        session_id = conv.id
    else:
        conv = await session.get(ConversationSession, session_id)
        if conv is None:
            conv = ConversationSession(user_id=user.id, title=query[:80], channel=channel)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
            session_id = conv.id

    session.add(
        ConversationMessage(session_id=session_id, role="user", content=query, agent_name=None, metadata_={})
    )
    await session.commit()

    initial: AgentState = {
        "messages": [HumanMessage(content=query)],
        "user_id": str(user.id),
        "external_id": external_id,
        "query": query,
        "intent": "",
        "intents": [],
        "profile_summary": profile.summary or "",
        "rag_context": "",
        "agent_outputs": {},
        "pending_action": {},
        "citations": [],
        "final_response": "",
        "routing_trace": [],
        "agents_used": [],
    }

    graph = get_graph()
    result = graph.invoke(initial)
    answer = result.get("final_response") or "回答を生成できませんでした。"
    latency_ms = int((time.perf_counter() - started) * 1000)
    intents = result.get("intents") or ([result.get("intent")] if result.get("intent") else [])
    pending = result.get("pending_action") or {}

    session.add(
        ConversationMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            agent_name=",".join(result.get("agents_used") or []),
            metadata_={
                "intent": result.get("intent"),
                "intents": intents,
                "routing_trace": result.get("routing_trace"),
                "pending_action": pending,
                "citations": result.get("citations") or [],
            },
        )
    )
    session.add(
        AgentRun(
            session_id=session_id,
            user_id=user.id,
            intent=",".join(intents) if intents else result.get("intent"),
            agents_used=result.get("agents_used") or [],
            routing_trace=result.get("routing_trace") or [],
            latency_ms=latency_ms,
        )
    )
    await personalization_engine.record_event(
        session,
        user,
        event_type="dialogue",
        payload={"intents": intents, "query": query[:200]},
    )
    await session.commit()

    return {
        "session_id": str(session_id),
        "user_id": str(user.id),
        "external_id": external_id,
        "intent": result.get("intent"),
        "intents": intents,
        "answer": answer,
        "agents_used": result.get("agents_used") or [],
        "routing_trace": result.get("routing_trace") or [],
        "rag_context": result.get("rag_context") or "",
        "citations": result.get("citations") or [],
        "pending_action": pending or None,
        "agent_outputs": result.get("agent_outputs") or {},
        "latency_ms": latency_ms,
        "profile_summary": profile.summary,
        "product": "LLM × マルチエージェント｜金融AIプロダクト",
    }
