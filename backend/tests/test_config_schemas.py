from app.api.schemas import ChatRequest, EvidenceIngestRequest, HealthResponse
from app.config import Settings


def test_settings_defaults():
    s = Settings()
    assert "TempestAI" in s.app_name or "金融" in s.app_name
    assert "asyncpg" in s.database_url or "postgresql" in s.database_url


def test_chat_request_validation():
    req = ChatRequest(message="hello", external_id="demo-user-001")
    assert req.channel == "web"


def test_evidence_schema():
    body = EvidenceIngestRequest(
        kind="qualitative",
        title="t",
        narrative="n",
        decision_relevance="r",
    )
    assert body.persist is True


def test_health_agents_include_evidence():
    h = HealthResponse(status="ok", app="x", llm_provider="mock", rag_documents=0)
    assert "evidence_intake" in h.agents
