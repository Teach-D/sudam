# ADR-001: 게임 서버 분리 여부

| 항목 | 내용 |
|------|------|
| 상태 | 결정됨 (2026-10-04) |
| 결정자 | 개발자 (1인) |

---

## 컨텍스트

수담 MVP는 세 가지 서비스(웹, 게임 서버, AI 서비스)로 구성된다. 게임 서버를 별도 Spring Boot 프로세스로 분리할지, AI 서비스(FastAPI)에 통합할지 결정해야 한다.

### 두 가지 선택지

**옵션 A: Spring Boot 분리 서비스**
- Java 21 + Spring Boot 3
- STOMP WebSocket 기반 실시간 이벤트
- JPA + Flyway (PostgreSQL 스키마 관리)
- 독립적인 상태 머신 (`WAITING → PLAYING → COACH_PAUSE → ANSWERING → FINISHED`)

**옵션 B: FastAPI 통합**
- Python 3.12 + FastAPI
- WebSocket (starlette)
- SQLAlchemy + Alembic
- AI 서비스와 같은 프로세스

---

## 결정: **옵션 A (Spring Boot 분리)**

---

## 근거

### 기술적 이유

1. **상태 머신 복잡성**: 게임 상태 전이(착수, 개입, 질문-응답, 재개, 계가)는 견고한 트랜잭션 관리가 필요하다. Spring의 `@Transactional` + JPA는 이 케이스에 최적화되어 있다.

2. **WebSocket 안정성**: STOMP + Spring WebSocket은 재접속, 세션 관리, 브로커 기반 메시지 라우팅이 프레임워크 수준에서 제공된다. FastAPI의 WebSocket은 저수준이라 이를 직접 구현해야 한다.

3. **장애 격리**: AI 서비스(KataGo 프로세스, LLM 호출)는 CPU/메모리 집약적이고 외부 의존성이 많다. AI 서비스 장애가 게임 상태에 영향을 주지 않으려면 분리가 유리하다.

4. **Flyway 마이그레이션**: DB 스키마 변경을 명시적으로 추적할 수 있어 12주 개발 중 안전한 스키마 진화가 가능하다.

### 트레이드오프

| 항목 | 분리 (선택) | 통합 |
|------|-------------|------|
| 초기 설정 비용 | 높음 (Gradle, JPA, Flyway) | 낮음 |
| 운영 복잡도 | 서비스 2개 추가 | 서비스 1개 |
| WebSocket 기능 | STOMP 완성도 높음 | 직접 구현 필요 |
| 장애 격리 | 우수 | 미흡 |
| 타입 안전성 | Java 강타입 | Python (Pydantic) |

### MVP 범위 고려

- 클로즈드 베타 50명: Docker Compose 1대로 충분
- Spring Boot 이미지 크기 ~ 200MB — 허용 가능
- `make up`으로 전체 Compose 재현 가능 → 운영 복잡도 관리 가능

---

## 결과

- `apps/game-server/` — Java 21 + Spring Boot 3 + STOMP + JPA + Flyway
- `apps/ai-service/` — Python 3.12 + FastAPI (AI 로직만)
- 통신: 게임 서버 → AI 서비스는 REST HTTP (동기), AI → 게임은 필요시 WebSocket 이벤트

### 재검토 시점

S4 이후 서비스가 VM 1대로 이전될 때, 메모리 사용량이 문제가 되면 FastAPI 통합을 재고한다.
