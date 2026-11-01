from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..agent import run_coach_push, run_coach_question
from ..cost_tracker import get_tracker

router = APIRouter()


# ── 스키마 ─────────────────────────────────────────────────────────────────────

class CoachPushRequest(BaseModel):
    game_id: str
    board_state: list[list[int]]
    reason_type: str
    score_drop: float
    move_number: int
    color_that_moved: Literal["B", "W"]
    best_move_korean: str = ""


class HintStepOut(BaseModel):
    step: int
    label: str
    text: str


class VariationMoveOut(BaseModel):
    row: int
    col: int
    color: str
    label: str


class CoachPushResponse(BaseModel):
    utterance: str
    verified: bool
    verification_error: str = ""
    variation: list[VariationMoveOut] = Field(default_factory=list)
    hints: list[HintStepOut] = Field(default_factory=list)
    cost: dict = Field(default_factory=dict)
    llm_model: str = ""
    latency_ms: int = 0


class CoachQuestionRequest(BaseModel):
    game_id: str
    board_state: list[list[int]]
    move_number: int
    question_text: str
    color_that_moved: Literal["B", "W"] = "B"
    # [["B","D4"],["W","Q4"],...] — 수순 전체.
    move_history: list[tuple[str, str]] = Field(default_factory=list)


class CoachQuestionResponse(BaseModel):
    question_type: str
    answer: str
    variation: list[dict] = Field(default_factory=list)
    cost: dict = Field(default_factory=dict)
    llm_model: str = ""
    latency_ms: int = 0


# ── 엔드포인트 ──────────────────────────────────────────────────────────────────

@router.post("/coach/push", response_model=CoachPushResponse)
async def coach_push(req: CoachPushRequest) -> CoachPushResponse:
    """F3 흐름: 개입 트리거 → 발화 + 힌트 생성."""
    t0 = time.monotonic()
    result = await run_coach_push(
        board_state=req.board_state,
        reason_type=req.reason_type,
        score_drop=req.score_drop,
        move_number=req.move_number,
        color_that_moved=req.color_that_moved,
        best_move_korean=req.best_move_korean,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    tracker = get_tracker()
    cost = result.get("cost", {})
    tracker.record_llm(
        req.game_id,
        input_tokens=cost.get("utterance_input_tokens", 0) + cost.get("variation_input_tokens", 0),
        output_tokens=cost.get("utterance_output_tokens", 0) + cost.get("variation_output_tokens", 0),
    )
    tracker.record_intervention(req.game_id)
    return CoachPushResponse(
        **result,
        llm_model=cost.get("model", ""),
        latency_ms=latency_ms,
    )


@router.post("/coach/question", response_model=CoachQuestionResponse)
async def coach_question(req: CoachQuestionRequest) -> CoachQuestionResponse:
    """F3-B 흐름: 사용자 질문 → 분류 + 답변."""
    t0 = time.monotonic()
    result = await run_coach_question(
        board_state=req.board_state,
        move_number=req.move_number,
        question_text=req.question_text,
        color_that_moved=req.color_that_moved,
        move_history=req.move_history,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    tracker = get_tracker()
    cost = result.get("cost", {})
    tracker.record_llm(
        req.game_id,
        input_tokens=cost.get("answer_input_tokens", 0),
        output_tokens=cost.get("answer_output_tokens", 0),
    )
    tracker.record_question(req.game_id)
    return CoachQuestionResponse(
        **result,
        llm_model=cost.get("model", ""),
        latency_ms=latency_ms,
    )


@router.get("/coach/cost/{game_id}")
async def get_game_cost(game_id: str) -> dict:
    """판당 원가 조회."""
    return get_tracker().get(game_id)


@router.get("/coach/cost")
async def get_all_costs() -> list[dict]:
    """전체 게임 원가 요약."""
    return get_tracker().summary()
