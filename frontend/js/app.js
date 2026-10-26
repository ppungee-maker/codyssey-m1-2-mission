// 바닐라 JS — 프레임워크 없음(요구사항). 서버 호출은 api.js 의 api.* 만 쓴다.
//
// 화면 상태는 하나뿐이다: 지금 보고 있는 대화 id(currentConversationId).
//   - 대화 목록에서 고르면 → 그 id 로 바꾸고 메시지를 불러온다
//   - 「새 대화」 → null. 다음 질문에서 서버가 새 id 를 만들어 돌려준다
//   - 데이터를 추가·수정·삭제하면 → 요약 막대와 목록을 다시 받는다(요약은 서버가 계산)
//
// 사용자·AI 가 쓴 글(메모·대화 제목·메시지)은 전부 textContent 로 넣는다. innerHTML 에
// 넣으면 메모에 <img onerror=…> 같은 글을 저장했을 때 그 스크립트가 실행된다.

let currentConversationId = null;
let dataLoaded = false; // 첫 데이터 목록을 받았는가 — 그 전엔 그래프를 그리지 않는다(스켈레톤 유지)
// 화면에 띄운 대화가 바뀔 때마다 1씩 올린다. 요청을 보낼 때의 값을 기억해 두었다가, 응답이
// 왔을 때 값이 달라졌으면(그새 새 대화·다른 대화로 옮김) 그 응답으로 화면을 바꾸지 않는다.
let viewGeneration = 0;

const $ = (id) => document.getElementById(id);

// 태그·속성·자식으로 요소를 만든다. 문자열 자식은 글자로만 들어간다(HTML 로 해석 안 됨).
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  node.append(...children.filter((c) => c != null));
  return node;
}

function showError(err) {
  const box = $("error");
  box.textContent = `오류: ${err.message}`;
  box.hidden = false;
  clearTimeout(showError.timer);
  showError.timer = setTimeout(() => (box.hidden = true), 6000);
}

// 버튼 핸들러 공통 — 실패하면 화면 위에 알린다(조용히 삼키지 않는다)
const guarded = (fn) => async (...args) => {
  try {
    await fn(...args);
  } catch (err) {
    showError(err);
  }
};

// --- 데이터 요약 ---
async function refreshSummary() {
  const s = await api.summary();
  // 처음 불러오는 동안 보이던 회색 자리(스켈레톤)를 걷어 낸다
  document.querySelectorAll(".summary-card .skeleton").forEach((n) => n.classList.remove("skeleton"));
  $("s-count").textContent = `${s.count}건`;
  $("s-period").textContent = s.date_from ? `${s.date_from} ~ ${s.date_to}` : "-";
  $("s-mean").textContent = s.mean != null ? s.mean.toFixed(2) : "-";
  $("s-maxmin").textContent = s.max != null ? `${s.max.toFixed(1)} / ${s.min.toFixed(1)}` : "-";
  $("s-stdev").textContent = s.stdev != null ? s.stdev.toFixed(2) : "-";
  $("s-trend").textContent = s.trend;
  $("s-trend").title = s.trend_detail;
}

// --- 보너스: 추이 그래프 ---
// 기간 버튼은 그래프 범위만 바꾼다(마지막 데이터 날짜 기준 최근 N일, 0 = 전체).
let chartDays = 90;

function renderChart() {
  // 첫 목록이 오기 전(기간 버튼·창 크기 변경)엔 「데이터 없음」 을 그리지 않고 스켈레톤을 둔다
  if (!dataLoaded) return;
  $("chart").classList.remove("skeleton-box");
  const rows = lastRows;
  let points = rows.map((r) => ({ date: r.date, value: r.value }));
  if (chartDays && points.length) {
    // "YYYY-MM-DD" 는 UTC 자정으로 읽힌다 — 날짜 빼기도 UTC 로 해야 서머타임 지역에서 첫날이 안 빠진다
    const start = new Date(points.at(-1).date);
    start.setUTCDate(start.getUTCDate() - (chartDays - 1));
    const from = start.toISOString().slice(0, 10);
    points = points.filter((p) => p.date >= from);
  }
  drawLineChart($("chart"), points);
}

// 화면 폭이 바뀌면(회전·창 크기) 그 폭에 맞춰 다시 그린다
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderChart, 150);
});

document.querySelectorAll(".range button").forEach((btn) =>
  btn.addEventListener("click", () => {
    chartDays = Number(btn.dataset.days);
    document.querySelectorAll(".range button").forEach((b) => b.classList.toggle("active", b === btn));
    renderChart();
  }),
);

// --- 데이터 관리(CRUD) ---
// 최근 것부터 PAGE 건씩 보여 준다(시드만 502건). 「더 보기」로 늘린다.
const PAGE = 15;
let shown = PAGE;
let editingId = null; // 지금 수정 중인 행 — 한 번에 하나만

function viewRow(r) {
  return el(
    "li",
    {},
    el("span", { class: "row-text" }, `${r.date} · ${r.value}${r.memo ? ` · ${r.memo}` : ""}`),
    el(
      "span",
      { class: "row-actions" },
      el("button", { type: "button", onclick: () => startEdit(r.id) }, "수정"),
      el("button", { type: "button", onclick: guarded(() => deleteData(r.id)) }, "삭제"),
    ),
  );
}

function editRow(r) {
  const date = el("input", { type: "date", value: r.date, required: "", "aria-label": "날짜" });
  const value = el("input", { type: "number", step: "any", value: String(r.value), required: "", "aria-label": "값" });
  const memo = el("input", { type: "text", value: r.memo ?? "", maxlength: "200", placeholder: "메모", "aria-label": "메모" });
  const form = el(
    "form",
    {
      class: "edit-form",
      onsubmit: guarded(async (e) => {
        e.preventDefault();
        await api.updateData(r.id, { date: date.value, value: Number(value.value), memo: memo.value.trim() || null });
        editingId = null;
        await refreshData();
      }),
    },
    date,
    value,
    memo,
    el(
      "span",
      { class: "row-actions" },
      el("button", { type: "submit" }, "저장"),
      el("button", { type: "button", onclick: () => cancelEdit() }, "취소"),
    ),
  );
  return el("li", { class: "editing" }, form);
}

let lastRows = [];

function renderDataList() {
  const recent = lastRows.slice(-shown).reverse();
  $("data-list").replaceChildren(...recent.map((r) => (r.id === editingId ? editRow(r) : viewRow(r))));
  $("data-count-hint").textContent = `전체 ${lastRows.length}건 중 최근 ${recent.length}건 표시`;
  $("data-more").hidden = recent.length >= lastRows.length;
}

function startEdit(id) {
  editingId = id;
  renderDataList();
  $("data-list").querySelector(".editing input")?.focus();
}

function cancelEdit() {
  editingId = null;
  renderDataList();
}

async function refreshDataList() {
  lastRows = await api.listData();
  dataLoaded = true;
  renderDataList();
  renderChart();
  return lastRows;
}

async function refreshData() {
  await Promise.all([refreshDataList(), refreshSummary()]);
}

async function deleteData(id) {
  if (!confirm("이 데이터를 삭제할까요?")) return;
  await api.deleteData(id);
  await refreshData();
}

$("data-more").addEventListener("click", () => {
  shown += PAGE;
  renderDataList();
});

$("data-form").addEventListener(
  "submit",
  guarded(async (e) => {
    e.preventDefault();
    await api.addData({
      date: $("data-date").value,
      value: Number($("data-value").value),
      memo: $("data-memo").value.trim() || null,
    });
    $("data-form").reset();
    $("data-date").value = today();
    await refreshData();
  }),
);

// --- 대화 기록 ---
async function refreshConversationList() {
  const rows = await api.listConversations();
  const items = rows.map((r) =>
    el(
      "li",
      {
        class: r.id === currentConversationId ? "active" : "",
        onclick: guarded(() => loadConversation(r.id)),
      },
      el("span", {}, `${r.title} (${r.message_count})`),
      el(
        "button",
        {
          type: "button",
          class: "del",
          "aria-label": "대화 삭제",
          onclick: guarded(async (e) => {
            e.stopPropagation();
            await api.deleteConversation(r.id);
            if (currentConversationId === r.id) startNewChat();
            await refreshConversationList();
          }),
        },
        "×",
      ),
    ),
  );
  $("conversation-list").replaceChildren(
    ...(items.length ? items : [el("li", { class: "hint empty" }, "아직 대화가 없습니다")]),
  );
}

function bubble(role, content) {
  return el("div", { class: `msg ${role}` }, content);
}

// 보너스: AI 가 답을 만들며 부른 도구를 답 아래에 작게 보여 준다 — 「추측이 아니라 찾아봤다」가 보이게
function answerBubble(resp) {
  const node = bubble("assistant", resp.answer);
  for (const t of resp.tools_used ?? []) {
    const args = Object.entries(t.arguments).map(([k, v]) => `${k}=${v}`).join(", ");
    node.append(el("div", { class: "tool-used" }, `도구 사용: ${t.name}(${args})`));
  }
  return node;
}

async function loadConversation(id) {
  const generation = ++viewGeneration;
  const conv = await api.getConversation(id);
  if (generation !== viewGeneration) return; // 그새 다른 대화를 눌렀다
  currentConversationId = conv.id;
  $("messages").replaceChildren(...conv.messages.map((m) => bubble(m.role, m.content)));
  scrollMessages();
  await refreshConversationList();
}

function startNewChat() {
  viewGeneration++;
  currentConversationId = null;
  $("messages").replaceChildren();
  refreshConversationList().catch(showError);
}
$("new-chat-btn").addEventListener("click", startNewChat);

function scrollMessages() {
  $("messages").scrollTop = $("messages").scrollHeight;
}

// --- 채팅 ---
$("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("chat-input");
  const message = input.value.trim();
  if (!message) return;

  const box = $("messages");
  box.append(bubble("user", message));
  input.value = "";
  const submit = e.target.querySelector("button");
  submit.disabled = true;

  const loading = bubble("assistant loading", "생각하는 중...");
  box.append(loading);
  scrollMessages();
  // 오래 걸리면 이유를 알려 준다(서버가 잠들어 있었거나 AI 가 느릴 때)
  const slow = setTimeout(() => {
    loading.textContent = "생각하는 중... 서버가 깨어나는 중이면 1분쯤 걸릴 수 있어요.";
  }, 6000);

  const generation = viewGeneration;
  try {
    const resp = await api.chat(message, currentConversationId);
    // 기다리는 동안 다른 대화로 옮겼으면 답은 서버의 원래 대화에 저장돼 있다 — 지금 화면엔
    // 넣지 않고 목록(메시지 수)만 갱신한다. 넣으면 다음 질문이 엉뚱한 대화로 간다.
    if (generation === viewGeneration) {
      currentConversationId = resp.conversation_id;
      loading.replaceWith(answerBubble(resp));
      await refreshConversationList();
    } else if (currentConversationId === resp.conversation_id) {
      // 다른 대화에 갔다가 이 대화로 돌아와 있다 — 저장된 답까지 다시 불러온다
      await loadConversation(resp.conversation_id);
    } else {
      await refreshConversationList();
    }
  } catch (err) {
    loading.textContent = `오류: ${err.message}`;
    loading.classList.remove("loading");
  } finally {
    clearTimeout(slow);
    submit.disabled = false;
    scrollMessages();
  }
});

// --- 보너스: 다크 모드 ---
$("theme-toggle").addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try {
    localStorage.setItem("theme", next);
  } catch {
    // 사생활 보호 모드 등에서 저장이 막혀도 전환은 된다
  }
});

// --- 보너스: 데이터 CSV 내보내기 ---
function csvCell(value) {
  // 숫자는 그대로 — 음수(-2.5)에 ' 를 붙이면 엑셀이 글자로 읽는다
  if (typeof value === "number") return String(value);
  const text = String(value ?? "");
  // 엑셀이 =·+·-·@ 로 시작하는 칸(앞에 공백·탭 같은 제어 문자가 있어도)을 수식으로 실행하지
  // 않게 앞에 ' 를 붙인다
  const safe = /^[\u0000-\u0020\uFEFF]*[=+\-@]/.test(text) ? `'${text}` : text;
  return `"${safe.replace(/"/g, '""')}"`;
}

$("export-btn").addEventListener(
  "click",
  guarded(async () => {
    const rows = await api.listData();
    const lines = [["id", "date", "value", "memo"], ...rows.map((r) => [r.id, r.date, r.value, r.memo])];
    const csv = "﻿" + lines.map((cols) => cols.map(csvCell).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    el("a", { href: url, download: "data_export.csv" }).click();
    // 브라우저가 내려받기를 시작한 뒤에 주소를 푼다 — 바로 풀면 일부 브라우저에서 빈 파일
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }),
);

// --- 초기화 ---
function today() {
  // toISOString 은 UTC 라 한국 아침 9시 전엔 어제 날짜가 나온다 — 브라우저 현지 날짜로
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

(async function init() {
  try {
    const saved = localStorage.getItem("theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch {
    // 저장소를 못 읽으면 기본 테마
  }
  $("data-date").value = today();
  // 2.5초 안에 서버가 답하면 안내 없이 넘어간다 — 늦으면 「깨우는 중」 안내를 띄운다
  const notice = setTimeout(() => ($("waking").hidden = false), 2500);
  try {
    await api.wake();
    await Promise.all([refreshData(), refreshConversationList()]);
  } catch (err) {
    showError(err);
    clearSkeletons();
  } finally {
    clearTimeout(notice);
    $("waking").hidden = true;
  }
})();

// 첫 불러오기가 실패하면 반짝이는 자리를 「불러오지 못함」 으로 바꾼다 — 계속 반짝이면 아직 기다리는 줄 안다
function clearSkeletons() {
  document.querySelectorAll(".summary-card .skeleton").forEach((n) => {
    n.classList.remove("skeleton");
    n.textContent = "-";
  });
  $("chart").classList.remove("skeleton-box");
  if (!dataLoaded) $("data-list").replaceChildren(el("li", { class: "hint empty" }, "데이터를 불러오지 못했습니다"));
}
