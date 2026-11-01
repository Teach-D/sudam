from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Move ────────────────────────────────────────────────────────────────────

class MoveRequest(BaseModel):
    game_id: str
    board_state: list[list[int]]  # 19×19, 0=empty 1=black 2=white
    move_number: int
    color: Literal["B", "W"]
    # [["B","D4"],["W","Q4"],...] — 수순 전체. 지정 시 KataGo에 수순으로 전달해
    # initialStones 왜곡(돌수-차례 불일치로 pass 추정)을 회피한다.
    move_history: list[tuple[str, str]] = Field(default_factory=list)


class MoveResponse(BaseModel):
    row: int
    col: int
    move_str: str           # Korean e.g. "가1", or "PASS"
    is_pass: bool = False
    score_lead: float = 0.0   # KataGo: positive = black ahead
    winrate: float = 0.5      # KataGo: black's winning probability
    score_stdev: float = 0.0  # KataGo: uncertainty


# ── Intervention ─────────────────────────────────────────────────────────────

class InterventionCheckRequest(BaseModel):
    game_id: str
    move_number: int
    score_before: float
    score_after: float
    winrate_before: float
    winrate_after: float
    score_stdev: float = 0.0
    interventions_so_far: int = 0
    last_intervention_move: int = 0
    board_state: list[list[int]] | None = None
    played_row: int | None = None
    played_col: int | None = None
    color_that_moved: Literal["B", "W"] = "B"


class InterventionCheckResponse(BaseModel):
    triggered: bool
    score: float
    reason_type: str | None
    score_drop: float
    breakdown: dict[str, float] = Field(default_factory=dict)


class InterventionDraftRequest(BaseModel):
    game_id: str
    board_state: list[list[int]]
    reason_type: str
    score_drop: float
    move_number: int
    color_that_moved: Literal["B", "W"]


class InterventionDraftResponse(BaseModel):
    draft_text: str
    reason_type: str
