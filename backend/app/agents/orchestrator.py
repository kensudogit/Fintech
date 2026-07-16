from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nodes import (
    classify_intent,
    knowledge_agent,
    operations_agent,
    personalization_agent,
    route_by_intent,
    synthesize,
)
from app.agents.state import AgentState
from app.db.models import AgentRun, ConversationMessage, ConversationSession
from app.personalization.engine import personalization_engine


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("operations_agent", operations_agent)
    graph.add_node("personalization_agent", personalization_agent)
    graph.add_node("knowledge_agent", knowledge_agent)
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "operations_agent": "operations_agent",
            "personalization_agent": "personalization_agent",
            "knowledge_agent": "knowledge_agent",
        },
    )
    graph.add_edge("operations_agent", "synthesize")
    graph.add_edge("personalization_agent", "synthesize")
    graph.add_edge("knowledge_agent", "synthesize")
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
        "profile_summary": profile.summary or "",
        "rag_context": "",
        "agent_outputs": {},
        "final_response": "",
        "routing_trace": [],
        "agents_used": [],
    }

    graph = get_graph()
    result = graph.invoke(initial)
    answer = result.get("final_response") or "回答を生成できませんでした。"
    latency_ms = int((time.perf_counter() - started) * 1000)

    session.add(
        ConversationMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            agent_name=",".join(result.get("agents_used") or []),
            metadata_={
                "intent": result.get("intent"),
                "routing_trace": result.get("routing_trace"),
            },
        )
    )
    session.add(
        AgentRun(
            session_id=session_id,
            user_id=user.id,
            intent=result.get("intent"),
            agents_used=result.get("agents_used") or [],
            routing_trace=result.get("routing_trace") or [],
            latency_ms=latency_ms,
        )
    )
    # Treat dialogue as a behavior signal for personalization learning
    await personalization_engine.record_event(
        session,
        user,
        event_type="dialogue",
        payload={"intent": result.get("intent"), "query": query[:200]},
    )
    await session.commit()

    return {
        "session_id": str(session_id),
        "user_id": str(user.id),
        "external_id": external_id,
        "intent": result.get("intent"),
        "answer": answer,
        "agents_used": result.get("agents_used") or [],
        "routing_trace": result.get("routing_trace") or [],
        "rag_context": result.get("rag_context") or "",
        "latency_ms": latency_ms,
        "profile_summary": profile.summary,
    }
