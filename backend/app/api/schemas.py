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
    intents: list[str] = []
    answer: str
    agents_used: list[str] = []
    routing_trace: list[str] = []
    rag_context: str = ""
    citations: list[str] = []
    pending_action: dict[str, Any] | None = None
    package_payload: dict[str, Any] | None = None
    agent_outputs: dict[str, str] = Field(default_factory=dict)
    latency_ms: int = 0
    profile_summary: str | None = None
    product: str | None = None


class LoanAnalyzeRequest(BaseModel):
    query: str = Field(default="融資稟議を審査して", min_length=1, max_length=4000)
    application_id: str | None = None


class MatchingSearchRequest(BaseModel):
    query: str = Field(default="ビジネスマッチング候補を出して", min_length=1, max_length=4000)
    source_company_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=5)


class DecisionTransformRequest(BaseModel):
    query: str = Field(
        default="定性・定量を統合して意思決定構造を変革して",
        min_length=1,
        max_length=4000,
    )
    case_id: str | None = None


class ValuationAnalyzeRequest(BaseModel):
    query: str = Field(
        default="ノースウィンド製造の企業価値を推定して",
        min_length=1,
        max_length=4000,
    )
    ticker: str | None = None
    horizon_months: int = Field(default=6, ge=1, le=12)


class EvidenceIngestRequest(BaseModel):
    """Structured evidence that improves decision quality (qual + quant)."""

    kind: str = Field(default="qualitative", description="quantitative | qualitative | news | note")
    title: str = Field(..., min_length=1, max_length=256)
    case_id: str | None = Field(default=None, description="DEC-* or null for global")
    source: str = "user_input"
    submitted_by: str = "demo-user-001"
    decision_relevance: str = Field(
        default="",
        description="この情報が意思決定にどう利するか",
        max_length=1000,
    )
    weight: float = Field(default=1.0, ge=0.1, le=3.0)
    # quantitative
    value: float | None = None
    unit: str | None = None
    trend: str | None = None
    # qualitative / news / note
    narrative: str | None = Field(default=None, max_length=8000)
    polarity: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    persist: bool = Field(default=True, description="PostgreSQL ナレッジにも保存")


class EvidenceFreeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    case_id: str | None = None
    source: str = "user_input"
    submitted_by: str = "demo-user-001"
    decision_relevance: str = ""
    persist: bool = True
    run_transform: bool = Field(
        default=False,
        description="投入後に意思決定構造エンジンを再実行する",
    )


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


class ConfirmActionRequest(BaseModel):
    action_id: str
    external_id: str = "demo-user-001"


class HealthResponse(BaseModel):
    status: str
    app: str
    product: str = "TempestAI｜金融AIパッケージ"
    llm_provider: str
    rag_documents: int
    agents: list[str] = [
        "operations",
        "personalization",
        "knowledge",
        "loan_screening",
        "b2b_matching",
        "sales_support",
        "decision_structure",
        "value_forecast",
        "evidence_intake",
        "orchestrator",
    ]
    packages: list[str] = [
        "tempest-valuation",
        "tempest-decision",
        "tempest-loan",
        "tempest-matching",
        "tempest-ops",
    ]
