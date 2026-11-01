from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from go_core.coordinate import Coordinate


@dataclass
class SGFMove:
    color: str  # 'B' or 'W'
    row: int
    col: int
    move_number: int
    is_pass: bool = False


@dataclass
class SGFSetup:
    """AB/AW 초기 배치 돌 (핸디캡·문제 셋업)."""
    color: str  # 'B' or 'W'
    row: int
    col: int


@dataclass
class SGFGame:
    moves: list[SGFMove] = field(default_factory=list)
    setup: list[SGFSetup] = field(default_factory=list)
    properties: dict[str, list[str]] = field(default_factory=dict)

    def board_size(self) -> int:
        sz = self.properties.get("SZ", ["19"])
        return int(sz[0])

    def result(self) -> str:
        return self.properties.get("RE", ["?"])[0]

    def komi(self) -> float:
        return float(self.properties.get("KM", ["6.5"])[0])


# Matches a property key followed by one or more [value] brackets.
# e.g. B[cd], SZ[19], AB[aa][bb]
_PROP_RE = re.compile(r"([A-Z]+)((?:\[[^\]]*\])+)")
_VAL_RE = re.compile(r"\[([^\]]*)\]")  # captures content inside [ ]


class SGF:
    """최소 SGF 파서 — 단일 게임 파일만 지원한다."""

    @staticmethod
    def load(path: str | Path) -> SGFGame:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return SGF.parse(text)

    @staticmethod
    def parse(text: str) -> SGFGame:
        game = SGFGame()
        move_num = 1

        for m in _PROP_RE.finditer(text):
            prop_key = m.group(1)
            values = _VAL_RE.findall(m.group(2))  # list of strings inside [ ]

            if prop_key in ("B", "W"):
                for val in values:
                    if len(val) == 2:
                        row, col = Coordinate.from_sgf(val)
                        game.moves.append(SGFMove(
                            color=prop_key, row=row, col=col, move_number=move_num
                        ))
                        move_num += 1
                    elif val == "" or val == "tt":
                        game.moves.append(SGFMove(
                            color=prop_key, row=-1, col=-1, move_number=move_num, is_pass=True
                        ))
                        move_num += 1
            elif prop_key in ("AB", "AW"):
                stone_color = "B" if prop_key == "AB" else "W"
                for val in values:
                    if len(val) == 2:
                        row, col = Coordinate.from_sgf(val)
                        game.setup.append(SGFSetup(color=stone_color, row=row, col=col))
            else:
                if prop_key not in game.properties:
                    game.properties[prop_key] = []
                game.properties[prop_key].extend(values)

        return game

    @staticmethod
    def save(game: SGFGame, path: str | Path) -> None:
        path = Path(path)
        lines = ["(;"]

        # header properties
        sz = game.board_size()
        lines.append(f"SZ[{sz}]")
        if "KM" in game.properties:
            lines.append(f"KM[{game.komi()}]")
        if "RE" in game.properties:
            lines.append(f"RE[{game.result()}]")

        for move in game.moves:
            if move.is_pass:
                lines.append(f";{move.color}[]")
            else:
                sgf_coord = Coordinate.to_sgf(move.row, move.col)
                lines.append(f";{move.color}[{sgf_coord}]")

        lines.append(")")
        path.write_text("\n".join(lines), encoding="utf-8")
