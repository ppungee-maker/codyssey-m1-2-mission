"""보너스 — MCP 서버: 같은 AI 비서를 Claude Desktop 같은 MCP 클라이언트에서도 쓴다(멀티채널).

웹 화면과 같은 백엔드 API 를 부른다 — 데이터·대화가 한 곳(Firestore)에 쌓인다.

  get_summary(days?)              요약             → GET  /api/data/summary
  query_data(date_from, date_to)  날짜 범위 값      → GET  /api/data (여기서 걸러냄)
  add_data(date, value, memo?)    데이터 추가       → POST /api/data
  ask(message)                    AI 비서에게 질문  → POST /api/chat (대화 기록에도 남는다)

웹 챗봇의 도구(backend/services/tools.py)는 읽기 전용인데 여기엔 add_data 가 있다. MCP 클라이언트는
도구를 부를 때마다 사람에게 허락을 받으니, 쓰기도 사람이 보고 누른 것만 일어난다.

실행(클라이언트가 띄운다): API_BASE_URL=<백엔드 주소> python mcp_server/server.py
"""

from __future__ import annotations

import os
from datetime import date

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
QUERY_LIMIT = 100

mcp = MCPServer(
    "ai-assistant",
    instructions="사용자가 저장한 시계열 데이터(날짜·값·메모)를 요약·조회·추가하고 AI 비서에게 묻는다.",
)


def _client() -> httpx.Client:
    # 무료 서버(Render)가 잠들어 있으면 깨어나는 데 1분 가까이 걸린다
    return httpx.Client(base_url=API_BASE_URL, timeout=70)


def _call(method: str, path: str, **kw) -> dict | list:
    with _client() as c:
        r = c.request(method, path, **kw)
    if r.status_code >= 400:
        detail = r.json().get("detail") if "json" in r.headers.get("content-type", "") else r.text
        # ToolError 는 메시지가 클라이언트(AI)까지 간다 — 다른 예외는 「도구 실행 오류」로만 보인다
        raise ToolError(f"{method} {path} → {r.status_code}: {detail}")
    return r.json()


@mcp.tool()
def get_summary(days: int | None = None) -> dict:
    """데이터 요약 — 건수·기간·평균·최고·최저·표준편차·마지막 값·추세. days 를 주면 최근 N일만."""
    if days is not None and not 1 <= days <= 3650:
        raise ToolError("days 는 1~3650 사이여야 합니다")
    return _call("GET", "/api/data/summary", params={"days": days} if days is not None else None)


@mcp.tool()
def query_data(date_from: date, date_to: date) -> dict:
    """날짜 범위(양 끝 포함)의 값 {date, value, memo} — 날짜순, 최대 100건."""
    if date_from > date_to:
        # 「0건」 으로 답하면 AI 가 「데이터가 없다」 로 오해한다 — 인자 오류로 알린다
        raise ToolError("date_from 이 date_to 보다 늦습니다")
    rows = [
        {"date": r["date"], "value": r["value"], "memo": r.get("memo")}
        for r in _call("GET", "/api/data")
        if date_from.isoformat() <= r["date"] <= date_to.isoformat()
    ]
    return {"count": len(rows), "truncated": len(rows) > QUERY_LIMIT, "rows": rows[:QUERY_LIMIT]}


@mcp.tool()
def add_data(date: date, value: float, memo: str | None = None) -> dict:
    """데이터 1건 추가 — 웹 화면 「데이터 관리」의 [추가] 와 같다."""
    return _call("POST", "/api/data", json={"date": date.isoformat(), "value": value, "memo": memo})


@mcp.tool()
def ask(message: str, conversation_id: str | None = None) -> dict:
    """AI 비서에게 질문 — 웹 채팅과 같은 답(요약 주입·도구 사용). 대화 기록에도 저장된다."""
    return _call("POST", "/api/chat", json={"message": message, "conversation_id": conversation_id})


if __name__ == "__main__":
    mcp.run()  # stdio — MCP 클라이언트가 이 프로세스를 띄워 표준입출력으로 말한다
