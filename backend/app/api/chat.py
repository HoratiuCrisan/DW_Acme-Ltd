import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from app.assistant.client import OllamaClient
from app.config import settings
from app.db.connection import get_session
from backend.app.db.repositories.llm_query_log import LLMQueryLogRepository
from app.models.llm_query_log import LLMQueryLog

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    user_id: UUID | None = None
    session_id: UUID | None = None


class ChatResponse(BaseModel):
    answer: str
    tool_calls_used: list[str]
    duration_ms: int


def get_ollama_client() -> OllamaClient:
    return OllamaClient(base_url=settings.ollama_base_url, model=settings.ollama_model)


def get_db_session():
    return get_session()


def get_llm_log_repo(db_session=Depends(get_db_session)) -> LLMQueryLogRepository:
    return LLMQueryLogRepository(db_session)


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    client: OllamaClient = Depends(get_ollama_client),
    log_repo: LLMQueryLogRepository = Depends(get_llm_log_repo),
    db_session = Depends(get_db_session),
):
    user_id = request.user_id or uuid.uuid4()
    session_id = request.session_id or uuid.uuid4()
    asked_at = datetime.now(timezone.utc)
    start_ms = int(time.time() * 1000)

    try:
        answer, tool_calls_used = client.chat(request.question, db_session)
    except httpx.ConnectError as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.status_code}")

    duration_ms = int(time.time() * 1000) - start_ms

    try:
        log_repo.save(LLMQueryLog(
            user_id=user_id,
            session_id=session_id,
            asked_at=asked_at,
            query_id=uuid.uuid4(),
            user_prompt=request.question,
            tools_invoked=", ".join(tool_calls_used) if tool_calls_used else None,
            llm_response=answer,
            duration_ms=duration_ms,
        ))
    except Exception as exc:
        logger.warning("LLM audit log write failed: %s", exc)

    return ChatResponse(
        answer=answer,
        tool_calls_used=tool_calls_used,
        duration_ms=duration_ms,
    )
