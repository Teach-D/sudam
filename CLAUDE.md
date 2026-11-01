# 수담 (Sudam) — CLAUDE.md

## 도메인 원칙

수담은 **지도대국** 도구다. AI 사범이 대국 중 결정적 순간에만 끼어들어 간결한 설명을 제공한다.

### 침묵 규칙 (절대 원칙)
- 이유 유형(5종) 중 하나에 명확히 해당하지 않으면 **설명하지 않는다**.
- 설명은 검증기(verifier)를 통과한 것만 노출한다.
- "두터움", "맛", "기세" 같은 모호한 표현은 금지 — 반드시 구체적 근거.

### 이유 유형 5종

| 코드 | 이름 | 설명 |
|------|------|------|
| `life_death` | 대마 생사 | 큰 그룹의 삶·죽음이 결정되는 순간 |
| `cut_left` | 끊김 | 돌이 끊겨 약해지는 순간 |
| `missed_attack` | 약한 돌 공격 | 약한 상대 돌을 공격할 기회를 놓침 |
| `missed_big_point` | 큰 자리 | 국지적으로 큰 자리를 선점할 기회 |
| `endgame_sente` | 끝내기 선수 | 선수 끝내기 기회 |

### 개입 기준 (4가지 가중치)

```
score = SIZE(0.3) + CLARITY(0.3) + STABILITY(0.2) + EXPLAINABILITY(0.2)
```

개입: score ≥ 0.5, 최대 3회/게임, 최소 20수 간격.

---

## 저장소 구조

```
sudam/
├─ Makefile                  ← up / dev / test / eval / models
├─ docker-compose.yml        ← db, game-server, ai-service, web
├─ .env.example
├─ CLAUDE.md                 ← 이 파일
├─ models/                   ← KataGo 바이너리·네트워크 (git 제외)
├─ apps/
│  ├─ web/                   ← Next.js (App Router) + TypeScript
│  ├─ game-server/           ← Java 21 + Spring Boot 3
│  └─ ai-service/            ← Python 3.12 + FastAPI
├─ packages/
│  ├─ go-core/               ← 보드 규칙, 그룹·활로, SGF, 좌표
│  ├─ analysis/              ← 피처 추출, 이유 분류, 개입 트리거
│  ├─ verifier/              ← 주장 스키마, 수순 증명
│  └─ engine-pool/           ← KataGo 프로세스 풀
├─ eval/
│  ├─ golden/                ← 국면, 유단자 라벨, 사용자 질문 샘플
│  └─ runners/               ← 회귀 테스트, 채점 리포트
├─ fixtures/
│  ├─ sgf/                   ← 규칙·분석 테스트 국면
│  └─ engine/                ← 녹화된 KataGo 응답 (CI용)
└─ docs/
   ├─ specs/
   ├─ adr/
   └─ experiments/
```

---

## 패키지별 역할

### `packages/go-core`
바둑 규칙 레이어. 다른 패키지가 이 패키지에 의존한다.

- `board.py` — 19×19 보드, 착수, 따냄, 자충 검사, 패 검사, 그룹·활로
- `coordinate.py` — SGF ↔ (row, col) ↔ 한국식 좌표 (`가1`…`타19`) ↔ numpy 인덱스
- `sgf.py` — SGF 파일 로드·저장, 수순 추출

규칙 테스트는 `fixtures/sgf/`의 SGF 국면을 공용으로 사용한다.

### `packages/analysis`
KataGo 피처를 받아 개입 여부를 결정한다.

- `analyzer.py` — KataGo JSON → Python 피처 구조체
- `classifier.py` — 이유 유형 분류 (5종)
- `intervention.py` — 4기준 점수 계산 + 개입 판단

### `packages/verifier`
LLM이 생성한 주장을 검증한다.

- `schema.py` — Pydantic 주장 스키마
- `verifier.py` — 수순 증명, 좌표 존재, 그룹 상태 검증

실패 → **전체 실패**, template_fallback으로 교체.

### `packages/engine-pool`
KataGo 프로세스 풀 관리.

- 우선순위: AI 착수 > 대화용 분석
- `KATAGO_MOCK=true` 시 녹화된 응답(`fixtures/engine/`) 반환

### `apps/ai-service`
FastAPI. packages를 조합하여 API를 제공한다.

- `POST /api/intervention` — 개입 여부 판단
- `POST /api/intervention/response` — 사범 발화 생성
- `POST /api/analysis/move` — 단수 분석
- `GET  /api/health`

### `apps/game-server`
Spring Boot 3. 게임 상태 머신 + STOMP WebSocket.

상태: `WAITING → PLAYING → COACH_PAUSE → ANSWERING → FINISHED`

### `apps/web`
Next.js 14 (App Router). SVG 바둑판, 사범 패널, 수순 재생.

---

## 코드 규칙

### Python
- 타입 힌트 필수 (Pydantic v2, `from __future__ import annotations`)
- `uv` 로 패키지 관리 — `pip install` 직접 사용 금지
- 테스트: pytest, `fixtures/sgf` 공용 사용
- 좌표는 항상 `(row: int, col: int)` — 0-indexed, row=0이 흑 시작 기준 위쪽

### Java
- Spring Boot 3 / Java 21
- 레코드(record) 우선, 불변 DTO
- `gradlew`로 실행 — `gradle` 직접 사용 금지

### TypeScript
- `pnpm` 로 패키지 관리
- `any` 금지, strict 모드
- 서버 컴포넌트 기본, 클라이언트 컴포넌트는 `'use client'` 명시

### 공통
- 주석은 WHY만 — 코드가 말하는 WHAT은 적지 않는다
- 에러 핸들링: 시스템 경계(사용자 입력, 외부 API)에서만
- 백워드-호환 shim 금지 — 안 쓰는 코드는 삭제

---

## 절대 자르지 않는 것

| 항목 | 이유 |
|------|------|
| 검증기 | 오류 발화 노출 방지 |
| 침묵 규칙 | MVP 핵심 가설 (설명 없는 편이 낫다) |
| 측정 로그 | G1·G2·G3 관문 판정 근거 |
