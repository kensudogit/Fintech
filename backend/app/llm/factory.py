from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.llm.mock import MockChatModel, MockEmbeddings


def get_chat_model() -> Any:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "openai" and settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key, temperature=0.2)

    if provider == "google" and settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=settings.llm_model, google_api_key=settings.google_api_key, temperature=0.2)

    return MockChatModel()


def get_embeddings() -> Any:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "openai" and settings.openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)

    if provider == "google" and settings.google_api_key:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=settings.google_api_key)

    return MockEmbeddings()
