from __future__ import annotations

import os

from fastapi import APIRouter

from analysis.analyzer import PositionFeatures
from analysis.intervention import check_intervention

from ..schemas import (
    InterventionCheckRequest,
    InterventionCheckResponse,
    InterventionDraftRequest,
    InterventionDraftResponse,
)

router = APIRouter()

_DRAFT_TEMPLATES: dict[str, str] = {
    "life_death": "{color}이 방금 큰 그룹의 생사에 영향을 주는 수를 두었습니다. "
                  "점수 차이가 약 {drop:.1f}집 발생했습니다.",
    "cut_left": "{color}의 돌이 끊겨 약한 그룹이 생겼습니다. "
                "점수 차이가 약 {drop:.1f}집 발생했습니다.",
    "missed_attack": "{color}이 약한 상대 돌을 공격할 기회를 놓쳤습니다. "
                     "점수 차이가 약 {drop:.1f}집입니다.",
    "missed_big_point": "{color}이 국지적으로 큰 자리를 놓쳤습니다. "
                        "점수 차이가 약 {drop:.1f}집입니다.",
    "endgame_sente": "{color}이 선수 끝내기 기회를 놓쳤습니다. "
                     "점수 차이가 약 {drop:.1f}집입니다.",
}


@router.post("/intervention/check", response_model=InterventionCheckResponse)
async def check(req: InterventionCheckRequest) -> InterventionCheckResponse:
    current = PositionFeatures(
        turn_number=req.move_number,
        current_player="B",
        score_lead=req.score_after,
        winrate=req.winrate_after,
        score_stdev=req.score_stdev,
    )
    previous = PositionFeatures(
        turn_number=req.move_number - 1,
        current_player="W",
        score_lead=req.score_before,
        winrate=req.winrate_before,
        score_stdev=req.score_stdev,
    )

    decision = check_intervention(
        current=current,
        previous=previous,
        move_number=req.move_number,
        interventions_this_game=req.interventions_so_far,
        last_intervention_move=req.last_intervention_move,
    )

    return InterventionCheckResponse(
        triggered=decision.triggered,
        score=decision.score,
        reason_type=decision.reason_type.value if decision.reason_type else None,
        score_drop=decision.score_drop,
        breakdown={
            "size": decision.size_score,
            "clarity": decision.clarity_score,
            "stability": decision.stability_score,
            "explainability": decision.explainability_score,
        },
    )


@router.post("/intervention/draft", response_model=InterventionDraftResponse)
async def draft(req: InterventionDraftRequest) -> InterventionDraftResponse:
    color_name = "흑" if req.color_that_moved == "B" else "백"
    template = _DRAFT_TEMPLATES.get(req.reason_type, "{color}이 실수를 했습니다 ({drop:.1f}집).")
    text = template.format(color=color_name, drop=req.score_drop)

    return InterventionDraftResponse(
        draft_text=text,
        reason_type=req.reason_type,
    )
