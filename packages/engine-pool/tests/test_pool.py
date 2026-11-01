from __future__ import annotations

import os

import pytest

os.environ.setdefault("KATAGO_MOCK", "true")

from engine_pool.pool import EnginePool, lifespan_pool
from engine_pool.types import AnalysisRequest, Priority


@pytest.fixture
async def pool():
    async with lifespan_pool(size=2) as p:
        yield p


async def test_mock_response_returned(pool: EnginePool):
    req = AnalysisRequest(board_size=19, moves=[], priority=Priority.ANALYSIS)
    resp = await pool.analyze(req)
    assert resp.turn_number == 0
    assert resp.current_player == "B"
    assert 0.0 <= resp.winrate <= 1.0
    assert len(resp.best_moves) == 5


async def test_ai_move_priority_first(pool: EnginePool):
    # AI_MOVE 우선순위가 ANALYSIS보다 낮은 번호 → 먼저 처리
    assert Priority.AI_MOVE < Priority.ANALYSIS


async def test_multiple_concurrent_requests(pool: EnginePool):
    import asyncio

    reqs = [
        AnalysisRequest(board_size=19, moves=[("B", "D4")] * i, request_id=f"r{i}")
        for i in range(5)
    ]
    results = await asyncio.gather(*[pool.analyze(r) for r in reqs])
    assert len(results) == 5
    for r in results:
        assert r.winrate > 0


async def test_request_id_preserved(pool: EnginePool):
    req = AnalysisRequest(board_size=19, moves=[], request_id="my-id-123")
    resp = await pool.analyze(req)
    assert resp.request_id == "my-id-123"


async def test_benchmark_returns_stats(pool: EnginePool):
    stats = await pool.benchmark(n_requests=10)
    assert "p95_ms" in stats
    assert stats["n"] == 10
    assert stats["p95_ms"] >= 0
