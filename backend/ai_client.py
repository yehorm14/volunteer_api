"""Lazily created OpenAI clients.

Clients are built on first use so the API starts without OPENAI_API_KEY.
The dependencies below return HTTP 503 when the key is missing.
"""
import os
from functools import lru_cache

from fastapi import HTTPException, status
from openai import AsyncOpenAI, OpenAI

AI_DISABLED_DETAIL = "AI features disabled: OPENAI_API_KEY not set"


def _require_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=AI_DISABLED_DETAIL
        )
    return key


@lru_cache
def _sync_client(key: str) -> OpenAI:
    return OpenAI(api_key=key)


@lru_cache
def _async_client(key: str) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=key)


def get_openai_client() -> OpenAI:
    return _sync_client(_require_key())


def get_async_openai_client() -> AsyncOpenAI:
    return _async_client(_require_key())
