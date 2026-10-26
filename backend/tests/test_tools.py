from services.tools import QUERY_LIMIT, TOOLS, run_tool


def test_tool_names_match_runner(client):
    for tool in TOOLS:
        assert "error" not in run_tool(tool["function"]["name"], {"date_from": "2026-01-01", "date_to": "2026-01-02"} if tool["function"]["name"] == "query_data" else {})


def test_query_range_is_inclusive_and_sorted(client):
    r = run_tool("query_data", {"date_from": "2026-08-31", "date_to": "2026-09-02"})
    assert [row["date"] for row in r["rows"]] == ["2026-08-31", "2026-09-01", "2026-09-02"]


def test_query_is_capped(client):
    r = run_tool("query_data", {"date_from": "2024-01-01", "date_to": "2026-12-31"})
    assert r["count"] == 502 and r["truncated"] and len(r["rows"]) == QUERY_LIMIT


def test_bad_arguments_come_back_as_error_not_exception(client):
    assert "error" in run_tool("query_data", {"date_from": "어제", "date_to": "2026-01-01"})
    assert "error" in run_tool("query_data", {"date_from": "2026-02-01", "date_to": "2026-01-01"})
    assert "error" in run_tool("get_summary", {"days": 0})
    assert "error" in run_tool("delete_all", {})


def test_tools_are_read_only(client):
    before = client.get("/api/data/summary").json()["count"]
    for tool in TOOLS:
        name = tool["function"]["name"]
        run_tool(name, {"date_from": "2024-01-01", "date_to": "2026-12-31"} if name == "query_data" else {})
    assert client.get("/api/data/summary").json()["count"] == before
