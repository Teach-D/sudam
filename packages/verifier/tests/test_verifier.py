from __future__ import annotations

import pytest

from verifier.schema import CoachClaim, VariationMove
from verifier.verifier import verify


def empty_board() -> list[list[int]]:
    return [[0] * 19 for _ in range(19)]


def board_with_stones(stones: list[tuple[int, int, int]]) -> list[list[int]]:
    """stones: list of (row, col, color) where color=1(B) or 2(W)"""
    b = empty_board()
    for r, c, color in stones:
        b[r][c] = color
    return b


# ── 기본 성공 경로 ──────────────────────────────────────────────────────────

def test_empty_variation_passes():
    claim = CoachClaim(reason_type="cut_left", utterance="돌이 끊겼습니다.", score_drop=3.0)
    result = verify(claim, empty_board())
    assert result.verified
    assert result.verification_error == ""


def test_valid_variation_passes():
    board = empty_board()
    claim = CoachClaim(
        reason_type="missed_attack",
        utterance="공격 기회를 놓쳤습니다.",
        score_drop=5.0,
        variation=[
            VariationMove(row=3, col=3, color="B", label="①"),
            VariationMove(row=3, col=4, color="W", label="②"),
        ],
    )
    result = verify(claim, board)
    assert result.verified


def test_affected_coords_with_stone_passes():
    board = board_with_stones([(5, 5, 1)])  # 흑돌 하나
    claim = CoachClaim(
        reason_type="life_death",
        utterance="대마 위기입니다.",
        score_drop=12.0,
        affected_coords=[(5, 5)],
    )
    result = verify(claim, board)
    assert result.verified


# ── 실패 경로 (일부러 틀린 주장) ───────────────────────────────────────────

def test_out_of_bounds_coord_fails():
    claim = CoachClaim(
        reason_type="cut_left",
        utterance="끊겼습니다.",
        score_drop=4.0,
        variation=[VariationMove(row=0, col=0, color="B")],
    )
    # VariationMove 자체는 pydantic이 0-18로 제한하므로 직접 테스트 불가
    # 대신 affected_coords 범위 초과 테스트
    claim2 = CoachClaim(
        reason_type="cut_left",
        utterance="끊겼습니다.",
        score_drop=4.0,
        affected_coords=[(20, 0)],  # out of bounds
    )
    result = verify(claim2, empty_board())
    assert not result.verified
    assert "out of bounds" in result.verification_error


def test_occupied_coord_in_variation_fails():
    """이미 돌이 놓인 자리에 수순을 두면 실패."""
    board = board_with_stones([(3, 3, 1)])  # 흑돌
    claim = CoachClaim(
        reason_type="missed_attack",
        utterance="공격 기회를 놓쳤습니다.",
        score_drop=6.0,
        variation=[VariationMove(row=3, col=3, color="W")],  # occupied
    )
    result = verify(claim, board)
    assert not result.verified
    assert "occupied" in result.verification_error


def test_affected_coords_empty_spot_fails():
    """affected_coords에 빈 자리가 있으면 실패."""
    board = empty_board()  # 아무 돌도 없음
    claim = CoachClaim(
        reason_type="life_death",
        utterance="대마 위기입니다.",
        score_drop=15.0,
        affected_coords=[(5, 5)],  # 이 자리에 돌 없음
    )
    result = verify(claim, board)
    assert not result.verified
    assert "no stone" in result.verification_error


def test_fallback_replaces_utterance_on_failure():
    """검증 실패 시 utterance가 template으로 교체된다."""
    board = empty_board()
    claim = CoachClaim(
        reason_type="life_death",
        utterance="LLM이 만든 틀린 발화.",
        score_drop=12.0,
        affected_coords=[(10, 10)],  # 빈 자리
    )
    result = verify(claim, board, color_that_moved="B")
    assert not result.verified
    assert "흑" in result.utterance
    assert "12.0" in result.utterance
    assert result.variation == []


def test_suicide_in_variation_fails():
    """자충 수가 포함된 수순은 실패."""
    # 돌로 사방을 막아 자충 상황 만들기
    board = board_with_stones([
        (0, 1, 1), (1, 0, 1), (1, 2, 1), (2, 1, 1),
    ])
    claim = CoachClaim(
        reason_type="missed_attack",
        utterance="공격 기회를 놓쳤습니다.",
        score_drop=5.0,
        variation=[VariationMove(row=1, col=1, color="W")],  # 자충
    )
    result = verify(claim, board)
    assert not result.verified
    assert "suicide" in result.verification_error or "liberty" in result.verification_error.lower() or "illegal" in result.verification_error
