import json
import httpx

from app.assistant.tools import TOOL_SCHEMAS, execute_tool

MAX_ITERATIONS = 5


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self._base_url = base_url
        self._model = model

    def chat(self, question: str, session) -> tuple[str, list[str]]:
        """
        Run the agentic tool-calling loop against Ollama.
        Returns (answer, tool_calls_used).
        Raises httpx.ConnectError if Ollama is unreachable.
        """
        messages = [{"role": "user", "content": question}]
        tool_calls_used: list[str] = []

        for _ in range(MAX_ITERATIONS):
            # Send the current conversation state plus the tool catalog.
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "tools": TOOL_SCHEMAS,
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()
            body = response.json()
            msg = body.get("message")
            if msg is None:
                raise ValueError(f"Unexpected Ollama response shape: {body}")

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return msg.get("content", ""), tool_calls_used

            # Preserve the assistant turn so the model can see its own tool request.
            messages.append(msg)

            # Execute each requested tool and feed the JSON result back as a tool message.
            for tc in tool_calls:
                call_id = tc.get("id", "")
                name = tc["function"]["name"]
                args = tc["function"].get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                result = execute_tool(name, args, session)
                tool_calls_used.append(name)
                messages.append({"role": "tool", "tool_call_id": call_id, "content": result})

        return "I could not determine an answer.", tool_calls_used
