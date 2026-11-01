"""go_core.SGF 단위 테스트."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from go_core.sgf import SGF, SGFGame, SGFMove, SGFSetup


SIMPLE_SGF = """\
(;GM[1]FF[4]SZ[19]KM[6.5]RE[B+R]
;B[pd];W[dp];B[pp];W[dd]
;B[fc];W[cf])
"""

PASS_SGF = """\
(;GM[1]SZ[19]
;B[pd];W[];B[pp])
"""


# ── 파싱 ────────────────────────────────────────────────────────────────────

def test_parse_move_count():
    game = SGF.parse(SIMPLE_SGF)
    assert len(game.moves) == 6


def test_parse_colors():
    game = SGF.parse(SIMPLE_SGF)
    colors = [m.color for m in game.moves]
    assert colors == ["B", "W", "B", "W", "B", "W"]


def test_parse_first_move_coord():
    game = SGF.parse(SIMPLE_SGF)
    # B[pd] → SGF from_sgf('pd'): col=p(15), row=d(3)
    m = game.moves[0]
    assert m.color == "B"
    assert m.row == 3
    assert m.col == 15


def test_parse_properties():
    game = SGF.parse(SIMPLE_SGF)
    assert game.board_size() == 19
    assert game.komi() == 6.5
    assert game.result() == "B+R"


def test_parse_pass_move_included():
    """패스 수도 SGFMove(is_pass=True)로 포함되어야 한다."""
    game = SGF.parse(PASS_SGF)
    # B[pd], W[], B[pp] — 총 3수
    assert len(game.moves) == 3
    pass_move = game.moves[1]
    assert pass_move.is_pass
    assert pass_move.color == "W"
    assert pass_move.move_number == 2


def test_parse_move_numbers():
    game = SGF.parse(SIMPLE_SGF)
    nums = [m.move_number for m in game.moves]
    assert nums == [1, 2, 3, 4, 5, 6]


# ── 저장 & 재로드 ───────────────────────────────────────────────────────────

def test_save_and_reload():
    game = SGF.parse(SIMPLE_SGF)
    with tempfile.NamedTemporaryFile(suffix=".sgf", delete=False) as f:
        tmp = Path(f.name)
    try:
        SGF.save(game, tmp)
        game2 = SGF.load(tmp)
        assert len(game2.moves) == len(game.moves)
        for m1, m2 in zip(game.moves, game2.moves):
            assert m1.color == m2.color
            assert m1.row == m2.row
            assert m1.col == m2.col
    finally:
        tmp.unlink(missing_ok=True)


def test_save_produces_valid_sgf():
    game = SGFGame(
        moves=[SGFMove("B", 3, 15, 1), SGFMove("W", 15, 3, 2)],
        properties={"SZ": ["19"], "KM": ["6.5"], "RE": ["B+R"]},
    )
    with tempfile.NamedTemporaryFile(suffix=".sgf", delete=False) as f:
        tmp = Path(f.name)
    try:
        SGF.save(game, tmp)
        text = tmp.read_text()
        assert "B[" in text
        assert "W[" in text
    finally:
        tmp.unlink(missing_ok=True)


# ── AB/AW 핸디캡·셋업 ────────────────────────────────────────────────────────

HANDICAP_SGF = """\
(;GM[1]SZ[19]HA[2]KM[0.5]
AB[pd][dp]
;W[pp];B[dd])
"""


def test_parse_ab_setup():
    """AB[] 핸디캡 돌이 game.setup에 포함되어야 한다."""
    game = SGF.parse(HANDICAP_SGF)
    assert len(game.setup) == 2
    colors = {s.color for s in game.setup}
    assert colors == {"B"}


def test_parse_ab_coords():
    """AB[pd] → row=3, col=15."""
    game = SGF.parse(HANDICAP_SGF)
    coords = {(s.row, s.col) for s in game.setup}
    assert (3, 15) in coords   # pd
    assert (15, 3) in coords   # dp


def test_parse_aw_setup():
    """AW[] 돌도 game.setup에 포함되어야 한다."""
    aw_sgf = "(;GM[1]SZ[19]AW[aa][bb];B[cc])"
    game = SGF.parse(aw_sgf)
    assert len(game.setup) == 2
    assert all(s.color == "W" for s in game.setup)


def test_setup_does_not_appear_in_moves():
    """AB/AW는 moves가 아닌 setup에만 들어가야 한다."""
    game = SGF.parse(HANDICAP_SGF)
    assert len(game.moves) == 2  # W[pp], B[dd]


# ── fixture SGF 파일 (fixtures/sgf/) ────────────────────────────────────────

SGF_FIXTURE_DIR = Path(__file__).parents[3] / "fixtures" / "sgf"


def test_fixture_capture_sgf():
    """fixtures/sgf/capture.sgf — 따냄 검증."""
    path = SGF_FIXTURE_DIR / "capture.sgf"
    if not path.exists():
        pytest.skip("fixture not found")
    game = SGF.load(path)
    assert len(game.moves) > 0


def test_fixture_ko_sgf():
    """fixtures/sgf/ko.sgf — 패 검증."""
    path = SGF_FIXTURE_DIR / "ko.sgf"
    if not path.exists():
        pytest.skip("fixture not found")
    game = SGF.load(path)
    assert len(game.moves) > 0
