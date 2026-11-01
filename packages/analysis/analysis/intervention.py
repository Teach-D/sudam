from __future__ import annotations

from dataclasses import dataclass

from .analyzer import PositionFeatures
from .classifier import ReasonType, classify

# S1 초기값: 사전 실험 결과 반영 전 기본값
SCORE_DROP_THRESHOLD = 3.0
WINRATE_DROP_THRESHOLD = 0.05
INTERVENTION_SCORE_THRESHOLD = 0.5
MAX_INTERVENTIONS_PER_GAME = 3
MIN_MOVE_INTERVAL = 20


@dataclass
class InterventionDecision:
    triggered: bool
    score: float
    reason_type: ReasonType | None
    score_drop: float
    # per-criterion breakdown for logging
    size_score: float = 0.0
    clarity_score: float = 0.0
    stability_score: float = 0.0
    explainability_score: float = 0.0


def check_intervention(
    current: PositionFeatures,
    previous: PositionFeatures | None,
    move_number: int,
    interventions_this_game: int,
    last_intervention_move: int,
) -> InterventionDecision:
    """
    4-criterion score = SIZE(0.3) + CLARITY(0.3) + STABILITY(0.2) + EXPLAINABILITY(0.2)
    Triggers when score >= 0.5, max 3/game, min 20 moves apart.
    """
    _no = InterventionDecision(triggered=False, score=0.0, reason_type=None, score_drop=0.0)

    if interventions_this_game >= MAX_INTERVENTIONS_PER_GAME:
        return _no
    if (move_number - last_intervention_move) < MIN_MOVE_INTERVAL:
        return _no
    if previous is None:
        return _no

    score_drop = abs(current.score_lead - previous.score_lead)
    winrate_drop = abs(current.winrate - previous.winrate)

    # SIZE: magnitude of mistake (normalised to 10-pt scale)
    size_score = min(score_drop / 10.0, 1.0)

    # CLARITY: winrate confirms the drop
    clarity_score = min(winrate_drop / 0.15, 1.0)

    # STABILITY: position is settled (low score variance)
    stability_score = 1.0 if current.score_stdev < 5.0 else max(0.0, 1.0 - current.score_stdev / 10.0)

    # EXPLAINABILITY: a reason type can be named
    reason_type = classify(current, previous)
    explainability_score = 1.0 if reason_type is not None else 0.0

    total = (
        size_score * 0.3
        + clarity_score * 0.3
        + stability_score * 0.2
        + explainability_score * 0.2
    )

    return InterventionDecision(
        triggered=total >= INTERVENTION_SCORE_THRESHOLD,
        score=round(total, 4),
        reason_type=reason_type,
        score_drop=score_drop,
        size_score=round(size_score, 4),
        clarity_score=round(clarity_score, 4),
        stability_score=round(stability_score, 4),
        explainability_score=explainability_score,
    )
