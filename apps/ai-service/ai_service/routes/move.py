from __future__ import annotations

from fastapi import APIRouter

from ..schemas import MoveRequest, MoveResponse
from ..services.ai_player import get_ai_move_async, move_to_str

router = APIRouter()


@router.post("/move", response_model=MoveResponse)
async def get_move(req: MoveRequest) -> MoveResponse:
    black = sum(1 for row in req.board_state for c in row if c == 1)
    white = sum(1 for row in req.board_state for c in row if c == 2)
    print(f"[MOVE REQ] move_number={req.move_number} color={req.color} B={black} W={white}", flush=True)

    result = await get_ai_move_async(req.board_state, req.color, req.move_history or None)

    return MoveResponse(
        row=result.row,
        col=result.col,
        move_str="PASS" if result.is_pass else move_to_str(result.row, result.col),
        is_pass=result.is_pass,
        score_lead=result.score_lead,
        winrate=result.winrate,
        score_stdev=result.score_stdev,
    )
