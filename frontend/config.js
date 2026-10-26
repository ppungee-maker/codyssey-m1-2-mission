// 백엔드 API 주소 — 로컬 개발 기본값(uvicorn 기본 포트).
// 배포(Vercel)에서는 빌드 때 scripts/write-config.js 가 환경변수 API_BASE_URL 로 이 파일을
// 새로 만든다. 그러니 배포 주소를 여기 적어 커밋하지 않는다.
const API_BASE_URL = "http://127.0.0.1:8000";
