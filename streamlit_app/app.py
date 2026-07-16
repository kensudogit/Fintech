from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8080").rstrip("/")

st.set_page_config(page_title="Fintech AI Console", page_icon="💹", layout="wide")
st.title("Fintech AI Console")
st.caption("マルチエージェント / RAG / パーソナライズ の運用ダッシュボード")

with st.sidebar:
    st.header("接続設定")
    api_base = st.text_input("API Base URL", API_BASE)
    external_id = st.text_input("User External ID", "demo-user-001")
    st.divider()
    if st.button("Health Check"):
        try:
            r = httpx.get(f"{api_base}/api/v1/health", timeout=10)
            st.json(r.json())
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))


tab_chat, tab_events, tab_suggest, tab_knowledge = st.tabs(
    ["対話 AI", "行動イベント", "パーソナライズ提案", "ナレッジ DB"]
)

with tab_chat:
    st.subheader("自然言語サポート（オーケストレーション）")
    message = st.text_area(
        "メッセージ",
        "振込手数料について教えて。あと家計の改善提案もほしい。",
        height=120,
    )
    if st.button("送信", type="primary"):
        with st.spinner("エージェント実行中..."):
            r = httpx.post(
                f"{api_base}/api/v1/chat",
                json={"message": message, "external_id": external_id, "channel": "streamlit"},
                timeout=60,
            )
            if r.status_code >= 400:
                st.error(r.text)
            else:
                data = r.json()
                st.success(data.get("answer", ""))
                c1, c2, c3 = st.columns(3)
                c1.metric("Intent", data.get("intent") or "-")
                c2.metric("Latency (ms)", data.get("latency_ms") or 0)
                c3.write("Agents")
                c3.code(", ".join(data.get("agents_used") or []))
                with st.expander("Routing trace"):
                    st.json(data.get("routing_trace") or [])
                with st.expander("RAG context"):
                    st.text(data.get("rag_context") or "")

with tab_events:
    st.subheader("行動データ登録")
    event_type = st.selectbox(
        "event_type",
        ["transfer", "invest_view", "expense", "login", "card_use", "dialogue"],
    )
    category = st.text_input("payload.category", "飲食")
    product = st.text_input("payload.product", "つみたてNISA")
    amount = st.number_input("payload.amount", min_value=0, value=1200)
    if st.button("イベント送信"):
        payload = {"category": category, "product": product, "amount": amount}
        r = httpx.post(
            f"{api_base}/api/v1/events",
            json={"external_id": external_id, "event_type": event_type, "payload": payload},
            timeout=30,
        )
        st.json(r.json())

with tab_suggest:
    st.subheader("パーソナライズ提案")
    if st.button("提案を取得"):
        r = httpx.get(f"{api_base}/api/v1/users/{external_id}/suggestions", timeout=30)
        data = r.json()
        st.write(data.get("profile_summary"))
        st.metric("Activity Score", data.get("activity_score", 0))
        st.write("Interests", data.get("interests"))
        for s in data.get("suggestions", []):
            st.info(s)

with tab_knowledge:
    st.subheader("ナレッジ一覧 / 再インデックス")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("一覧取得"):
            r = httpx.get(f"{api_base}/api/v1/knowledge", timeout=30)
            rows = r.json()
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.warning("ナレッジがありません")
    with col_b:
        if st.button("RAG 再構築"):
            r = httpx.post(f"{api_base}/api/v1/rag/reindex", timeout=60)
            st.json(r.json())

    st.markdown("---")
    st.subheader("ナレッジ追加")
    title = st.text_input("title", "新しいFAQ")
    category_k = st.text_input("category", "faq")
    source = st.text_input("source", "manual")
    content = st.text_area("content", "ここにナレッジ本文を入力")
    if st.button("取り込み"):
        r = httpx.post(
            f"{api_base}/api/v1/knowledge",
            json={
                "title": title,
                "category": category_k,
                "source": source,
                "content": content,
            },
            timeout=30,
        )
        st.json(r.json())
