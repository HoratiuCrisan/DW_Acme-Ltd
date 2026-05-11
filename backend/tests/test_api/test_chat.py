import httpx
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.api.chat import get_ollama_client, get_llm_log_repo, get_db_session


def test_chat_returns_200():
    mock_client = MagicMock()
    mock_client.chat.return_value = ("AAPL averaged $150.", ["list_instruments", "get_analytics"])
    mock_log_repo = MagicMock()

    app.dependency_overrides[get_ollama_client] = lambda: mock_client
    app.dependency_overrides[get_llm_log_repo] = lambda: mock_log_repo
    app.dependency_overrides[get_db_session] = lambda: MagicMock()

    try:
        client = TestClient(app)
        response = client.post("/chat", json={"question": "What was AAPL's average close?"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "AAPL averaged $150."
        assert data["tool_calls_used"] == ["list_instruments", "get_analytics"]
        assert isinstance(data["duration_ms"], int)
    finally:
        app.dependency_overrides.pop(get_ollama_client, None)
        app.dependency_overrides.pop(get_llm_log_repo, None)
        app.dependency_overrides.pop(get_db_session, None)


def test_chat_returns_503_when_ollama_down():
    mock_client = MagicMock()
    mock_client.chat.side_effect = httpx.ConnectError("Connection refused")
    mock_log_repo = MagicMock()

    app.dependency_overrides[get_ollama_client] = lambda: mock_client
    app.dependency_overrides[get_llm_log_repo] = lambda: mock_log_repo
    app.dependency_overrides[get_db_session] = lambda: MagicMock()

    try:
        client = TestClient(app)
        response = client.post("/chat", json={"question": "What was AAPL's average close?"})
        assert response.status_code == 503
        assert "Ollama unavailable" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_ollama_client, None)
        app.dependency_overrides.pop(get_llm_log_repo, None)
        app.dependency_overrides.pop(get_db_session, None)
