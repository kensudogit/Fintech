from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    user_id: str
    external_id: str
    query: str
    intent: str
    intents: list[str]
    profile_summary: str
    rag_context: str
    agent_outputs: dict[str, str]
    pending_action: dict[str, Any]
    package_payload: dict[str, Any]
    citations: list[str]
    final_response: str
    routing_trace: list[str]
    agents_used: list[str]
