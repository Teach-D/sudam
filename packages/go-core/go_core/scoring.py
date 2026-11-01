from __future__ import annotations

from dataclasses import dataclass

from go_core.board import Board, Color


@dataclass(frozen=True)
class TerritoryMap:
    """집 분류 결과."""
    black: frozenset[tuple[int, int]]   # 흑 집 (빈 점)
    white: frozenset[tuple[int, int]]   # 백 집 (빈 점)
    dame: frozenset[tuple[int, int]]    # 공배 (어느 쪽도 아님)


@dataclass(frozen=True)
class ScoreResult:
    """중국식 area scoring 결과."""
    black_territory: int    # 흑 집 (빈 점 수)
    white_territory: int    # 백 집 (빈 점 수)
    black_stones: int       # 보드 위 살아있는 흑돌
    white_stones: int       # 보드 위 살아있는 백돌
    komi: float
    black_score: float      # black_territory + black_stones
    white_score: float      # white_territory + white_stones + komi
    result: str             # "B+6.5" / "W+2.5" / "Jigo"
    territory_map: TerritoryMap


def count_territory(
    board: Board,
    dead_stones: frozenset[tuple[int, int]] = frozenset(),
) -> TerritoryMap:
    """빈 영역을 flood-fill해 흑 집 / 백 집 / 공배로 분류한다.

    dead_stones 위치는 EMPTY로 간주한다.
    빅(seki)처럼 흑·백 양쪽에 접한 영역은 공배로 처리한다.
    """
    grid = board._grid
    size = board.SIZE

    def _color_at(r: int, c: int) -> Color:
        if (r, c) in dead_stones:
            return Color.EMPTY
        return grid[r][c]

    black_pts: set[tuple[int, int]] = set()
    white_pts: set[tuple[int, int]] = set()
    dame_pts: set[tuple[int, int]] = set()

    visited: set[tuple[int, int]] = set()

    for start_r in range(size):
        for start_c in range(size):
            if (start_r, start_c) in visited:
                continue
            if _color_at(start_r, start_c) != Color.EMPTY:
                continue

            # BFS: 연결된 빈 영역(region) 탐색
            region: set[tuple[int, int]] = set()
            borders: set[Color] = set()
            stack = [(start_r, start_c)]

            while stack:
                r, c = stack.pop()
                if (r, c) in visited:
                    continue
                if _color_at(r, c) != Color.EMPTY:
                    borders.add(_color_at(r, c))
                    continue
                visited.add((r, c))
                region.add((r, c))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < size and 0 <= nc < size and (nr, nc) not in visited:
                        stack.append((nr, nc))

            # 영역 분류
            if borders == {Color.BLACK}:
                black_pts.update(region)
            elif borders == {Color.WHITE}:
                white_pts.update(region)
            else:
                dame_pts.update(region)

    return TerritoryMap(
        black=frozenset(black_pts),
        white=frozenset(white_pts),
        dame=frozenset(dame_pts),
    )


def calculate_score(
    board: Board,
    dead_stones: frozenset[tuple[int, int]] = frozenset(),
    komi: float = 6.5,
) -> ScoreResult:
    """중국식 area scoring을 계산한다.

    Score(Black) = 흑 집 + 살아있는 흑돌
    Score(White) = 백 집 + 살아있는 백돌 + komi
    """
    territory = count_territory(board, dead_stones)

    black_stones = sum(
        1
        for r in range(board.SIZE)
        for c in range(board.SIZE)
        if board._grid[r][c] == Color.BLACK and (r, c) not in dead_stones
    )
    white_stones = sum(
        1
        for r in range(board.SIZE)
        for c in range(board.SIZE)
        if board._grid[r][c] == Color.WHITE and (r, c) not in dead_stones
    )

    black_score = float(len(territory.black) + black_stones)
    white_score = float(len(territory.white) + white_stones) + komi

    diff = black_score - white_score
    if diff > 0:
        result = f"B+{diff:.1f}"
    elif diff < 0:
        result = f"W+{(-diff):.1f}"
    else:
        result = "Jigo"

    return ScoreResult(
        black_territory=len(territory.black),
        white_territory=len(territory.white),
        black_stones=black_stones,
        white_stones=white_stones,
        komi=komi,
        black_score=black_score,
        white_score=white_score,
        result=result,
        territory_map=territory,
    )
