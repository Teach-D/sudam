"""go_core.Board 단위 테스트 — fixtures/sgf/ SGF 파일 포함."""
from __future__ import annotations

import pytest
from go_core.board import Board, Color, MoveResult


# ── 기본 착수 ──────────────────────────────────────────────────────────────

def test_place_empty_board():
    b = Board()
    r = b.place(3, 3, Color.BLACK)
    assert r.ok
    assert b.get(3, 3) == Color.BLACK


def test_place_occupied():
    b = Board()
    b.place(3, 3, Color.BLACK)
    r = b.place(3, 3, Color.WHITE)
    assert not r.ok
    assert "occupied" in r.error


def test_place_out_of_bounds():
    b = Board()
    assert not b.place(-1, 0, Color.BLACK).ok
    assert not b.place(0, 19, Color.BLACK).ok
    assert not b.place(19, 19, Color.BLACK).ok


def test_move_count():
    b = Board()
    b.place(0, 0, Color.BLACK)
    b.place(1, 0, Color.WHITE)
    assert b.move_count == 2


# ── 따냄 (capture) ────────────────────────────────────────────────────────

def test_capture_single_stone():
    """사방에 백을 두어 흑 1점 따냄."""
    b = Board()
    b.place(1, 1, Color.BLACK)
    b.place(0, 1, Color.WHITE)
    b.place(2, 1, Color.WHITE)
    b.place(1, 0, Color.WHITE)
    result = b.place(1, 2, Color.WHITE)
    assert result.ok
    assert (1, 1) in result.captured
    assert b.get(1, 1) == Color.EMPTY


def test_capture_corner_stone():
    """(0,0) 모서리에서 흑 1점 따냄 — 활로 2개."""
    b = Board()
    b.place(0, 0, Color.BLACK)
    b.place(0, 1, Color.WHITE)
    result = b.place(1, 0, Color.WHITE)
    assert result.ok
    assert (0, 0) in result.captured


def test_capture_group():
    """흑 2점 그룹 따냄."""
    b = Board()
    b.place(1, 1, Color.BLACK)
    b.place(1, 2, Color.BLACK)
    # 백이 사방 포위
    b.place(0, 1, Color.WHITE)
    b.place(0, 2, Color.WHITE)
    b.place(1, 0, Color.WHITE)
    b.place(2, 1, Color.WHITE)
    b.place(2, 2, Color.WHITE)
    result = b.place(1, 3, Color.WHITE)
    assert result.ok
    assert frozenset([(1, 1), (1, 2)]) == result.captured
    assert b.get(1, 1) == Color.EMPTY
    assert b.get(1, 2) == Color.EMPTY


def test_capture_opponent_before_self_check():
    """착수 후 상대를 먼저 따내야 자충이 아닌 경우.

    국면 (코너):
      * W .     ← 흑이 (0,0)에 놓음 — W(0,1)·W(1,0) 모두 활로 0
      W B .       → 둘 다 따냄 → 흑(0,0)이 활로 2개 확보 → 자충 아님
      B . .
    """
    b = Board()
    b.place(0, 2, Color.BLACK)
    b.place(1, 1, Color.BLACK)
    b.place(2, 0, Color.BLACK)
    b.place(0, 1, Color.WHITE)  # (0,0)만이 활로
    b.place(1, 0, Color.WHITE)  # (0,0)만이 활로
    r = b.place(0, 0, Color.BLACK)
    assert r.ok
    assert frozenset([(0, 1), (1, 0)]) == r.captured


# ── 자충 (self-capture) ───────────────────────────────────────────────────

def test_self_capture_forbidden():
    """활로가 없는 점에 돌을 놓으면 자충으로 거부된다."""
    b = Board()
    # (0,0) 주변을 백으로 막기
    b.place(0, 1, Color.WHITE)
    b.place(1, 0, Color.WHITE)
    r = b.place(0, 0, Color.BLACK)
    assert not r.ok
    assert "self-capture" in r.error
    assert b.get(0, 0) == Color.EMPTY


def test_self_capture_group_forbidden():
    """2점 그룹이 자충이 되는 경우."""
    b = Board()
    b.place(0, 0, Color.BLACK)
    b.place(0, 2, Color.WHITE)
    b.place(1, 0, Color.WHITE)
    b.place(1, 1, Color.WHITE)
    # (0,1)은 흑이 놓으면 흑 그룹 (0,0)-(0,1)이 됨
    # 활로: (0,0)의 활로는 이미 모두 막혀 있고, (0,1) 자체도 막혀있어야 자충
    # (0,1)의 이웃: (0,0)=흑, (0,2)=백, (1,1)=백 → 활로 없음 → 자충
    r = b.place(0, 1, Color.BLACK)
    assert not r.ok
    assert "self-capture" in r.error


# ── 패 (ko) ───────────────────────────────────────────────────────────────

def test_basic_ko():
    """단패 상황 — 방금 따낸 점에 즉시 되돌릴 수 없다.

    패 모양 (col→, row↓):
      . B W .
      B W . W
      . B W .
    흑이 (1,2)에 두어 백 (1,1)을 따냄 → ko_point = (1,1).
    백이 즉시 (1,1)에 두려 하면 거부.
    """
    b = Board()
    # 백 (1,1)을 먼저 놓고 순서대로 포위
    b.place(1, 1, Color.WHITE)
    b.place(0, 1, Color.BLACK)
    b.place(1, 0, Color.BLACK)
    b.place(2, 1, Color.BLACK)
    b.place(0, 2, Color.WHITE)
    b.place(1, 3, Color.WHITE)
    b.place(2, 2, Color.WHITE)
    # 흑이 (1,2)에 두어 백 (1,1) 따냄
    r = b.place(1, 2, Color.BLACK)
    assert r.ok
    assert (1, 1) in r.captured
    assert b.ko_point == (1, 1)
    # 백이 즉시 (1,1)에 두면 ko 위반
    r2 = b.place(1, 1, Color.WHITE)
    assert not r2.ok
    assert "ko" in r2.error


def test_ko_cleared_after_other_move():
    """다른 점에 둔 뒤에는 패 금지가 풀린다."""
    b = Board()
    b.place(1, 1, Color.WHITE)
    b.place(0, 1, Color.BLACK)
    b.place(1, 0, Color.BLACK)
    b.place(2, 1, Color.BLACK)
    b.place(0, 2, Color.WHITE)
    b.place(1, 3, Color.WHITE)
    b.place(2, 2, Color.WHITE)
    b.place(1, 2, Color.BLACK)   # 흑이 (1,1) 따냄 → ko at (1,1)
    b.place(18, 18, Color.WHITE) # 백이 다른 곳에 둠 → ko 해소
    r = b.place(1, 1, Color.BLACK)
    assert r.ok  # 이제 흑이 (1,1)에 둘 수 있음


def test_ko_not_triggered_for_multiple_capture():
    """2점 이상 따낸 경우 ko가 발생하지 않는다."""
    b = Board()
    b.place(0, 0, Color.WHITE)
    b.place(0, 1, Color.WHITE)
    b.place(1, 0, Color.BLACK)
    b.place(1, 1, Color.BLACK)
    b.place(0, 2, Color.BLACK)
    r = b.place(2, 0, Color.BLACK)  # 백 2점 따냄
    # 2점이므로 패 미발생
    assert r.ok
    assert b.ko_point is None


# ── 그룹 & 활로 ───────────────────────────────────────────────────────────

def test_group_single():
    b = Board()
    b.place(5, 5, Color.BLACK)
    g = b.get_group(5, 5)
    assert g == frozenset([(5, 5)])


def test_group_connected():
    b = Board()
    b.place(5, 5, Color.BLACK)
    b.place(5, 6, Color.BLACK)
    b.place(5, 7, Color.BLACK)
    g = b.get_group(5, 5)
    assert g == frozenset([(5, 5), (5, 6), (5, 7)])


def test_group_not_diagonal():
    """대각선은 연결되지 않는다."""
    b = Board()
    b.place(5, 5, Color.BLACK)
    b.place(6, 6, Color.BLACK)
    g = b.get_group(5, 5)
    assert g == frozenset([(5, 5)])


def test_liberties_center():
    b = Board()
    b.place(9, 9, Color.BLACK)
    libs = b.get_liberties(9, 9)
    assert libs == frozenset([(8, 9), (10, 9), (9, 8), (9, 10)])


def test_liberties_corner():
    b = Board()
    b.place(0, 0, Color.BLACK)
    libs = b.get_liberties(0, 0)
    assert libs == frozenset([(0, 1), (1, 0)])


def test_liberties_decrease_with_opponent():
    b = Board()
    b.place(9, 9, Color.BLACK)
    b.place(9, 10, Color.WHITE)
    assert b.liberty_count(9, 9) == 3


def test_empty_cell_returns_empty_group():
    b = Board()
    assert b.get_group(0, 0) == frozenset()
    assert b.get_liberties(0, 0) == frozenset()


# ── 패스 (pass) ───────────────────────────────────────────────────────────

def test_pass_returns_ok():
    b = Board()
    r = b.pass_turn(Color.BLACK)
    assert r.ok
    assert r.is_pass


def test_pass_increments_move_count():
    b = Board()
    b.place(3, 3, Color.BLACK)
    b.pass_turn(Color.WHITE)
    assert b.move_count == 2


def test_pass_clears_ko():
    """패스하면 패 금지가 해제된다."""
    b = Board()
    b.place(1, 1, Color.WHITE)
    b.place(0, 1, Color.BLACK)
    b.place(1, 0, Color.BLACK)
    b.place(2, 1, Color.BLACK)
    b.place(0, 2, Color.WHITE)
    b.place(1, 3, Color.WHITE)
    b.place(2, 2, Color.WHITE)
    b.place(1, 2, Color.BLACK)   # 흑이 (1,1) 따냄 → ko at (1,1)
    assert b.ko_point == (1, 1)
    b.pass_turn(Color.WHITE)     # 백이 패스 → ko 해소
    assert b.ko_point is None


def test_pass_does_not_change_board():
    """패스해도 보드 상태는 변하지 않는다."""
    b = Board()
    b.place(5, 5, Color.BLACK)
    b.pass_turn(Color.WHITE)
    assert b.get(5, 5) == Color.BLACK
    for r in range(Board.SIZE):
        for c in range(Board.SIZE):
            if (r, c) != (5, 5):
                assert b.get(r, c) == Color.EMPTY


# ── 보드 복사 ─────────────────────────────────────────────────────────────

def test_copy_independence():
    b = Board()
    b.place(3, 3, Color.BLACK)
    b2 = b.copy()
    b2.place(4, 4, Color.WHITE)
    assert b.get(4, 4) == Color.EMPTY
    assert b2.get(3, 3) == Color.BLACK
