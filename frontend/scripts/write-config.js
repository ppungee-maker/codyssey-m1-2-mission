// Vercel 빌드 단계에서 config.js 를 만든다 — 백엔드 주소를 코드에 박지 않고 환경변수
// API_BASE_URL 로 받는다(요구 10). Vercel → Settings → Environment Variables 에 넣는다.
//
//   API_BASE_URL=https://<서비스명>.onrender.com node scripts/write-config.js
//
// 값이 없으면 빌드를 실패시킨다 — 로컬 주소(127.0.0.1)가 배포본에 들어가 「서버에 연결하지
// 못했습니다」만 뜨는 것보다, Vercel 빌드 로그에서 바로 보이는 편이 낫다.
const fs = require("fs");
const path = require("path");

const raw = (process.env.API_BASE_URL || "").trim();
if (!/^https?:\/\/[^\s"'`]+$/.test(raw)) {
  console.error("API_BASE_URL 환경변수가 없거나 주소 형식이 아닙니다 (예: https://my-api.onrender.com)");
  process.exit(1);
}
const url = raw.replace(/\/+$/, ""); // 끝의 / 는 떼어 낸다 — `${API_BASE_URL}/api/...` 가 // 가 되지 않게

const out = path.join(__dirname, "..", "config.js");
fs.writeFileSync(
  out,
  `// 빌드 때 scripts/write-config.js 가 만든 파일 — 직접 고치지 않는다.\nconst API_BASE_URL = ${JSON.stringify(url)};\n`,
);
console.log(`config.js ← API_BASE_URL=${url}`);
