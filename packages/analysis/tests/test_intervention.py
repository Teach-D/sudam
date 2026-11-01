from __future__ import annotations

import pytest
from analysis.analyzer import PositionFeatures
from analysis.classifier import ReasonType
from analysis.intervention import (
    MAX_INTERVENTIONS_PER_GAME,
    MIN_MOVE_INTERVAL,
    check_intervention,
)


def _pos(turn: int, score: float, winrate: float, stdev: float = 2.0) -> PositionFeatures:
    return PositionFeatures(
        turn_number=turn,
        current_player="B",
        score_lead=score,
        winrate=winrate,
        score_stdev=stdev,
    )


class TestNoTriggerGuards:
    def test_no_trigger_without_previous(self):
        cur = _pos(30, -5.0, 0.40)
        result = check_intervention(cur, None, 30, 0, 0)
        assert not result.triggered

    def test_no_trigger_max_interventions_reached(self):
        prev = _pos(30, 2.0, 0.55)
        cur = _pos(31, -8.0, 0.35)
        result = check_intervention(cur, prev, 31, MAX_INTERVENTIONS_PER_GAME, 0)
        assert not result.triggered

    def test_no_trigger_too_close_to_last_intervention(self):
        prev = _pos(30, 2.0, 0.55)
        cur = _pos(31, -8.0, 0.35)
        # last intervention was on move 20, current is 31 → gap = 11 < 20
        result = check_intervention(cur, prev, 31, 1, 20)
        assert not result.triggered


class TestTrigger:
    def test_large_score_drop_triggers(self):
        prev = _pos(40, 5.0, 0.60)
        cur = _pos(41, -6.0, 0.40)  # 11-pt drop, 20% winrate drop
        result = check_intervention(cur, prev, 41, 0, 0)
        assert result.triggered
        assert result.score_drop == pytest.approx(11.0)

    def test_reason_type_life_death_on_large_drop(self):
        prev = _pos(40, 5.0, 0.60)
        cur = _pos(41, -6.0, 0.40)
        result = check_intervention(cur, prev, 41, 0, 0)
        assert result.reason_type == ReasonType.LIFE_DEATH

    def test_small_drop_does_not_trigger(self):
        prev = _pos(40, 2.0, 0.52)
        cur = _pos(41, 1.0, 0.50)  # 1-pt drop
        result = check_intervention(cur, prev, 41, 0, 0)
        assert not result.triggered

    def test_endgame_sente_in_late_game(self):
        prev = _pos(160, 3.0, 0.58)
        cur = _pos(161, 0.5, 0.52)  # 2.5-pt drop in move 161 > 150
        result = check_intervention(cur, prev, 161, 0, 0)
        # endgame_sente classified
        assert result.reason_type == ReasonType.ENDGAME_SENTE

    def test_score_breakdown_sums_to_total(self):
        prev = _pos(50, 5.0, 0.62, stdev=1.5)
        cur = _pos(51, -7.0, 0.38, stdev=1.5)
        result = check_intervention(cur, prev, 51, 0, 0)
        computed = (
            result.size_score * 0.3
            + result.clarity_score * 0.3
            + result.stability_score * 0.2
            + result.explainability_score * 0.2
        )
        assert result.score == pytest.approx(computed, abs=1e-3)

    def test_trigger_respects_min_interval_exactly(self):
        prev = _pos(40, 5.0, 0.60)
        cur = _pos(60, -6.0, 0.40)
        # last intervention at move 40, current move 60 → gap == 20, allowed
        result = check_intervention(cur, prev, 60, 1, 40)
        assert result.triggered
