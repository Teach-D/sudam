.PHONY: help up down dev test test-engine eval models lint fmt setup-game tunnel

help:
	@echo "수담 (Sudam) — make targets"
	@echo ""
	@echo "  make up            전체 Docker Compose 실행"
	@echo "  make down          Docker Compose 종료"
	@echo "  make dev           DB 컨테이너 + 세 서비스 로컬 실행 (핫 리로드)"
	@echo "  make test          단위 테스트 (녹화된 KataGo 응답 사용)"
	@echo "  make test-engine   실제 KataGo 통합 테스트"
	@echo "  make eval          golden set 회귀 + 채점 리포트"
	@echo "  make models        KataGo 바이너리·네트워크 다운로드"
	@echo "  make lint          모든 서비스 lint"
	@echo "  make fmt           모든 서비스 format"

# ── Docker ─────────────────────────────────────────────────────────────────

up:
	@cp -n .env.example .env 2>/dev/null || true
	docker compose up --build -d
	@echo "→ http://localhost:3000"

down:
	docker compose down

# ── Dev mode: DB in container, services run locally ──────────────────────

dev: _check-uv _check-pnpm
	@cp -n .env.example .env 2>/dev/null || true
	@echo "Starting DB..."
	docker compose up db -d
	@echo "Starting services (concurrently)..."
	$(MAKE) -j3 _dev-ai _dev-game _dev-web

_dev-ai:
	cd apps/ai-service && uv run uvicorn ai_service.app:app --reload --port 8000

_dev-game:
	cd apps/game-server && ./gradlew bootRun

_dev-web:
	cd apps/web && pnpm dev

# ── Testing ────────────────────────────────────────────────────────────────

tunnel:
	cloudflared tunnel --url http://localhost:3000

setup-game:
	@echo "Setting up Gradle wrapper for game-server..."
	@if command -v gradle >/dev/null 2>&1; then \
		cd apps/game-server && gradle wrapper --gradle-version 8.8; \
	else \
		echo "Gradle not found locally. Use 'make up' to build via Docker."; \
	fi

test: _check-uv
	@echo "=== go-core ==="
	cd packages/go-core && uv run pytest -v
	@echo "=== analysis ==="
	cd packages/analysis && uv run pytest -v
	@echo "=== engine-pool (mock) ==="
	KATAGO_MOCK=true cd packages/engine-pool && uv run pytest -v
	@echo "=== verifier ==="
	cd packages/verifier && uv run pytest -v
	@echo "=== ai-service ==="
	cd apps/ai-service && uv run pytest -v

test-engine: _check-uv
	@echo "=== engine-pool (real KataGo) ==="
	cd packages/engine-pool && uv run pytest -v -m engine

eval: _check-uv
	@echo "=== golden set 회귀 평가 ==="
	python eval/runners/eval_runner.py
	@echo ""
	@echo "=== 유닛 테스트 (빠른 회귀) ==="
	cd packages/go-core && uv run pytest -q
	cd packages/analysis && uv run pytest -q
	cd packages/verifier && uv run pytest -q
	cd apps/ai-service && uv run pytest -q

eval-live: _check-uv
	@echo "=== 라이브 평가 (AI 서비스 필요) ==="
	EVAL_LIVE=true python eval/runners/eval_runner.py

# ── Models (KataGo) ────────────────────────────────────────────────────────

models:
	@bash scripts/setup-katago.sh

# ── Lint / Format ──────────────────────────────────────────────────────────

lint: _check-uv
	uv run --directory packages/go-core ruff check .
	uv run --directory packages/analysis ruff check .
	uv run --directory packages/engine-pool ruff check .
	uv run --directory packages/verifier ruff check .
	uv run --directory apps/ai-service ruff check .

fmt: _check-uv
	uv run --directory packages/go-core ruff format .
	uv run --directory packages/analysis ruff format .
	uv run --directory packages/engine-pool ruff format .
	uv run --directory packages/verifier ruff format .
	uv run --directory apps/ai-service ruff format .

# ── Prereq checks ──────────────────────────────────────────────────────────

_check-uv:
	@command -v uv >/dev/null 2>&1 || (echo "ERROR: uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)

_check-pnpm:
	@command -v pnpm >/dev/null 2>&1 || (echo "ERROR: pnpm not found. Install: npm install -g pnpm" && exit 1)
