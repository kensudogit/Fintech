from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.llm.factory import get_chat_model
from app.rag.pipeline import rag_service


def classify_intent(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたは金融アプリの意図分類器です。"
                "次のいずれか1語のみを返してください: operations / personalization / knowledge"
            )
        ),
        HumanMessage(content=f"ユーザー入力: {state['query']}\nintent を判定してください。"),
    ]
    result = llm.invoke(prompt)
    intent = str(getattr(result, "content", result)).strip().lower()
    if intent not in {"operations", "personalization", "knowledge"}:
        # heuristic fallback
        q = state["query"]
        if any(k in q for k in ("手数料", "口座開設", "とは", "教えて", "流れ", "不正利用")):
            intent = "knowledge"
        elif any(k in q for k in ("提案", "おすすめ", "分析", "節約", "パーソナライズ")):
            intent = "personalization"
        elif any(k in q for k in ("振込して", "送金して", "残高確認", "カード停止", "操作したい")):
            intent = "operations"
        else:
            intent = "knowledge"

    # Prefer knowledge for FAQ-style questions even if mock returns operations
    q = state["query"]
    if any(k in q for k in ("手数料", "口座開設", "とは", "流れ", "不正利用")):
        intent = "knowledge"
    elif any(k in q for k in ("提案", "おすすめ", "分析", "節約", "パーソナライズ")):
        intent = "personalization"

    trace = list(state.get("routing_trace", []))
    trace.append(f"intent={intent}")
    return {"intent": intent, "routing_trace": trace}


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent") or "knowledge"
    if intent == "operations":
        return "operations_agent"
    if intent == "personalization":
        return "personalization_agent"
    return "knowledge_agent"


def operations_agent(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたは金融アプリの操作サポートAIです。"
                "ユーザーの自然言語を解釈し、実行可能な操作候補と必要パラメータを日本語で案内してください。"
                "実際の送金実行は行わず、確認ステップを必ず含めてください。"
            )
        ),
        HumanMessage(
            content=(
                f"ユーザー: {state['query']}\n"
                f"プロファイル: {state.get('profile_summary', '')}\n"
                "操作サポートとして回答してください。"
            )
        ),
    ]
    result = llm.invoke(prompt)
    text = str(getattr(result, "content", result))
    outputs = dict(state.get("agent_outputs", {}))
    outputs["operations"] = text
    used = list(state.get("agents_used", []))
    used.append("operations")
    trace = list(state.get("routing_trace", []))
    trace.append("ran:operations")
    return {
        "agent_outputs": outputs,
        "agents_used": used,
        "routing_trace": trace,
        "messages": [AIMessage(content=text)],
        "final_response": text,
    }


def personalization_agent(state: AgentState) -> dict[str, Any]:
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
    text = str(getattr(result, "content", result))
    outputs = dict(state.get("agent_outputs", {}))
    outputs["personalization"] = text
    used = list(state.get("agents_used", []))
    used.append("personalization")
    trace = list(state.get("routing_trace", []))
    trace.append("ran:personalization")
    return {
        "agent_outputs": outputs,
        "agents_used": used,
        "routing_trace": trace,
        "messages": [AIMessage(content=text)],
        "final_response": text,
    }


def knowledge_agent(state: AgentState) -> dict[str, Any]:
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
    # Attach concise source titles for transparency
    if chunks:
        sources = ", ".join(c.title for c in chunks[:3])
        text = f"{text}\n\n参照: {sources}"

    outputs = dict(state.get("agent_outputs", {}))
    outputs["knowledge"] = text
    used = list(state.get("agents_used", []))
    used.append("knowledge")
    trace = list(state.get("routing_trace", []))
    trace.append("ran:knowledge")
    return {
        "rag_context": context,
        "agent_outputs": outputs,
        "agents_used": used,
        "routing_trace": trace,
        "messages": [AIMessage(content=text)],
        "final_response": text,
    }


def synthesize(state: AgentState) -> dict[str, Any]:
    """Optional multi-agent synthesis when multiple specialists contributed."""
    outputs = state.get("agent_outputs") or {}
    if len(outputs) <= 1:
        return {
            "final_response": state.get("final_response") or next(iter(outputs.values()), ""),
        }

    llm = get_chat_model()
    joined = "\n\n".join(f"[{name}]\n{text}" for name, text in outputs.items())
    prompt = [
        SystemMessage(content="複数エージェントの回答を矛盾なく統合し、簡潔な最終回答を日本語で作成してください。"),
        HumanMessage(content=f"元の質問: {state['query']}\n\n各エージェント出力:\n{joined}"),
    ]
    result = llm.invoke(prompt)
    text = str(getattr(result, "content", result))
    used = list(state.get("agents_used", []))
    used.append("orchestrator")
    trace = list(state.get("routing_trace", []))
    trace.append("ran:synthesize")
    return {
        "final_response": text,
        "agents_used": used,
        "routing_trace": trace,
        "messages": [AIMessage(content=text)],
    }
