from __future__ import annotations

from enum import Enum

from .analyzer import PositionFeatures
from .features import BoardFeatures


class ReasonType(str, Enum):
    LIFE_DEATH = "life_death"
    CUT_LEFT = "cut_left"
    MISSED_ATTACK = "missed_attack"
    MISSED_BIG_POINT = "missed_big_point"
    ENDGAME_SENTE = "endgame_sente"


def classify(
    current: PositionFeatures,
    previous: PositionFeatures | None = None,
    board_features: BoardFeatures | None = None,
) -> ReasonType | None:
    """
    이유 유형 5종 분류기.
    board_features(S2 피처)가 있으면 공간 피처 기반으로, 없으면 점수 기반 휴리스틱 사용.
    이유 유형 5종 중 하나에 해당하지 않으면 None 반환 (침묵 규칙).
    """
    if previous is None:
        return None

    score_drop = abs(current.score_lead - previous.score_lead)
    winrate_drop = abs(current.winrate - previous.winrate)

    if board_features is not None:
        return _classify_with_features(current, score_drop, winrate_drop, board_features)

    return _classify_heuristic(current, score_drop, winrate_drop)


def _classify_with_features(
    current: PositionFeatures,
    score_drop: float,
    winrate_drop: float,
    bf: BoardFeatures,
) -> ReasonType | None:
    """
    BoardFeatures 5종을 사용한 분류.

    우선순위:
      1. life_death  — 단수 그룹 + 큰 점수 하락
      2. cut_left    — 상대 단수 없는데 점수 하락 + 안정적이지 않음
      3. missed_attack — 상대 단수 그룹이 있었지만 공격 안 함
      4. endgame_sente — 선수 기회, 후반
      5. missed_big_point — 나머지 중간 규모 실수
    """
    # 1. 대마 생사: 내 단수 그룹이 생겼고 점수 손실이 큼
    if bf.groups_in_atari >= 1 and (score_drop > 8.0 or winrate_drop > 0.12):
        return ReasonType.LIFE_DEATH

    # 2. 끊김: 점수 손실 중간 + 상대가 잡은 돌 없음 + 선수 아님
    if 4.0 < score_drop <= 8.0 and bf.opponent_groups_captured_or_atari == 0 and not bf.is_sente:
        return ReasonType.CUT_LEFT

    # 3. 약한 돌 공격 기회를 놓침: 상대 단수 그룹이 생겼는데 점수가 줄어든 경우
    if bf.opponent_groups_captured_or_atari >= 1 and bf.local_score_delta < -2.0:
        return ReasonType.MISSED_ATTACK

    # 4. 끝내기 선수: 선수 기회 + 후반(수 > 150)
    if bf.is_sente and current.turn_number > 150 and score_drop > 1.5:
        return ReasonType.ENDGAME_SENTE

    # 5. 큰 자리: 선수가 아닌 중간 실수 + 풍부한 탐색(방문 많음)
    if 2.0 < score_drop <= 4.0 and bf.local_best_visit_avg > 100.0:
        return ReasonType.MISSED_BIG_POINT

    return None


def _classify_heuristic(
    current: PositionFeatures,
    score_drop: float,
    winrate_drop: float,
) -> ReasonType | None:
    """board_features 없을 때 사용하는 점수 기반 휴리스틱 (S1 호환)."""
    if score_drop > 10.0 or winrate_drop > 0.15:
        return ReasonType.LIFE_DEATH

    if score_drop > 5.0:
        if current.best_moves:
            best_score = current.best_moves[0].score_lead
            if best_score - current.score_lead > 3.0:
                return ReasonType.MISSED_ATTACK
        return ReasonType.CUT_LEFT

    if score_drop > 2.0 and current.turn_number > 150:
        return ReasonType.ENDGAME_SENTE

    return None
