"""MCP 서버 도구를 실제 백엔드 앱(메모리 저장소 + mock AI)에 붙여 부른다 — 네트워크 없이."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "mcp_server")]
for key in ("OPENAI_API_KEY", "FIREBASE_CREDENTIALS_JSON", "FIREBASE_PROJECT_ID"):
    os.environ[key] = ""

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from main import app  # noqa: E402
from repositories import store  # noqa: E402
from seed import seed_if_empty  # noqa: E402


@pytest.fixture(autouse=True)
def backend(monkeypatch):
    store.__init__()
    seed_if_empty(store)
    monkeypatch.setattr(server, "_client", lambda: TestClient(app))


def call(name, **args):
    result = asyncio.run(server.mcp.call_tool(name, args))
    assert not result.is_error, result
    return json.loads(result.content[0].text)


def test_lists_four_tools():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == {"get_summary", "query_data", "add_data", "ask"}


def test_summary_and_query():
    assert call("get_summary")["count"] == 502
    assert call("get_summary", days=30)["basis"] == "최근 30일"
    rows = call("query_data", date_from="2026-09-01", date_to="2026-09-02")["rows"]
    assert [r["value"] for r in rows] == [217.44, 224.41]


def test_add_then_ask_uses_same_backend():
    call("add_data", date="2026-10-01", value=300.5, memo="MCP 로 추가")
    assert call("get_summary")["count"] == 503
    r = call("ask", message="2026-10-01 값은?")
    assert "300.5" in r["answer"] and r["tools_used"][0]["name"] == "query_data"
    assert any(c["id"] == r["conversation_id"] for c in TestClient(app).get("/api/conversations").json())


def test_backend_error_is_reported():
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError, match="422.*memo"):
        asyncio.run(server.mcp.call_tool("add_data", {"date": "2026-10-01", "value": 1, "memo": "가" * 201}))


@pytest.mark.parametrize(
    "name,args,match",
    [
        ("get_summary", {"days": 0}, "1~3650"),
        ("query_data", {"date_from": "2026-09-02", "date_to": "2026-09-01"}, "늦습니다"),
    ],
)
def test_bad_arguments_are_tool_errors(name, args, match):
    from mcp.server.mcpserver.exceptions import ToolError

    with pytest.raises(ToolError, match=match):
        asyncio.run(server.mcp.call_tool(name, args))
