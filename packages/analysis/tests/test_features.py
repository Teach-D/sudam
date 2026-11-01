from __future__ import annotations

from go_core.board import Board, Color
from analysis.features import BoardFeatures, extract_board_features, _count_atari_groups
from analysis.analyzer import MoveInfo


def _make_board(*moves: tuple[Color, int, int]) -> Board:
    board = Board()
    for color, row, col in moves:
        board.place(row, col, color)
    return board


def test_no_atari_on_empty_board():
    board = Board()
    assert _count_atari_groups(board, Color.BLACK) == 0


def test_single_stone_in_corner_has_two_liberties_not_atari():
    board = Board()
    board.place(0, 0, Color.BLACK)
    # corner stone has 2 liberties → not atari
    assert _count_atari_groups(board, Color.BLACK) == 0


def test_stone_in_atari():
    """흑 돌을 3방향이 막힌 위치에 놓으면 단수."""
    board = Board()
    # 흑 돌을 (0,1)에 놓고 주변을 백으로 막기
    board.place(0, 0, Color.BLACK)  # 흑
    board.place(1, 0, Color.WHITE)  # 아래 막기
    board.place(0, 1, Color.WHITE)  # 오른쪽 막기
    # (0,0)는 이제 활로가 0 → 따냄 발생. 대신 단수 시나리오 사용
    board2 = Board()
    board2.place(0, 1, Color.BLACK)  # 흑 (활로: 상=없음, 우=(0,2), 하=(1,1), 좌=(0,0))
    board2.place(0, 0, Color.WHITE)  # 왼쪽 막기
    board2.place(1, 1, Color.WHITE)  # 아래 막기
    board2.place(0, 2, Color.WHITE)  # 오른쪽 막기
    # (0,1) 흑은 이제 활로가 없어 따냄되어 있음.
    # 실제 단수 테스트: 별도 설정
    board3 = Board()
    # 흑 돌 하나를 두고 3면을 백으로 둘러싸서 단수(활로 1) 상태
    board3.place(5, 5, Color.BLACK)
    board3.place(4, 5, Color.WHITE)
    board3.place(6, 5, Color.WHITE)
    board3.place(5, 4, Color.WHITE)
    # 흑 (5,5)는 오른쪽 (5,6)만 활로 → 단수
    assert _count_atari_groups(board3, Color.BLACK) == 1


def test_extract_board_features_basic():
    board = Board()
    board.place(5, 5, Color.BLACK)

    best = [
        MoveInfo(move="D4", visits=100, winrate=0.52, score_lead=0.5, order=0),
        MoveInfo(move="Q16", visits=80, winrate=0.51, score_lead=0.3, order=1),
        MoveInfo(move="D16", visits=60, winrate=0.50, score_lead=0.1, order=2),
    ]

    features = extract_board_features(
        board_after=board,
        played_row=5,
        played_col=5,
        played_color=Color.BLACK,
        best_moves=best,
        score_lead_before=0.0,
        score_lead_after=0.5,
    )

    assert isinstance(features, BoardFeatures)
    assert features.local_score_delta == 0.5
    assert features.local_best_visit_avg == (100 + 80 + 60) / 3
    assert features.groups_in_atari >= 0
    assert features.opponent_groups_captured_or_atari >= 0


def test_extract_empty_best_moves():
    board = Board()
    features = extract_board_features(
        board_after=board,
        played_row=None,
        played_col=None,
        played_color=Color.BLACK,
        best_moves=[],
        score_lead_before=0.0,
        score_lead_after=0.0,
    )
    assert features.local_best_visit_avg == 0.0
    assert features.is_sente is False
