// 백엔드 호출만 모은 곳 — 화면 코드(app.js)는 fetch 를 직접 부르지 않고 여기 함수만 쓴다.
// API_BASE_URL 은 config.js 에서 온다.

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// 응답을 이 시간까지만 기다린다 — 무료 서버가 깨어나는 데 30초~1분이 걸려서 넉넉히
const TIMEOUT_MS = 70000;

async function request(path, { method = "GET", body, timeoutMs = TIMEOUT_MS } = {}) {
  let resp;
  try {
    resp = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    const timedOut = err.name === "TimeoutError";
    throw new ApiError(timedOut ? "서버 응답이 너무 늦습니다. 잠시 후 다시 시도해 주세요." : "서버에 연결하지 못했습니다.", 0);
  }
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

// 콜드스타트 대응: 무료 서버(Render)는 15분 넘게 요청이 없으면 잠든다. 첫 요청은 서버가
// 깨어날 때까지 걸리거나, 깨어나는 동안 502·503 이 올 수 있다 → 상태 확인(GET /)을 몇 번
// 다시 해서 깨운 뒤에 화면 데이터를 받는다. 깨어 있으면 바로 끝난다.
async function wakeServer({ tries = 6, waitMs = 5000 } = {}) {
  for (let i = 1; ; i++) {
    try {
      return await request("/", { timeoutMs: 60000 });
    } catch (err) {
      const retryable = err.status === 0 || err.status === 502 || err.status === 503;
      if (!retryable || i >= tries) throw err;
      await new Promise((r) => setTimeout(r, waitMs));
    }
  }
}

const api = {
  wake: wakeServer,
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
