from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import FrozenSet


class Color(IntEnum):
    BLACK = 1
    WHITE = -1
    EMPTY = 0

    def opponent(self) -> "Color":
        if self == Color.BLACK:
            return Color.WHITE
        if self == Color.WHITE:
            return Color.BLACK
        raise ValueError("EMPTY has no opponent")


@dataclass(frozen=True)
class MoveResult:
    ok: bool
    captured: frozenset[tuple[int, int]] = field(default_factory=frozenset)
    error: str = ""
    is_pass: bool = False


_NEIGHBORS = ((-1, 0), (1, 0), (0, -1), (0, 1))


class Board:
    """19×19 바둑판. row=0이 위쪽(흑 시작점 쪽), col=0이 왼쪽."""

    SIZE = 19

    def __init__(self) -> None:
        self._grid: list[list[Color]] = [
            [Color.EMPTY] * self.SIZE for _ in range(self.SIZE)
        ]
        # ko: 직전 수에서 한 점을 따낸 경우 그 빈 점 좌표 (단패만 추적)
        self._ko: tuple[int, int] | None = None
        self._move_count: int = 0

    # ── 공개 인터페이스 ────────────────────────────────────────────────────

    def place(self, row: int, col: int, color: Color) -> MoveResult:
        """돌을 놓는다. 규칙 위반이면 MoveResult(ok=False)를 반환한다."""
        if not self._in_bounds(row, col):
            return MoveResult(ok=False, error="out of bounds")
        if self._grid[row][col] != Color.EMPTY:
            return MoveResult(ok=False, error="occupied")
        if (row, col) == self._ko:
            return MoveResult(ok=False, error="ko")

        # 임시로 돌을 놓아 자충·패 검사
        self._grid[row][col] = color
        captured = self._remove_dead_groups(color.opponent())

        if not self._has_liberty(row, col) and not captured:
            # 자충: 놓은 뒤 활로가 0이고 아무것도 따내지 못함
            self._grid[row][col] = Color.EMPTY
            return MoveResult(ok=False, error="self-capture")

        # 단패: 정확히 1점만 따냈고, 놓은 돌도 1점 그룹이고, 활로가 1개
        new_ko: tuple[int, int] | None = None
        if len(captured) == 1:
            group = self._get_group(row, col)
            if len(group) == 1:
                libs = self._liberties(group)
                if len(libs) == 1:
                    (new_ko,) = captured  # 따낸 점이 다음 수에서 금지점

        self._ko = new_ko
        self._move_count += 1
        return MoveResult(ok=True, captured=frozenset(captured))

    def pass_turn(self, color: Color) -> MoveResult:
        """차례를 패스한다. 패는 해소되고 수 번호가 증가한다."""
        self._ko = None
        self._move_count += 1
        return MoveResult(ok=True, is_pass=True)

    def get(self, row: int, col: int) -> Color:
        return self._grid[row][col]

    def copy(self) -> "Board":
        b = Board()
        b._grid = [row[:] for row in self._grid]
        b._ko = self._ko
        b._move_count = self._move_count
        return b

    @property
    def move_count(self) -> int:
        return self._move_count

    @property
    def ko_point(self) -> tuple[int, int] | None:
        return self._ko

    # ── 그룹·활로 ─────────────────────────────────────────────────────────

    def get_group(self, row: int, col: int) -> frozenset[tuple[int, int]]:
        """(row, col) 돌이 속한 그룹(연결된 같은 색 돌 집합)을 반환한다."""
        if self._grid[row][col] == Color.EMPTY:
            return frozenset()
        return frozenset(self._get_group(row, col))

    def get_liberties(self, row: int, col: int) -> frozenset[tuple[int, int]]:
        """그룹의 활로 집합을 반환한다."""
        if self._grid[row][col] == Color.EMPTY:
            return frozenset()
        group = self._get_group(row, col)
        return frozenset(self._liberties(group))

    def liberty_count(self, row: int, col: int) -> int:
        return len(self.get_liberties(row, col))

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────

    def _in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.SIZE and 0 <= col < self.SIZE

    def _neighbors(self, row: int, col: int):
        for dr, dc in _NEIGHBORS:
            r, c = row + dr, col + dc
            if self._in_bounds(r, c):
                yield r, c

    def _get_group(self, row: int, col: int) -> set[tuple[int, int]]:
        color = self._grid[row][col]
        visited: set[tuple[int, int]] = set()
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if (r, c) in visited:
                continue
            visited.add((r, c))
            for nr, nc in self._neighbors(r, c):
                if self._grid[nr][nc] == color and (nr, nc) not in visited:
                    stack.append((nr, nc))
        return visited

    def _liberties(self, group: set[tuple[int, int]]) -> set[tuple[int, int]]:
        libs: set[tuple[int, int]] = set()
        for r, c in group:
            for nr, nc in self._neighbors(r, c):
                if self._grid[nr][nc] == Color.EMPTY:
                    libs.add((nr, nc))
        return libs

    def _has_liberty(self, row: int, col: int) -> bool:
        group = self._get_group(row, col)
        return bool(self._liberties(group))

    def _remove_dead_groups(self, color: Color) -> list[tuple[int, int]]:
        """color 돌 중 활로가 0인 그룹을 보드에서 제거하고 따낸 좌표 목록을 반환한다."""
        captured: list[tuple[int, int]] = []
        visited: set[tuple[int, int]] = set()
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self._grid[r][c] == color and (r, c) not in visited:
                    group = self._get_group(r, c)
                    visited.update(group)
                    if not self._liberties(group):
                        for gr, gc in group:
                            self._grid[gr][gc] = Color.EMPTY
                            captured.append((gr, gc))
        return captured
