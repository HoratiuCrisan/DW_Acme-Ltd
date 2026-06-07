from unittest.mock import MagicMock, patch

from app.assistant.client import OllamaClient


def _make_client() -> OllamaClient:
    return OllamaClient(base_url="http://localhost:11434", model="llama3.2")


def _make_resp(content=None, tool_calls=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    msg = {"role": "assistant"}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    resp.json.return_value = {"message": msg}
    return resp


def test_single_turn_no_tools():
    """Ollama responds with text immediately — no tool calls."""
    mock_resp = _make_resp(content="The answer is 42.")

    with patch("httpx.post", return_value=mock_resp):
        answer, tools_used = _make_client().chat("Question?", session=None)

    assert answer == "The answer is 42."
    assert tools_used == []


def test_one_tool_call_then_answer():
    """Ollama requests one tool call, then gives a final text answer."""
    tool_resp = _make_resp(tool_calls=[
        {"function": {"name": "list_instruments", "arguments": {}}}
    ])
    answer_resp = _make_resp(content="Here are the instruments.")

    mock_session = MagicMock()

    with patch("httpx.post", side_effect=[tool_resp, answer_resp]):
        with patch("app.assistant.client.execute_tool", return_value='[]') as mock_exec:
            answer, tools_used = _make_client().chat("List all instruments", session=mock_session)

    assert answer == "Here are the instruments."
    assert tools_used == ["list_instruments"]
    mock_exec.assert_called_once_with("list_instruments", {}, mock_session)


def test_max_iterations_returns_fallback():
    """When Ollama always returns tool calls, loop exits after MAX_ITERATIONS."""
    tool_resp = _make_resp(tool_calls=[
        {"function": {"name": "list_instruments", "arguments": {}}}
    ])

    with patch("httpx.post", return_value=tool_resp):
        with patch("app.assistant.client.execute_tool", return_value="[]"):
            answer, tools_used = _make_client().chat("Loop forever", session=MagicMock())

    assert answer == "I could not determine an answer."
    assert len(tools_used) == 5  # MAX_ITERATIONS
