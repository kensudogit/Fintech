from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.finance.tools import finance_toolkit
from app.llm.factory import get_chat_model
from app.rag.pipeline import rag_service
from app.tempest.decision import decision_engine
from app.tempest.loan import loan_engine
from app.tempest.matching import matching_engine
from app.tempest.sales import sales_engine
from app.tempest.valuation import valuation_agent

VALID_INTENTS = (
    "operations",
    "personalization",
    "knowledge",
    "loan_screening",
    "b2b_matching",
    "sales_support",
    "decision_structure",
    "value_forecast",
)


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

    if any(
        k in q
        for k in (
            "企業価値",
            "真の企業価値",
            "公正価値",
            "バリュエーション",
            "株価予測",
            "時系列予測",
            "高度予測",
            "センチメント",
            "割安",
            "割高",
            "DCF",
            "EV推定",
        )
    ):
        found.append("value_forecast")
    if any(
        k in q
        for k in (
            "意思決定構造",
            "意思決定を変革",
            "決裁構造",
            "定性・定量",
            "定性定量",
            "エビデンス台帳",
            "シナリオ分岐",
            "反対仮説",
            "与信スタンス",
            "業況判断",
        )
    ):
        found.append("decision_structure")
    if any(k in q for k in ("稟議", "融資審査", "信用審査", "与信", "融資判断", "融資案件", "LN-")):
        found.append("loan_screening")
        if "decision_structure" not in found and any(k in q for k in ("構造", "変革", "統合", "判断枠")):
            found.append("decision_structure")
    if any(k in q for k in ("マッチング", "ビジネスマッチ", "取引先紹介", "企業紹介", "提携先", "マッチ候補")):
        found.append("b2b_matching")
    if any(k in q for k in ("営業支援", "トークスクリプト", "訪問提案", "法人営業", "営業トーク")):
        found.append("sales_support")
    if _wants_operations(q):
        found.append("operations")
    if any(k in q for k in ("おすすめ", "節約", "パーソナライズ", "家計", "改善提案")):
        found.append("personalization")
    elif "提案" in q and "loan_screening" not in found and "b2b_matching" not in found and "sales_support" not in found:
        found.append("personalization")
    if any(k in q for k in ("手数料", "口座開設", "とは", "教えて", "流れ", "不正利用", "FAQ", "知識", "NISA", "審査基準")):
        found.append("knowledge")

    if not found:
        found = ["knowledge"]
    return found


def classify_intent(state: AgentState) -> dict[str, Any]:
    llm = get_chat_model()
    prompt = [
        SystemMessage(
            content=(
                "あなたは金融機関向けAIの意図分類器です。"
                "該当する意図をカンマ区切りで返してください。"
                "候補: operations, personalization, knowledge, loan_screening, b2b_matching, sales_support, decision_structure, value_forecast"
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

    package_payload: dict[str, Any] = dict(state.get("package_payload") or {})

    if "value_forecast" in intents:
        val = _run_value_forecast(state)
        outputs["value_forecast"] = val["text"]
        used.append("value_forecast")
        trace.append("ran:value_forecast")
        package_payload = {"type": "value_forecast", **val["payload"]}

    if "decision_structure" in intents:
        dec = _run_decision_structure(state)
        outputs["decision_structure"] = dec["text"]
        used.append("decision_structure")
        trace.append("ran:decision_structure")
        if package_payload.get("type") != "value_forecast":
            package_payload = {"type": "decision_structure", **dec["payload"]}

    if "loan_screening" in intents:
        loan = _run_loan_screening(state)
        outputs["loan_screening"] = loan["text"]
        used.append("loan_screening")
        trace.append("ran:loan_screening")
        if package_payload.get("type") not in ("value_forecast", "decision_structure"):
            package_payload = {"type": "loan_screening", **loan["payload"]}

    if "b2b_matching" in intents:
        match = _run_b2b_matching(state)
        outputs["b2b_matching"] = match["text"]
        used.append("b2b_matching")
        trace.append("ran:b2b_matching")
        package_payload = {"type": "b2b_matching", **match["payload"]}

    if "sales_support" in intents:
        sales = _run_sales_support(state)
        outputs["sales_support"] = sales["text"]
        used.append("sales_support")
        trace.append("ran:sales_support")
        if not package_payload:
            package_payload = {"type": "sales_support", **sales["payload"]}

    return {
        "agent_outputs": outputs,
        "agents_used": used,
        "routing_trace": trace,
        "rag_context": rag_context,
        "pending_action": pending_action,
        "package_payload": package_payload,
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


def _run_value_forecast(state: AgentState) -> dict[str, Any]:
    result = valuation_agent.analyze(state["query"])
    chunks = rag_service.retrieve(f"企業価値 予測 センチメント {state['query']}")
    policy = rag_service.format_context(chunks[:2]) if chunks else ""
    text = result["message"]
    if policy:
        text = f"{text}\n\n（参考ナレッジ）\n{policy[:400]}"
    return {"text": text, "payload": result}


def _run_decision_structure(state: AgentState) -> dict[str, Any]:
    result = decision_engine.transform(state["query"])
    chunks = rag_service.retrieve(f"意思決定 定性 定量 {state['query']}")
    policy = rag_service.format_context(chunks[:2]) if chunks else ""
    text = result["message"]
    if policy:
        text = f"{text}\n\n（参考ナレッジ）\n{policy[:400]}"
    return {"text": text, "payload": result}


def _run_loan_screening(state: AgentState) -> dict[str, Any]:
    result = loan_engine.analyze(state["query"])
    chunks = rag_service.retrieve(f"融資稟議 審査基準 {state['query']}")
    policy = rag_service.format_context(chunks[:2]) if chunks else ""
    text = result["message"]
    if policy:
        text = f"{text}\n\n（参考ポリシー）\n{policy[:500]}"
    return {"text": text, "payload": result}


def _run_b2b_matching(state: AgentState) -> dict[str, Any]:
    result = matching_engine.search(state["query"])
    return {"text": result["message"], "payload": result}


def _run_sales_support(state: AgentState) -> dict[str, Any]:
    result = sales_engine.support(state["query"])
    return {"text": result["message"], "payload": result}


def synthesize(state: AgentState) -> dict[str, Any]:
    outputs = state.get("agent_outputs") or {}
    if not outputs:
        return {"final_response": "回答を生成できませんでした。", "messages": [AIMessage(content="")]}

    labels = {
        "value_forecast": "TempestAI企業価値・高度予測",
        "decision_structure": "TempestAI意思決定構造",
        "loan_screening": "TempestAI融資稟議",
        "b2b_matching": "TempestAIビジネスマッチング",
        "sales_support": "TempestAI営業支援",
        "operations": "操作サポート",
        "personalization": "パーソナライズ提案",
        "knowledge": "ナレッジ / FAQ",
    }
    order = (
        "value_forecast",
        "decision_structure",
        "loan_screening",
        "b2b_matching",
        "sales_support",
        "operations",
        "personalization",
        "knowledge",
    )

    if len(outputs) == 1:
        text = next(iter(outputs.values()))
    else:
        # Structured merge keeps tool facts intact under mock LLM
        parts = [f"### {labels.get(name, name)}\n{outputs[name]}" for name in order if name in outputs]
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
