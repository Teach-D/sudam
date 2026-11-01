from __future__ import annotations

import json
import random
from pathlib import Path

from .types import AnalysisRequest, AnalysisResponse, MoveInfo

_FIXTURES_DIR = Path(__file__).parents[3] / "fixtures" / "engine"
_GTP_COLS = list("ABCDEFGHJKLMNOPQRST")

# 19로 화점 (row, col) — row=0이 위
_STAR_POINTS_19 = frozenset([
    (3, 3), (3, 9), (3, 15),
    (9, 3), (9, 9), (9, 15),
    (15, 3), (15, 9), (15, 15),
])


def _heuristic_best_moves(
    grid: list[list[int]], board_size: int, turn: int, count: int = 5
) -> list[str]:
    """기존 돌 근접도 히트맵 + 화점 보너스로 후보 수를 고른다."""
    rng = random.Random(turn * 6571 + 17)
    star_points = _STAR_POINTS_19 if board_size == 19 else frozenset()

    # 돌마다 반경 5 안에 열기 확산
    heat = [[0.0] * board_size for _ in range(board_size)]
    radius = 5
    for r in range(board_size):
        for c in range(board_size):
            if grid[r][c] == 0:
                continue
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < board_size and 0 <= nc < board_size:
                        d = abs(dr) + abs(dc)
                        if d <= radius:
                            heat[nr][nc] += (radius + 1 - d) * 2.0

    candidates: list[tuple[float, str]] = []
    for r in range(board_size):
        for c in range(board_size):
            if grid[r][c] != 0:
                continue
            score = heat[r][c]
            # 화점 보너스: 초반에 강하게, 이후 약하게
            if (r, c) in star_points:
                score += 30.0 if turn < 8 else 5.0
            score += rng.uniform(0.0, 0.3)  # 동점 tie-break
            gtp = f"{_GTP_COLS[c]}{board_size - r}"
            candidates.append((score, gtp))

    candidates.sort(key=lambda x: -x[0])
    return [pos for _, pos in candidates[:count]]


def _sample_unique_moves(turn: int, board_size: int, count: int = 5) -> list[str]:
    """board_grid 없을 때 fallback: seeded 랜덤."""
    rng = random.Random(turn * 7919 + 42)
    seen: set[str] = set()
    moves: list[str] = []
    attempts = 0
    while len(moves) < count and attempts < 200:
        col = _GTP_COLS[rng.randrange(board_size)]
        row = rng.randint(1, board_size)
        pos = f"{col}{row}"
        if pos not in seen:
            seen.add(pos)
            moves.append(pos)
        attempts += 1
    return moves


def load_fixture(name: str = "sample_analysis.json") -> dict:
    path = _FIXTURES_DIR / name
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def mock_response(req: AnalysisRequest) -> AnalysisResponse:
    """KataGo 없이 합리적인 mock 응답을 돌려준다."""
    turn = len(req.moves)
    current_player = "B" if turn % 2 == 0 else "W"

    # ±15 범위: 실제 KataGo 수준의 score 변동 반영 (±5는 winrate가 [0.25,0.75]에 갇힘)
    score_lead = round(random.uniform(-15.0, 15.0), 2)
    winrate = round(0.5 + score_lead / 30.0, 4)
    winrate = max(0.05, min(0.95, winrate))

    if req.board_grid is not None:
        positions = _heuristic_best_moves(req.board_grid, req.board_size, turn)
    else:
        positions = _sample_unique_moves(turn, req.board_size)

    best_moves = [
        MoveInfo(
            move=pos,
            visits=max(10, 50 - i * 8),
            winrate=round(winrate - i * 0.02, 4),
            score_lead=round(score_lead - i * 0.5, 2),
            order=i,
        )
        for i, pos in enumerate(positions)
    ]

    return AnalysisResponse(
        request_id=req.request_id,
        turn_number=turn,
        current_player=current_player,
        score_lead=score_lead,
        winrate=winrate,
        score_stdev=round(random.uniform(3.0, 10.0), 2),
        best_moves=best_moves,
    )
