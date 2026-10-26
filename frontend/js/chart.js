// 보너스: 시계열 선 그래프 — 라이브러리 없이 SVG 로 그린다(프레임워크 금지 요구와 같은 이유로
// 의존성 0). 마우스·손가락을 올리면 가장 가까운 날의 값과 날짜를 보여 준다.

const SVG_NS = "http://www.w3.org/2000/svg";

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

// points = [{date: "YYYY-MM-DD", value: number}] (날짜순)
function drawLineChart(svg, points) {
  // 그리는 좌표 = 실제 화면 폭. 800 고정으로 그려 줄이면 휴대폰에서 글자가 5px 로 작아진다.
  const W = Math.max(280, Math.round(svg.clientWidth || 800));
  const H = W < 500 ? 180 : 220;
  const PAD = { top: 16, right: 12, bottom: 26, left: 48 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.replaceChildren();
  if (points.length < 2) {
    const msg = svgEl("text", { x: W / 2, y: H / 2, "text-anchor": "middle", class: "chart-label" });
    msg.textContent = "그래프를 그리려면 데이터가 2건 이상 필요합니다";
    svg.append(msg);
    return;
  }

  // Math.min(...values) 는 값이 수십만 개면 인자 수 한도로 RangeError — 한 번 훑어서 구한다
  let lo = Infinity, hi = -Infinity;
  for (const p of points) {
    if (p.value < lo) lo = p.value;
    if (p.value > hi) hi = p.value;
  }
  if (lo === hi) { lo -= 1; hi += 1; } // 값이 전부 같아도 선이 가운데 그려지게
  const x = (i) => PAD.left + (i / (points.length - 1)) * (W - PAD.left - PAD.right);
  const y = (v) => PAD.top + (1 - (v - lo) / (hi - lo)) * (H - PAD.top - PAD.bottom);

  // 가로 눈금 3줄(최저·중간·최고)
  for (const v of [lo, (lo + hi) / 2, hi]) {
    svg.append(svgEl("line", { x1: PAD.left, x2: W - PAD.right, y1: y(v), y2: y(v), class: "chart-grid" }));
    const t = svgEl("text", { x: PAD.left - 6, y: y(v) + 4, "text-anchor": "end", class: "chart-label" });
    t.textContent = v.toFixed(1);
    svg.append(t);
  }
  for (const [i, anchor] of [[0, "start"], [points.length - 1, "end"]]) {
    const t = svgEl("text", { x: x(i), y: H - 6, "text-anchor": anchor, class: "chart-label" });
    t.textContent = points[i].date;
    svg.append(t);
  }

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join("");
  const base = H - PAD.bottom;
  svg.append(svgEl("path", { d: `${line}L${x(points.length - 1)},${base}L${x(0)},${base}Z`, class: "chart-area" }));
  svg.append(svgEl("path", { d: line, class: "chart-line" }));

  // 가리키는 점
  const dot = svgEl("circle", { r: 4, class: "chart-dot", visibility: "hidden" });
  const tip = svgEl("text", { class: "chart-tip", visibility: "hidden" });
  svg.append(dot, tip);
  svg.onpointermove = (e) => {
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - PAD.left) / (W - PAD.left - PAD.right)) * (points.length - 1));
    const p = points[Math.max(0, Math.min(points.length - 1, i))];
    const j = points.indexOf(p);
    dot.setAttribute("cx", x(j));
    dot.setAttribute("cy", y(p.value));
    tip.textContent = `${p.date} · ${p.value}`;
    tip.setAttribute("x", Math.min(x(j) + 8, W - 140));
    tip.setAttribute("y", Math.max(y(p.value) - 8, 14));
    dot.setAttribute("visibility", "visible");
    tip.setAttribute("visibility", "visible");
  };
  svg.onpointerleave = () => {
    dot.setAttribute("visibility", "hidden");
    tip.setAttribute("visibility", "hidden");
  };
}
