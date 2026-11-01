from __future__ import annotations

from analysis.analyzer import MoveInfo, PositionFeatures
from analysis.classifier import ReasonType, classify
from analysis.features import BoardFeatures


def _pos(turn: int, score: float, winrate: float, best_score: float = 0.0) -> PositionFeatures:
    best_moves = [MoveInfo(move="Q16", visits=100, winrate=0.6, score_lead=best_score, order=0)]
    return PositionFeatures(
        turn_number=turn,
        current_player="B",
        score_lead=score,
        winrate=winrate,
        best_moves=best_moves,
    )


def _bf(
    groups_in_atari: int = 0,
    local_score_delta: float = 0.0,
    opponent_groups_captured_or_atari: int = 0,
    local_best_visit_avg: float = 0.0,
    is_sente: bool = False,
) -> BoardFeatures:
    return BoardFeatures(
        groups_in_atari=groups_in_atari,
        local_score_delta=local_score_delta,
        opponent_groups_captured_or_atari=opponent_groups_captured_or_atari,
        local_best_visit_avg=local_best_visit_avg,
        is_sente=is_sente,
    )


# ── 휴리스틱 경로 (board_features=None) ─────────────────────────────────────

def test_silence_when_no_previous():
    cur = _pos(30, -5.0, 0.40)
    assert classify(cur, None) is None


def test_life_death_on_large_score_drop():
    prev = _pos(30, 5.0, 0.60)
    cur = _pos(31, -6.0, 0.40)
    assert classify(cur, prev) == ReasonType.LIFE_DEATH


def test_life_death_on_large_winrate_drop_alone():
    prev = _pos(30, 3.0, 0.65)
    cur = _pos(31, -4.0, 0.45)
    assert classify(cur, prev) == ReasonType.LIFE_DEATH


def test_missed_attack_when_best_move_recovers():
    prev = _pos(30, 2.0, 0.56)
    cur = _pos(31, -4.0, 0.44, best_score=5.0)
    assert classify(cur, prev) == ReasonType.MISSED_ATTACK


def test_cut_left_when_moderate_drop_no_recovery():
    prev = _pos(30, 2.0, 0.56)
    cur = _pos(31, -4.0, 0.44, best_score=-3.0)
    assert classify(cur, prev) == ReasonType.CUT_LEFT


def test_endgame_sente_in_late_game():
    prev = _pos(160, 3.0, 0.58)
    cur = _pos(161, 0.5, 0.52)
    assert classify(cur, prev) == ReasonType.ENDGAME_SENTE


def test_silence_on_small_early_drop():
    prev = _pos(30, 1.0, 0.52)
    cur = _pos(31, 0.0, 0.50)
    assert classify(cur, prev) is None


# ── BoardFeatures 기반 경로 ──────────────────────────────────────────────────

def test_bf_life_death():
    prev = _pos(40, 5.0, 0.60)
    cur = _pos(41, -4.0, 0.46)  # 9pt, 14% winrate drop
    bf = _bf(groups_in_atari=1, local_score_delta=-9.0)
    assert classify(cur, prev, bf) == ReasonType.LIFE_DEATH


def test_bf_cut_left():
    prev = _pos(50, 3.0, 0.56)
    cur = _pos(51, -2.5, 0.50)  # 5.5pt drop, no opponent atari, no sente
    bf = _bf(local_score_delta=-5.5, opponent_groups_captured_or_atari=0, is_sente=False)
    assert classify(cur, prev, bf) == ReasonType.CUT_LEFT


def test_bf_missed_attack():
    prev = _pos(60, 2.0, 0.55)
    cur = _pos(61, 0.0, 0.52)  # small drop but opponent had an atari group
    bf = _bf(opponent_groups_captured_or_atari=1, local_score_delta=-3.0)
    assert classify(cur, prev, bf) == ReasonType.MISSED_ATTACK


def test_bf_endgame_sente():
    prev = _pos(155, 4.0, 0.62)
    cur = _pos(156, 2.0, 0.58)  # sente miss in late game
    bf = _bf(is_sente=True)
    assert classify(cur, prev, bf) == ReasonType.ENDGAME_SENTE


def test_bf_missed_big_point():
    prev = _pos(80, 2.0, 0.55)
    cur = _pos(81, -1.0, 0.52)  # 3pt drop, high visit count
    bf = _bf(local_best_visit_avg=200.0, is_sente=False)
    assert classify(cur, prev, bf) == ReasonType.MISSED_BIG_POINT


def test_bf_silence_small_drop():
    prev = _pos(30, 1.0, 0.52)
    cur = _pos(31, 0.5, 0.51)
    bf = _bf()
    assert classify(cur, prev, bf) is None
