from __future__ import annotations

from dataclasses import dataclass

from go_core.board import Board, Color
from go_core.coordinate import Coordinate
from engine_pool.pool import get_pool
from engine_pool.types import KATAGO_PLAY_VISITS, AnalysisRequest, Priority

_INT_TO_COLOR = {0: Color.EMPTY, 1: Color.BLACK, 2: Color.WHITE}
_GTP_COLS = list("ABCDEFGHJKLMNOPQRST")
_COL_INDEX = {c: i for i, c in enumerate(_GTP_COLS)}


@dataclass
class AIMoveResult:
    row: int
    col: int
    score_lead: float
    winrate: float
    score_stdev: float
    is_pass: bool = False


def _restore_board(board_state: list[list[int]]) -> Board:
    board = Board()
    for r in range(Board.SIZE):
        for c in range(Board.SIZE):
            board._grid[r][c] = _INT_TO_COLOR[board_state[r][c]]
    return board


def _gtp_to_rowcol(gtp: str) -> tuple[int, int] | None:
    """GTP 좌표("D4") → (row, col). PASS/pass → None."""
    if gtp.upper() in ("PASS", ""):
        return None
    col_char = gtp[0].upper()
    row_num = int(gtp[1:])
    col = _COL_INDEX.get(col_char)
    if col is None:
        return None
    row = Board.SIZE - row_num
    return row, col


async def get_ai_move_async(
    board_state: list[list[int]],
    color: str,
    move_history: list[tuple[str, str]] | None = None,
) -> AIMoveResult:
    """
    engine-pool을 통해 KataGo(또는 mock)에 착수를 요청하고 결과를 반환한다.
    KataGo 응답의 score_lead / winrate / score_stdev도 함께 반환한다.
    """
    pool = get_pool()
    moves = move_history or []
    # 수순이 있으면 moves로 쿼리해 KataGo가 자연스러운 history로 평가하게 한다.
    # 수순이 없을 때만 initialStones + initialPlayer로 폴백 (돌수-차례 불일치로
    # KataGo가 pass를 추정해 집차가 왜곡될 수 있음).
    has_history = len(moves) > 0
    req = AnalysisRequest(
        board_size=Board.SIZE,
        moves=moves,
        board_grid=None if has_history else board_state,
        initial_player=None if has_history else color,
        priority=Priority.AI_MOVE,
        max_visits=KATAGO_PLAY_VISITS,
    )
    resp = await pool.analyze(req)

    board = _restore_board(board_state)
    stone = Color.BLACK if color == "B" else Color.WHITE

    for move_info in resp.best_moves:
        pos = _gtp_to_rowcol(move_info.move)
        if pos is None:
            return AIMoveResult(
                row=-1, col=-1,
                score_lead=resp.score_lead, winrate=resp.winrate, score_stdev=resp.score_stdev,
                is_pass=True,
            )
        row, col = pos
        if not (0 <= row < Board.SIZE and 0 <= col < Board.SIZE):
            continue
        if board_state[row][col] != 0:
            continue
        test = board.copy()
        if test.place(row, col, stone).ok:
            return AIMoveResult(
                row=row, col=col,
                score_lead=resp.score_lead, winrate=resp.winrate, score_stdev=resp.score_stdev,
            )

    return AIMoveResult(
        row=-1, col=-1,
        score_lead=resp.score_lead, winrate=resp.winrate, score_stdev=resp.score_stdev,
        is_pass=True,
    )


def move_to_str(row: int, col: int) -> str:
    return Coordinate.to_korean(row, col)
