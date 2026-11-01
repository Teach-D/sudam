from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 로컬: apps/ai-service/ai_service/ → parents[3] = 프로젝트 루트
# Docker: /app/ai_service/ → parents[2] = / (없으면 최상위로 폴백)
_parents = Path(__file__).parents
_PROJECT_ROOT = _parents[3] if len(_parents) > 3 else _parents[-1]
_env_file = _PROJECT_ROOT / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file, override=False)
    except ImportError:
        pass  # python-dotenv 없으면 환경 변수를 그대로 사용

from engine_pool.pool import get_pool
from .routes import health, intervention, move, coach


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = get_pool()
    await pool.start()
    # KataGo 모델 워밍업 — 첫 사용자 요청 전에 모델을 메모리에 로드한다.
    if not pool._mock:
        import asyncio
        from engine_pool.types import AnalysisRequest, Priority
        try:
            await asyncio.wait_for(
                pool.analyze(AnalysisRequest(board_size=19, moves=[], priority=Priority.ANALYSIS)),
                timeout=120,
            )
        except Exception:
            pass  # 워밍업 실패는 무시 — 첫 요청이 느릴 수 있음
    yield
    await pool.stop()


app = FastAPI(title="Sudam AI Service", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(move.router, prefix="/api")
app.include_router(intervention.router, prefix="/api")
app.include_router(coach.router, prefix="/api")
