from app.llm.mock import MockChatModel, MockEmbeddings


def test_embeddings_deterministic():
    emb = MockEmbeddings(dim=32)
    a = emb.embed_query("融資 稟議")
    b = emb.embed_query("融資 稟議")
    assert a == b
    assert len(a) == 32


def test_chat_intent_classification():
    llm = MockChatModel()

    class Msg:
        def __init__(self, content: str) -> None:
            self.content = content

    out = llm.invoke(
        [
            Msg("意図を判定してください"),
            Msg("ユーザー入力: 企業価値を推定して\nintents を判定してください。"),
        ]
    )
    assert "value_forecast" in out.content
