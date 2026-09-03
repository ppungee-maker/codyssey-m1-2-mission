# AI Agent 개발: 나만의 AI 비서 구축

> 코디세이 `AI 응용 학습 (AI Native Master)` 과정 · `codyssey mission` API로 원문 그대로 발췌.

### 1. 미션 소개

일반적인 ChatGPT는 여러분의 데이터를 모릅니다. "이번 달 매출이 어때?"라고 물어도 일반적인 답변만 돌아옵니다.

이 미션에서는 내 데이터를 이해하고 맞춤형 답변을 제공하는 AI 서비스를 만듭니다.

시계열 데이터를 분석하고, 그 결과를 데이터베이스에 저장하고, AI가 이 데이터를 기반으로 대화하는 웹 서비스를 완성합니다.

"내 상황을 아는 AI 비서"를 직접 만들어보세요.

### 2. 최종 결과물

다음 4가지 기능이 정상 동작하는 애플리케이션 1개를 완성한다.

1. 데이터 기반 AI 채팅 — 저장된 데이터 요약을 반영한 AI 답변 + 로딩 표시
2. 데이터 관리(CRUD) — (date, value, memo) 형태의 데이터 추가/수정/삭제
3. 대화 기록 저장 및 불러오기 — 대화 저장, 목록 조회, 특정 대화 불러오기
4. 배포 및 문서화 — 배포 URL 접속(프론트/백엔드), Swagger UI 확인, README로 실행/환경변수 안내

### 3. 과제 목표

- 시계열 데이터를 분석하고, 요약 정보를 만들어 서비스에서 활용하는 흐름을 설명할 수 있다.
- FastAPI 프로젝트를 라우터/서비스 등으로 분리해 구성한 기준을 설명할 수 있다.
- Pydantic을 활용해 요청 데이터 검증을 적용한 이유와 방식을 설명할 수 있다.
- Firestore에 데이터를 저장하고 CRUD로 다루는 방법을 설명할 수 있다.
- "데이터 요약을 시스템 프롬프트에 주입하는 방식(컨텍스트 주입)"의 원리를 설명할 수 있다.
- 배포 환경에서 CORS/환경변수/키 관리가 왜 필요한지 설명할 수 있다.

### 4. 기능 요구 사항

1. **개발 환경 준비**: Python 3.10+, venv, fastapi/uvicorn/firebase-admin/openai/python-dotenv, Firebase 프로젝트+서비스계정키, OpenAI API 키, Render/Vercel 계정
2. **데이터 선정 및 분석**: 관심있는 시계열 데이터, 최소 100개 이상, 요약정보(기간/개수/기본통계/최근추세) 생성 가능해야 함
3. **FastAPI 프로젝트 구성**: 앱 초기화+CORS, 로컬 실행(`uvicorn main:app --reload`), Swagger UI(`/docs`)
4. **Firebase(Firestore) 연동**: 서비스계정키는 환경변수로 관리(코드 하드코딩 금지), 컬렉션 구조(data/conversations)
5. **데이터 API 개발**: `POST/GET /api/data`, `PUT/DELETE /api/data/{id}`, `GET /api/data/summary`
6. **대화 기록 API 개발**: `POST/GET /api/conversations`, `DELETE /api/conversations/{id}`, 대화 불러오기(옵션A: `GET /api/conversations/{id}` 또는 옵션B: 목록에 messages 포함)
7. **AI 챗봇 API 개발(컨텍스트 주입)**: `POST /api/chat` — 요약조회→시스템프롬프트삽입→GPT호출→대화자동저장
8. **백엔드 배포(Render)**: GitHub push, Web Service 생성, `/docs` 확인, 콜드스타트 안내
9. **웹 프론트엔드 개발(바닐라)**: HTML/CSS/JS(프레임워크 금지) — 채팅 인터페이스, 데이터 관리, 대화 기록, 데이터 요약 표시
10. **프론트엔드 배포(Vercel) 및 문서화**: 환경변수로 API URL 설정, README(서비스소개/기술스택/배포URL/로컬실행법/env변수목록/제출스크린샷)

### 5. 보너스 과제 (선택)

- AI 도구 호출(Function Calling) + 멀티채널 연동 — GPT가 내부 기능을 "도구"로 호출, MCP Server 또는 GPT Actions 중 1개 방식으로 연동, README에 호출 흐름 정리
- 인사이트·UX 고도화 — 요약/통계 확장(지표 1개+), 프론트 시각화(그래프 1개), 데이터 내보내기(CSV/JSON), 다크 모드 토글
