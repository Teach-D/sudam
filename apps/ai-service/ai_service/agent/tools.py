from __future__ import annotations

from typing import Any

from go_core.board import Board, Color
from go_core.coordinate import Coordinate
from engine_pool.pool import get_pool
from engine_pool.types import AnalysisRequest, Priority


# ── Tool 1: play_variation ──────────────────────────────────────────────────

def play_variation(
    board_state: list[list[int]],
    moves: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    보드 위에서 수순을 재생하고, 각 수에서의 합법 여부와
    최종 보드 상태를 반환한다.

    moves: [{"row": int, "col": int, "color": "B"|"W"}, ...]
    """
    board = _board_from_state(board_state)
    played: list[dict[str, Any]] = []
    for i, mv in enumerate(moves):
        row, col = mv["row"], mv["col"]
        color = Color.BLACK if mv["color"] == "B" else Color.WHITE
        result = board.place(row, col, color)
        if not result.ok:
            return {
                "ok": False,
                "error": f"step {i}: illegal move at ({row},{col}): {result.error}",
                "played": played,
            }
        played.append({
            "row": row,
            "col": col,
            "color": mv["color"],
            "label": _label(i + 1),
            "korean": Coordinate.to_korean(row, col),
            "captured": list(result.captured),
        })

    final_board = [
        [int(board._grid[r][c]) for c in range(Board.SIZE)]
        for r in range(Board.SIZE)
    ]
    return {"ok": True, "played": played, "final_board": final_board}


# ── Tool 2: analyze_position ────────────────────────────────────────────────

async def analyze_position(
    board_state: list[list[int]],
    move_number: int,
    color: str = "B",
    max_visits: int = 100,
) -> dict[str, Any]:
    """
    현재 국면을 engine-pool로 분석한다.
    KATAGO_MOCK=true면 녹화된 응답 반환.
    """
    pool = get_pool()
    req = AnalysisRequest(
        board_state=board_state,
        move_number=move_number,
        color=color,
        max_visits=max_visits,
    )
    resp = await pool.analyze(req, priority=Priority.COACH)
    return {
        "score_lead": resp.score_lead,
        "winrate": resp.winrate,
        "score_stdev": resp.score_stdev,
        "best_moves": [
            {
                "move": m.move,
                "visits": m.visits,
                "score_lead": m.score_lead,
                "winrate": m.winrate,
                "korean": _move_str_to_korean(m.move),
            }
            for m in resp.best_moves[:5]
        ],
    }


# ── Tool 3: get_board_facts ─────────────────────────────────────────────────

def get_board_facts(
    board_state: list[list[int]],
    coords: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """
    보드에서 그룹·활로 정보를 반환한다.
    coords가 주어지면 해당 좌표 돌의 그룹·활로만 반환.
    """
    board = _board_from_state(board_state)
    facts: dict[str, Any] = {"groups": []}

    targets = coords or _all_stone_coords(board_state)
    visited: set[tuple[int, int]] = set()

    for r, c in targets:
        if (r, c) in visited or board_state[r][c] == 0:
            continue
        color_val = board_state[r][c]
        color = Color.BLACK if color_val == 1 else Color.WHITE
        group = board._get_group(r, c)
        visited.update(group)
        liberties = board._liberties(group)
        facts["groups"].append({
            "color": "B" if color == Color.BLACK else "W",
            "size": len(group),
            "liberties": len(liberties),
            "in_atari": len(liberties) == 1,
            "coords": [[r2, c2] for r2, c2 in sorted(group)],
            "liberty_coords": [[r2, c2] for r2, c2 in sorted(liberties)],
            "korean": Coordinate.to_korean(r, c),
        })

    return facts


# ── helpers ─────────────────────────────────────────────────────────────────

def _board_from_state(state: list[list[int]]) -> Board:
    board = Board()
    for r, row in enumerate(state):
        for c, v in enumerate(row):
            if v == 1:
                board._grid[r][c] = Color.BLACK
            elif v == 2:
                board._grid[r][c] = Color.WHITE
    return board


def _all_stone_coords(state: list[list[int]]) -> list[tuple[int, int]]:
    return [(r, c) for r in range(19) for c in range(19) if state[r][c] != 0]


def _label(n: int) -> str:
    labels = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
    return labels[n - 1] if 1 <= n <= len(labels) else str(n)


def _move_str_to_korean(move_str: str) -> str:
    if move_str in ("pass", "PASS"):
        return "패스"
    # KataGo vertex format: "A1" … "T19" (no "I")
    col_letters = "ABCDEFGHJKLMNOPQRST"
    if not move_str or move_str[0] not in col_letters:
        return move_str
    col = col_letters.index(move_str[0])
    try:
        row_from_bottom = int(move_str[1:])
        row = 19 - row_from_bottom  # 0-indexed, row=0 at top
        return Coordinate.to_korean(row, col)
    except ValueError:
        return move_str
