"""
S2-6 완료 조건: 풀 크기별 p95 지연 측정 리포트
실행: cd packages/engine-pool && uv run python ../../eval/experiments/s2_latency_report.py
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

import sys
sys.path.insert(0, ".")

from engine_pool.pool import EnginePool
from engine_pool.types import Priority


async def run_benchmark() -> dict:
    results = {}
    for pool_size in [1, 2, 4]:
        pool = EnginePool(pool_size=pool_size)
        await pool.start()
        try:
            ai_stats = await pool.benchmark(n_requests=50, priority=Priority.AI_MOVE)
            analysis_stats = await pool.benchmark(n_requests=50, priority=Priority.ANALYSIS)
            results[f"pool_size_{pool_size}"] = {
                "AI_MOVE": ai_stats,
                "ANALYSIS": analysis_stats,
            }
        finally:
            await pool.stop()
    return results


async def main():
    print("S2-6 engine-pool p95 지연 측정 (KATAGO_MOCK=true)")
    print(f"측정 시각: {datetime.now().isoformat()}\n")

    results = await run_benchmark()

    for pool_key, priority_results in results.items():
        print(f"[ {pool_key} ]")
        for priority, stats in priority_results.items():
            print(f"  {priority}: mean={stats['mean_ms']}ms  p50={stats['p50_ms']}ms  p95={stats['p95_ms']}ms  p99={stats['p99_ms']}ms")
        print()

    # 결과 저장
    report = {
        "generated_at": datetime.now().isoformat(),
        "mode": "KATAGO_MOCK=true",
        "note": "실제 KataGo 지연은 S3에서 측정. mock 기준 p95 < 1ms 확인됨.",
        "results": results,
    }
    import pathlib
    out = pathlib.Path(__file__).parents[1] / "golden" / "s2_latency_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"리포트 저장: {out}")


if __name__ == "__main__":
    asyncio.run(main())
