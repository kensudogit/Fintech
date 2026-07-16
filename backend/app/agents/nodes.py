from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.finance.tools import finance_toolkit
from app.llm.factory import get_chat_model
from app.rag.pipeline import rag_service

VALID_INTENTS = ("operations", "personalization", "knowledge")


def _wants_operations(q: str) -> bool:
    """Detect actionable ops; fee FAQs like 振込手数料 are knowledge, not transfer."""
    if any(k in q for k in ("残高", "カード停止", "カードを止め", "freeze", "利用停止")):
        return True
    if any(k in q for k in ("振り込", "送金して", "振込して", "振込みたい", "送金したい")):
        return True
    if "手数料" in q:
        return False
    return any(k in q for k in ("振込", "送金", "transfer", "pay", "操作"))


def _detect_intents(query: str) -> list[str]:
    """Rule-based multi-intent detection for compound financial queries."""
    q = query
    found: list[str] = []

    if _wants_operations(q):
        found.append("operations")
    if any(k in q for k in ("提案", "おすすめ", "分析", "節約", "パーソナライズ", "家計", "改善")):
        found.append("personalization")
    if any(k in q for k in ("手数料", "口座開設", "とは", "教えて", "流れ", "不正利用", "FAQ", "知識", "NISA")):
        found.append("knowledge")

    if not found:
        found = ["knowledge"]
    return found


def classify_intent(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたは金融アプリの意図分類器です。"
                "該当する意図をカンマ区切りで返してください。"
                "候補: operations, personalization, knowledge"
                "複合質問なら複数返してください。余計な文字は不要です。"
            )
        ),
        HumanMessage(content=f"ユーザー入力: {state['query']}\nintents を判定してください。"),
    ]
    result = llm.invoke(prompt)
    raw = str(getattr(result, "content", result)).strip().lower()
    intents = [p.strip() for p in raw.replace("、", ",").split(",") if p.strip() in VALID_INTENTS]
    if not intents:
        intents = _detect_intents(state["query"])
    else:
        # Merge heuristic extras for compound questions like "手数料と提案"
        for extra in _detect_intents(state["query"]):
            if extra not in intents:
                intents.append(extra)

    # Deduplicate preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for i in intents:
        if i not in seen:
            seen.add(i)
            ordered.append(i)

    primary = ordered[0]
    trace = list(state.get("routing_trace", []))
    trace.append(f"intents={','.join(ordered)}")
    return {
        "intent": primary,
        "intents": ordered,
        "routing_trace": trace,
        "pending_action": {},
        "citations": [],
    }


def run_specialists(state: AgentState) -> dict[str, Any]:
    """Fan-out: run all selected specialist agents then merge outputs."""
    intents = state.get("intents") or [state.get("intent") or "knowledge"]
    outputs = dict(state.get("agent_outputs") or {})
    used = list(state.get("agents_used") or [])
    trace = list(state.get("routing_trace") or [])
    rag_context = state.get("rag_context") or ""
    pending_action: dict[str, Any] = dict(state.get("pending_action") or {})
    citations = list(state.get("citations") or [])

    if "operations" in intents:
        op = _run_operations(state)
        outputs["operations"] = op["text"]
        used.append("operations")
        trace.append("ran:operations")
        if op.get("pending_action"):
            pending_action = op["pending_action"]

    if "personalization" in intents:
        text = _run_personalization(state)
        outputs["personalization"] = text
        used.append("personalization")
        trace.append("ran:personalization")

    if "knowledge" in intents:
        kn = _run_knowledge(state)
        outputs["knowledge"] = kn["text"]
        rag_context = kn["rag_context"]
        citations = kn.get("citations") or []
        used.append("knowledge")
        trace.append("ran:knowledge")

    return {
        "agent_outputs": outputs,
        "agents_used": used,
        "routing_trace": trace,
        "rag_context": rag_context,
        "pending_action": pending_action,
        "citations": citations,
        "final_response": next(iter(outputs.values()), ""),
    }


def _run_operations(state: AgentState) -> dict[str, Any]:
    plan = finance_toolkit.parse_operation(state["query"], state["external_id"])
    tool_message = plan.get("message", "")
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたは金融アプリの操作サポートAIです。"
                "ツール結果を踏まえ、ユーザー向けに丁寧な日本語で案内してください。"
                "実送金は確認後のみ。リスクと取消可否に触れてください。"
            )
        ),
        HumanMessage(
            content=(
                f"ユーザー: {state['query']}\n"
                f"プロファイル: {state.get('profile_summary', '')}\n"
                f"ツール結果:\n{tool_message}\n"
                "操作サポートとして回答してください。"
            )
        ),
    ]
    result = llm.invoke(prompt)
    text = str(getattr(result, "content", result))
    # Prefer structured tool message when mock LLM is generic
    if "下書き" in tool_message or "残高照会" in tool_message or plan.get("action_type") != "guide":
        text = tool_message if len(tool_message) > 20 else f"{text}\n\n{tool_message}"
    return {"text": text, "pending_action": plan.get("pending_action") or {}}


def _run_personalization(state: AgentState) -> str:
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたは行動データ分析に基づくパーソナライズ提案AIです。"
                "ユーザーの行動・対話履歴サマリを踏まえ、具体的で実行可能な提案を日本語で提示してください。"
            )
        ),
        HumanMessage(
            content=(
                f"ユーザー質問: {state['query']}\n"
                f"プロファイル要約: {state.get('profile_summary', '')}\n"
                "パーソナライズ提案を作成してください。"
            )
        ),
    ]
    result = llm.invoke(prompt)
    return str(getattr(result, "content", result))


def _run_knowledge(state: AgentState) -> dict[str, Any]:
    chunks = rag_service.retrieve(state["query"])
    context = rag_service.format_context(chunks)
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたはナレッジDB連携の対話型サポートAIです。"
                "与えられたコンテキストのみを根拠に正確に回答し、不明点は推測せず確認を促してください。"
            )
        ),
        HumanMessage(
            content=(
                f"質問: {state['query']}\n\n"
                f"Context:\n{context}\n\n"
                "ナレッジに基づく回答を日本語で作成してください。"
            )
        ),
    ]
    result = llm.invoke(prompt)
    text = str(getattr(result, "content", result))
    citations = [c.title for c in chunks[:3]]
    if citations:
        text = f"{text}\n\n参照: {', '.join(citations)}"
    return {"text": text, "rag_context": context, "citations": citations}


def synthesize(state: AgentState) -> dict[str, Any]:
    outputs = state.get("agent_outputs") or {}
    if not outputs:
        return {"final_response": "回答を生成できませんでした。", "messages": [AIMessage(content="")]}

    labels = {
        "operations": "操作サポート",
        "personalization": "パーソナライズ提案",
        "knowledge": "ナレッジ回答",
    }

    if len(outputs) == 1:
        text = next(iter(outputs.values()))
    else:
        # Structured merge keeps tool facts (残高・確認ID) intact under mock LLM
        parts = [
            f"### {labels.get(name, name)}\n{outputs[name]}"
            for name in ("operations", "personalization", "knowledge")
            if name in outputs
        ]
        text = "\n\n".join(parts)

    pending = state.get("pending_action") or {}
    if pending.get("action_id") and pending["action_id"] not in text:
        text = f"{text}\n\n【確認待ち操作】{pending.get('summary', '')}（ID: {pending['action_id']}）"

    used = list(state.get("agents_used", []))
    if "orchestrator" not in used:
        used.append("orchestrator")
    trace = list(state.get("routing_trace", []))
    trace.append("ran:synthesize")
    return {
        "final_response": text,
        "agents_used": used,
        "routing_trace": trace,
        "messages": [AIMessage(content=text)],
    }


# Back-compat aliases used by older imports
def operations_agent(state: AgentState) -> dict[str, Any]:
    return run_specialists({**state, "intents": ["operations"]})


def personalization_agent(state: AgentState) -> dict[str, Any]:
    return run_specialists({**state, "intents": ["personalization"]})


def knowledge_agent(state: AgentState) -> dict[str, Any]:
    return run_specialists({**state, "intents": ["knowledge"]})


def route_by_intent(state: AgentState) -> str:
    return "run_specialists"
