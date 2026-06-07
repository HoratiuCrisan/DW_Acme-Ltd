from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.db.connection import get_session
from app.mcp.tools import MCPToolError, TOOL_DEFINITIONS, execute_mcp_tool

router = APIRouter()

JSONRPC_VERSION = "2.0"


class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION)
    id: int | str | None = None
    method: str
    params: dict[str, Any] | None = None


def get_db_session():
    return get_session()


@router.post("")
def mcp_json_rpc(rpc_request: JsonRpcRequest, request: Request):
    if rpc_request.jsonrpc != JSONRPC_VERSION:
        return _error(rpc_request.id, -32600, "Invalid Request", "jsonrpc must be '2.0'")

    if rpc_request.method == "initialize":
        return _result(rpc_request.id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "acme-warehouse-mcp", "version": "0.1.0"},
            "capabilities": {"tools": {}},
        })

    if rpc_request.method == "tools/list":
        return _result(rpc_request.id, {"tools": TOOL_DEFINITIONS})

    if rpc_request.method == "tools/call":
        params = rpc_request.params or {}
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            return _error(rpc_request.id, -32602, "Invalid params", "params.name is required")
        try:
            session_factory = request.app.dependency_overrides.get(get_db_session, get_db_session)
            db_session = session_factory()
            structured = execute_mcp_tool(name, arguments, db_session)
        except MCPToolError as exc:
            code = -32602 if exc.code == "invalid_params" else -32004
            return _error(rpc_request.id, code, exc.code, str(exc))
        return _result(rpc_request.id, {
            "content": [{"type": "text", "text": f"{name} returned structured data"}],
            "structuredContent": structured,
            "isError": False,
        })

    return _error(rpc_request.id, -32601, "Method not found", rpc_request.method)


def _result(request_id, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _error(request_id, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": error}
