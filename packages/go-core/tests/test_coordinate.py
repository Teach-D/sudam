"""go_core.Coordinate 단위 테스트."""
from __future__ import annotations

import pytest
from go_core.coordinate import Coordinate


# ── SGF ───────────────────────────────────────────────────────────────────

def test_sgf_roundtrip():
    for row in range(19):
        for col in range(19):
            sgf = Coordinate.to_sgf(row, col)
            r2, c2 = Coordinate.from_sgf(sgf)
            assert (r2, c2) == (row, col), f"roundtrip fail for ({row},{col})"


def test_sgf_aa_is_origin():
    assert Coordinate.from_sgf("aa") == (0, 0)


def test_sgf_ss_is_bottom_right():
    # SGF 's' = index 18
    assert Coordinate.from_sgf("ss") == (18, 18)


def test_sgf_col_row_order():
    # SGF는 (col, row) 순서
    r, c = Coordinate.from_sgf("ba")  # col=1, row=0
    assert (r, c) == (0, 1)


def test_sgf_invalid_length():
    with pytest.raises(ValueError):
        Coordinate.from_sgf("a")

    with pytest.raises(ValueError):
        Coordinate.from_sgf("abc")


# ── 한국식 ────────────────────────────────────────────────────────────────

def test_korean_roundtrip():
    for row in range(19):
        for col in range(19):
            kr = Coordinate.to_korean(row, col)
            r2, c2 = Coordinate.from_korean(kr)
            assert (r2, c2) == (row, col), f"Korean roundtrip fail ({row},{col}): {kr}"


def test_korean_top_left():
    # row=0, col=0 → 가19 (위쪽이 19행)
    assert Coordinate.to_korean(0, 0) == "가19"
    assert Coordinate.from_korean("가19") == (0, 0)


def test_korean_bottom_left():
    # row=18, col=0 → 가1
    assert Coordinate.to_korean(18, 0) == "가1"
    assert Coordinate.from_korean("가1") == (18, 0)


def test_korean_top_right():
    # row=0, col=18 → 머19
    assert Coordinate.to_korean(0, 18) == "머19"


# ── numpy ────────────────────────────────────────────────────────────────

def test_numpy_identity():
    for row in range(19):
        for col in range(19):
            assert Coordinate.to_numpy(row, col) == (row, col)
            assert Coordinate.from_numpy(row, col) == (row, col)


# ── GTP ──────────────────────────────────────────────────────────────────

def test_gtp_a1_is_bottom_left():
    # GTP A1 = row 18, col 0
    assert Coordinate.from_gtp("A1") == (18, 0)


def test_gtp_a19_is_top_left():
    assert Coordinate.from_gtp("A19") == (0, 0)


def test_gtp_skips_i():
    # J = col 8 (skipping I)
    assert Coordinate.from_gtp("J1") == (18, 8)


def test_gtp_roundtrip():
    for row in range(19):
        for col in range(19):
            gtp = Coordinate.to_gtp(row, col)
            r2, c2 = Coordinate.from_gtp(gtp)
            assert (r2, c2) == (row, col), f"GTP roundtrip fail ({row},{col}): {gtp}"
