"""go_core.scoring 단위 테스트 — 중국식 area scoring."""
from __future__ import annotations

import pytest
from go_core.board import Board, Color
from go_core.scoring import TerritoryMap, ScoreResult, count_territory, calculate_score


# ── 집 분류 (count_territory) ─────────────────────────────────────────────────

def test_empty_board_all_dame():
    """빈 보드 전체 361점이 공배여야 한다 (어느 쪽 집도 아님)."""
    b = Board()
    tm = count_territory(b)
    assert len(tm.dame) == 361
    assert len(tm.black) == 0
    assert len(tm.white) == 0


def test_black_encloses_corner():
    """흑이 코너 영역을 완전히 둘러싸면 흑 집."""
    b = Board()
    # (0,2), (1,2), (2,2), (2,1), (2,0) 로 좌상단 코너 3×3 영역 막기
    # . . B
    # . . B
    # B B B
    for r in range(3):
        b.place(r, 2, Color.BLACK)
    for c in range(2):
        b.place(2, c, Color.BLACK)

    tm = count_territory(b)
    # 좌상단 2×2 = (0,0),(0,1),(1,0),(1,1) 이 흑 집
    assert (0, 0) in tm.black
    assert (0, 1) in tm.black
    assert (1, 0) in tm.black
    assert (1, 1) in tm.black
    assert len(tm.white) == 0


def test_white_encloses_corner():
    """백이 코너를 둘러싸면 백 집."""
    b = Board()
    for r in range(3):
        b.place(r, 2, Color.WHITE)
    for c in range(2):
        b.place(2, c, Color.WHITE)

    tm = count_territory(b)
    assert (0, 0) in tm.white
    assert len(tm.black) == 0


def test_dame_touches_both():
    """흑과 백 사이의 빈 점은 공배."""
    b = Board()
    b.place(9, 8, Color.BLACK)
    b.place(9, 10, Color.WHITE)
    # (9, 9)는 흑·백 양쪽에 접함 → dame
    tm = count_territory(b)
    assert (9, 9) in tm.dame


def test_two_separate_regions():
    """흑 집과 백 집이 동시에 존재한다."""
    b = Board()
    # 좌상단: 흑 울타리
    for r in range(3):
        b.place(r, 3, Color.BLACK)
    b.place(3, 0, Color.BLACK)
    b.place(3, 1, Color.BLACK)
    b.place(3, 2, Color.BLACK)

    # 우하단: 백 울타리 (row 15-18, col 15-18)
    for r in range(15, 19):
        b.place(r, 15, Color.WHITE)
    b.place(15, 16, Color.WHITE)
    b.place(15, 17, Color.WHITE)
    b.place(15, 18, Color.WHITE)

    tm = count_territory(b)
    assert len(tm.black) > 0
    assert len(tm.white) > 0
    assert tm.black.isdisjoint(tm.white)
    assert tm.black.isdisjoint(tm.dame)


def test_dead_stones_removed_become_territory():
    """사석을 제거하면 그 자리가 상대 집에 포함된다."""
    b = Board()
    # 흑이 백 돌 하나를 완전히 포위
    b.place(1, 1, Color.WHITE)   # 사석이 될 백돌
    b.place(0, 1, Color.BLACK)
    b.place(2, 1, Color.BLACK)
    b.place(1, 0, Color.BLACK)
    b.place(1, 2, Color.BLACK)

    dead = frozenset([(1, 1)])
    tm = count_territory(b, dead_stones=dead)
    # (1,1)은 사석 → 빈 점으로 간주 → 흑 집 영역에 포함
    assert (1, 1) in tm.black


# ── 점수 계산 (calculate_score) ───────────────────────────────────────────────

def test_score_known_values():
    """계산값이 예측 가능한 단순 국면으로 정확성 검증.

    흑 col 9 + 백 col 10으로 수직 분할:
      - 흑 집: col 0~8 = 9열 × 19행 = 171
      - 백 집: col 11~18 = 8열 × 19행 = 152
      - 흑 돌: 19, 백 돌: 19
      - black_score = 171 + 19 = 190
      - white_score = 152 + 19 = 171
    """
    b = Board()
    for r in range(Board.SIZE):
        b.place(r, 9, Color.BLACK)
        b.place(r, 10, Color.WHITE)

    result = calculate_score(b, komi=0.0)
    assert result.black_territory == 171   # col 0~8
    assert result.white_territory == 152   # col 11~18
    assert result.black_stones == 19
    assert result.white_stones == 19
    assert result.black_score == 190.0
    assert result.white_score == 171.0
    assert result.result.startswith("B+")


def test_black_wins():
    """흑이 더 많은 영역을 가지면 흑 승."""
    b = Board()
    # 흑이 좌측 19줄 전부 장악: col 0~8 흑 돌 벽, col 9 경계
    for r in range(Board.SIZE):
        b.place(r, 9, Color.BLACK)

    result = calculate_score(b, komi=0.0)
    assert result.black_score > result.white_score
    assert result.result.startswith("B+")


def test_white_wins_with_komi():
    """komi가 충분히 크면 백 승."""
    b = Board()
    # black_score=190, white_score=171+komi → komi>19 이면 백 승
    for r in range(Board.SIZE):
        b.place(r, 9, Color.BLACK)
        b.place(r, 10, Color.WHITE)

    result = calculate_score(b, komi=19.5)
    assert result.result.startswith("W+")
    assert result.white_score > result.black_score


def test_score_result_fields():
    """ScoreResult 필드들이 정확하게 채워진다."""
    b = Board()
    # 흑 1점만 놓은 보드
    b.place(9, 9, Color.BLACK)

    result = calculate_score(b, komi=6.5)
    assert result.komi == 6.5
    assert result.black_stones == 1
    assert result.white_stones == 0
    assert result.black_score == result.black_territory + 1
    assert result.white_score == result.white_territory + 0 + 6.5
    assert isinstance(result.territory_map, TerritoryMap)


def test_dead_stones_affect_score():
    """사석은 점수에서 제외되고 상대 집에 편입된다."""
    b = Board()
    # 백 돌이 코너에 살아있는 상태 (활로 있음)
    b.place(0, 0, Color.WHITE)   # 활로 2개 — 보드에 남아 있음
    b.place(5, 5, Color.BLACK)   # 흑 돌 (먼 곳)

    no_dead = calculate_score(b, dead_stones=frozenset(), komi=0.0)
    with_dead = calculate_score(b, dead_stones=frozenset([(0, 0)]), komi=0.0)

    # 사석 선언 후 백 돌 1개 소실
    assert with_dead.white_stones == 0
    assert no_dead.white_stones == 1
    # 사석 자리 (0,0)이 흑 집 영역에 포함되어 흑 집 증가
    assert with_dead.black_territory > no_dead.black_territory


def test_result_format_black():
    """흑 승 결과 문자열 형식 확인."""
    b = Board()
    for r in range(Board.SIZE):
        b.place(r, 9, Color.BLACK)
    result = calculate_score(b, komi=0.0)
    assert result.result.startswith("B+")
    # 소수점 1자리 형식
    parts = result.result.split("+")
    float(parts[1])  # 파싱 가능해야 함


def test_result_format_white():
    """백 승 결과 문자열 형식 확인."""
    b = Board()
    for r in range(Board.SIZE):
        b.place(r, 9, Color.WHITE)
    result = calculate_score(b, komi=6.5)
    assert result.result.startswith("W+")
