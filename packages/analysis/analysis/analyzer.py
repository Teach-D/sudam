from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MoveInfo:
    move: str
    visits: int
    winrate: float
    score_lead: float
    order: int


@dataclass
class PositionFeatures:
    turn_number: int
    current_player: str  # "B" or "W"
    score_lead: float    # positive = Black leading
    winrate: float       # Black's winrate (0.0–1.0)
    best_moves: list[MoveInfo] = field(default_factory=list)
    score_stdev: float = 0.0


def from_katago_response(response: dict) -> PositionFeatures:
    root = response.get("rootInfo", {})
    move_infos = response.get("moveInfos", [])

    best_moves = [
        MoveInfo(
            move=m["move"],
            visits=m.get("visits", 0),
            winrate=m.get("winrate", 0.5),
            score_lead=m.get("scoreLead", 0.0),
            order=m.get("order", 0),
        )
        for m in move_infos[:5]
    ]

    return PositionFeatures(
        turn_number=response.get("turnNumber", 0),
        current_player=root.get("currentPlayer", "B"),
        score_lead=root.get("scoreLead", 0.0),
        winrate=root.get("winrate", 0.5),
        best_moves=best_moves,
        score_stdev=root.get("scoreStdev", 0.0),
    )
