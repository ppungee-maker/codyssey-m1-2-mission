// 백엔드 호출만 모은 곳 — 화면 코드(app.js)는 fetch 를 직접 부르지 않고 여기 함수만 쓴다.
// API_BASE_URL 은 config.js 에서 온다.

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body } = {}) {
  const resp = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    const payload = await resp.json().catch(() => ({}));
    // 422 는 [{loc, msg}] 목록, 나머지는 문자열 — 둘 다 한 줄 문장으로
    const detail = Array.isArray(payload.detail)
      ? payload.detail.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join(", ")
      : payload.detail;
    throw new ApiError(detail || `HTTP ${resp.status}`, resp.status);
  }
  return resp.status === 204 ? null : resp.json();
}

const api = {
  summary: () => request("/api/data/summary"),
  listData: () => request("/api/data"),
  addData: (row) => request("/api/data", { method: "POST", body: row }),
  updateData: (id, fields) => request(`/api/data/${encodeURIComponent(id)}`, { method: "PUT", body: fields }),
  deleteData: (id) => request(`/api/data/${encodeURIComponent(id)}`, { method: "DELETE" }),
  listConversations: () => request("/api/conversations"),
  getConversation: (id) => request(`/api/conversations/${encodeURIComponent(id)}`),
  deleteConversation: (id) => request(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
  chat: (message, conversationId) =>
    request("/api/chat", { method: "POST", body: { message, conversation_id: conversationId } }),
};
