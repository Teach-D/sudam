from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from .mock import mock_response
from .types import AnalysisRequest, AnalysisResponse, MoveInfo, Priority

_MOCK_ENV = os.getenv("KATAGO_MOCK", "true").lower() == "true"
_CACHE_SIZE = int(os.getenv("KATAGO_CACHE_SIZE", "128"))


def _cache_key(req: AnalysisRequest) -> tuple:
    """캐시 키 — 결과에 영향을 주는 필드만. request_id/priority는 제외."""
    moves_key = tuple(tuple(m) for m in req.moves)
    grid_key = (
        tuple(tuple(row) for row in req.board_grid)
        if req.board_grid is not None
        else None
    )
    allow_key = tuple(req.allow_moves) if req.allow_moves else None
    return (
        req.board_size,
        moves_key,
        grid_key,
        req.initial_player,
        allow_key,
        req.max_visits,
        req.rules,
        req.komi,
    )

# packages/engine-pool/engine_pool/pool.py → 4단계 위 = 프로젝트 루트
_PROJECT_ROOT = Path(__file__).parents[3]


def _resolve_path(p: str) -> str:
    """./로 시작하는 상대 경로를 프로젝트 루트 기준 절대 경로로 변환한다."""
    if p.startswith("./") or p.startswith(".\\"):
        return str((_PROJECT_ROOT / p[2:]).resolve())
    return p


def _parse_katago_response(data: dict) -> AnalysisResponse:
    root = data.get("rootInfo", {})
    raw_moves = data.get("moveInfos", [])
    sorted_moves = sorted(raw_moves, key=lambda m: m.get("order", 999))
    best_moves = [
        MoveInfo(
            move=m["move"],
            visits=m.get("visits", 0),
            winrate=round(m.get("winrate", 0.5), 4),
            score_lead=round(m.get("scoreLead", 0.0), 2),
            order=i,
            pv=list(m.get("pv", []))[:5],
        )
        for i, m in enumerate(sorted_moves[:10])
    ]
    return AnalysisResponse(
        request_id=data.get("id", ""),
        turn_number=data.get("turnNumber", 0),
        current_player=root.get("currentPlayer", "B"),
        score_lead=round(root.get("scoreLead", 0.0), 2),
        winrate=round(root.get("winrate", 0.5), 4),
        score_stdev=round(root.get("scoreStdev", 0.0), 2),
        best_moves=best_moves,
    )


@dataclass(order=True)
class _PriorityItem:
    priority: Priority
    seq: int
    request: AnalysisRequest = field(compare=False)
    future: asyncio.Future = field(compare=False)


class EnginePool:
    """
    KataGo 프로세스 풀.

    - KATAGO_MOCK=true(기본값): mock 응답 반환 (CI, 개발용)
    - KATAGO_MOCK=false: KataGo analysis engine과 JSON으로 통신
    - 우선순위: Priority.AI_MOVE(0) > Priority.ANALYSIS(1)
    """

    def __init__(
        self,
        pool_size: int = 2,
        binary: str | None = None,
        model: str | None = None,
        config: str | None = None,
        timeout_seconds: float = float(os.getenv("KATAGO_TIMEOUT", "20")),
    ) -> None:
        self.pool_size = pool_size
        self.binary = _resolve_path(binary or os.getenv("KATAGO_BINARY", "katago"))
        self.model = _resolve_path(model or os.getenv("KATAGO_MODEL", ""))
        self.config = _resolve_path(config or os.getenv("KATAGO_CONFIG", "/app/katago_analysis.cfg"))
        self.timeout_seconds = timeout_seconds

        # 모델 파일이 없으면 자동으로 mock 모드로 전환
        model_exists = bool(self.model) and Path(self.model).exists()
        self._mock = _MOCK_ENV or not model_exists

        self._queue: asyncio.PriorityQueue[_PriorityItem] = asyncio.PriorityQueue()
        self._seq = 0
        self._workers: list[asyncio.Task] = []
        self._started = False

        # KataGo 프로세스 관련
        self._katago_proc: asyncio.subprocess.Process | None = None
        self._pending: dict[str, asyncio.Future[AnalysisResponse]] = {}
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._ready_event: asyncio.Event | None = None

        # 포지션 LRU 캐시 — 같은 (수순, visits, allow_moves)에 대한 반복 쿼리 skip.
        # 지도대국 중 사용자가 같은 포지션에 variation/reason 질문을 분리해서 던지는 패턴이 흔하다.
        self._cache: OrderedDict[tuple, AnalysisResponse] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        if not self._mock:
            await self._launch_katago()
        for _ in range(self.pool_size):
            self._workers.append(asyncio.create_task(self._worker()))

    async def stop(self) -> None:
        for w in self._workers:
            w.cancel()
        self._workers.clear()
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._stderr_task:
            self._stderr_task.cancel()
            self._stderr_task = None
        if self._katago_proc:
            self._katago_proc.terminate()
            await self._katago_proc.wait()
            self._katago_proc = None
        self._started = False

    async def analyze(self, req: AnalysisRequest) -> AnalysisResponse:
        """요청을 큐에 넣고 결과를 기다린다. mock 모드에서는 큐를 우회한다."""
        if not req.request_id:
            req.request_id = str(uuid.uuid4())

        if self._mock:
            return mock_response(req)

        # 캐시 조회 — hit면 KataGo 호출 자체를 skip.
        key = _cache_key(req)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            self._cache_hits += 1
            print(
                f"[KATAGO CACHE HIT] id={req.request_id[:8]} "
                f"hits={self._cache_hits} misses={self._cache_misses}",
                flush=True,
            )
            # request_id는 호출자별로 다르므로 교체해 반환.
            return replace(cached, request_id=req.request_id)
        self._cache_misses += 1

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[AnalysisResponse] = loop.create_future()
        item = _PriorityItem(priority=req.priority, seq=self._seq, request=req, future=fut)
        self._seq += 1
        await self._queue.put(item)
        result = await asyncio.wait_for(fut, timeout=self.timeout_seconds)

        # 캐시 삽입 (LRU 정책).
        self._cache[key] = result
        self._cache.move_to_end(key)
        if len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return result

    async def benchmark(
        self, n_requests: int = 20, priority: Priority = Priority.ANALYSIS
    ) -> dict[str, float]:
        import statistics

        latencies: list[float] = []
        for i in range(n_requests):
            req = AnalysisRequest(
                board_size=19,
                moves=[],
                request_id=f"bench-{i}",
                priority=priority,
            )
            t0 = time.perf_counter()
            await self.analyze(req)
            latencies.append((time.perf_counter() - t0) * 1000)

        latencies.sort()
        return {
            "n": n_requests,
            "mean_ms": round(statistics.mean(latencies), 2),
            "p50_ms": round(latencies[len(latencies) // 2], 2),
            "p95_ms": round(latencies[int(len(latencies) * 0.95)], 2),
            "p99_ms": round(latencies[int(len(latencies) * 0.99)], 2),
        }

    async def _launch_katago(self) -> None:
        """KataGo 프로세스를 시작하고 'Started, ready' 메시지를 확인한 뒤 리턴한다."""
        cmd = [self.binary, "analysis", "-model", self.model, "-config", self.config]
        self._ready_event = asyncio.Event()
        self._katago_proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,  # ready 감지를 위해 캡처
        )
        self._reader_task = asyncio.create_task(self._katago_reader())
        self._stderr_task = asyncio.create_task(self._katago_stderr_reader())

        # KataGo가 완전히 초기화될 때까지 대기 (최대 120초)
        await asyncio.wait_for(self._ready_event.wait(), timeout=120)
        print("[KATAGO] ready", flush=True)

    async def _katago_stderr_reader(self) -> None:
        """KataGo stderr를 읽어 콘솔에 출력하고, 준비 완료 시 _ready_event를 설정한다."""
        proc = self._katago_proc
        while proc and proc.stderr:
            line = await proc.stderr.readline()
            if not line:
                break
            decoded = line.decode(errors="replace").rstrip()
            print(f"[KATAGO] {decoded}", flush=True)
            if self._ready_event and not self._ready_event.is_set():
                if "ready to begin handling requests" in decoded:
                    self._ready_event.set()

    async def _katago_reader(self) -> None:
        """KataGo stdout를 줄 단위로 읽어 pending future에 결과를 전달한다."""
        proc = self._katago_proc
        while proc and proc.stdout:
            line = await proc.stdout.readline()
            if not line:
                break
            try:
                raw = line.decode().strip()
                data = json.loads(raw)
                root = data.get("rootInfo", {})
                print(
                    f"[KATAGO RESP RAW] id={data.get('id','')[:8]} "
                    f"currentPlayer={root.get('currentPlayer')} "
                    f"winrate={root.get('winrate')} scoreLead={root.get('scoreLead')} "
                    f"visits={root.get('visits')}",
                    flush=True,
                )
                req_id = data.get("id", "")
                fut = self._pending.pop(req_id, None)
                if fut and not fut.done():
                    fut.set_result(_parse_katago_response(data))
            except Exception as e:
                print(f"[KATAGO PARSE ERR] {e}: {line[:200]}", flush=True)

    async def _worker(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                if self._mock:
                    result = mock_response(item.request)
                else:
                    result = await asyncio.wait_for(
                        self._katago_query(item.request),
                        timeout=self.timeout_seconds,
                    )
                if not item.future.done():
                    item.future.set_result(result)
            except Exception as exc:
                if not item.future.done():
                    item.future.set_exception(exc)
            finally:
                self._queue.task_done()

    async def _katago_query(self, req: AnalysisRequest) -> AnalysisResponse:
        """KataGo analysis engine에 JSON 쿼리를 보내고 응답을 기다린다."""
        if self._katago_proc is None or self._katago_proc.stdin is None:
            raise RuntimeError("KataGo process not running")

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[AnalysisResponse] = loop.create_future()
        self._pending[req.request_id] = fut

        # board_grid가 있으면 현재 포지션을 initialStones으로 전달한다.
        # 차례는 initial_player(명시) 또는 pass 트릭(폴백)으로 결정.
        _GTP_COLS = list("ABCDEFGHJKLMNOPQRST")
        if req.board_grid is not None:
            initial_stones = [
                [("B" if req.board_grid[r][c] == 1 else "W"),
                 f"{_GTP_COLS[c]}{req.board_size - r}"]
                for r in range(req.board_size)
                for c in range(req.board_size)
                if req.board_grid[r][c] != 0
            ]
            if req.initial_player is None and len(req.moves) % 2 == 1:
                # 폴백: 호출자가 initial_player를 안 넘긴 레거시 경로.
                # pass는 ~5-15집 손해로 평가돼 집차/승률이 왜곡되지만, 차례를
                # 바꿀 다른 수단이 없어 유지한다.
                turn_moves: list[list[str]] = [["B", "pass"]]
            else:
                turn_moves = []
        else:
            initial_stones = []
            turn_moves = [[color, move] for color, move in req.moves]

        query: dict = {
            "id": req.request_id,
            "moves": turn_moves,
            "initialStones": initial_stones,
            "rules": req.rules,
            "komi": req.komi,
            "boardXSize": req.board_size,
            "boardYSize": req.board_size,
            "analyzeTurns": [len(turn_moves)],
            "maxVisits": req.max_visits,
        }
        if req.initial_player is not None:
            query["initialPlayer"] = req.initial_player
        if req.allow_moves:
            # to-move 결정: initial_player 우선, 아니면 moves 수순 마지막의 반대편.
            # 둘 다 없으면 흑으로 기본값 (빈 보드 흑 선착).
            if req.initial_player:
                to_move_for_allow = req.initial_player
            elif req.moves:
                last_color = req.moves[-1][0]
                to_move_for_allow = "W" if last_color == "B" else "B"
            else:
                to_move_for_allow = "B"
            query["allowMoves"] = [{
                "player": to_move_for_allow,
                "moves": list(req.allow_moves),
                "untilDepth": 1,
            }]
        payload = json.dumps(query) + "\n"
        print(f"[KATAGO QUERY] id={req.request_id[:8]} stones={len(initial_stones)} moves={turn_moves} initialPlayer={query.get('initialPlayer','<none>')} visits={req.max_visits}", flush=True)
        self._katago_proc.stdin.write(payload.encode())
        await self._katago_proc.stdin.drain()

        result = await asyncio.wait_for(fut, timeout=self.timeout_seconds)
        print(f"[KATAGO RESP] id={req.request_id[:8]} best={result.best_moves[0].move if result.best_moves else 'none'}", flush=True)
        return result


# 싱글턴
_pool: Optional[EnginePool] = None


def get_pool() -> EnginePool:
    global _pool
    if _pool is None:
        _pool = EnginePool()
    return _pool


@asynccontextmanager
async def lifespan_pool(size: int = 2) -> AsyncIterator[EnginePool]:
    pool = EnginePool(pool_size=size)
    await pool.start()
    try:
        yield pool
    finally:
        await pool.stop()
