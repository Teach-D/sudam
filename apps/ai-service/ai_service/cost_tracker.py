"""
판당 LLM 토큰 / KataGo CPU 시간 원가 측정.

ai-service 내부에서 호출해 game_id 단위로 누적한다.
메모리 내 간이 집계 (PostgreSQL 연동은 S5에서 확장).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from collections import defaultdict

# xAI Grok 가격 (공식 사이트에서 확인: console.x.ai)
GROK_INPUT_COST_PER_1M = 0.30   # USD per 1M input tokens (grok-3-mini 기준)
GROK_OUTPUT_COST_PER_1M = 0.50  # USD per 1M output tokens


@dataclass
class GameCost:
    game_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    katago_ms: float = 0.0
    interventions: int = 0
    questions: int = 0
    started_at: float = field(default_factory=time.time)

    @property
    def llm_cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * GROK_INPUT_COST_PER_1M
            + self.output_tokens / 1_000_000 * GROK_OUTPUT_COST_PER_1M
        )

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "katago_ms": round(self.katago_ms, 1),
            "interventions": self.interventions,
            "questions": self.questions,
            "llm_cost_usd": round(self.llm_cost_usd, 6),
            "elapsed_s": round(time.time() - self.started_at, 1),
        }


class CostTracker:
    def __init__(self) -> None:
        self._games: dict[str, GameCost] = defaultdict(lambda: GameCost(game_id="unknown"))

    def _get(self, game_id: str) -> GameCost:
        if game_id not in self._games:
            self._games[game_id] = GameCost(game_id=game_id)
        return self._games[game_id]

    def record_llm(self, game_id: str, input_tokens: int, output_tokens: int) -> None:
        g = self._get(game_id)
        g.input_tokens += input_tokens
        g.output_tokens += output_tokens

    def record_katago(self, game_id: str, elapsed_ms: float) -> None:
        self._get(game_id).katago_ms += elapsed_ms

    def record_intervention(self, game_id: str) -> None:
        self._get(game_id).interventions += 1

    def record_question(self, game_id: str) -> None:
        self._get(game_id).questions += 1

    def get(self, game_id: str) -> dict:
        return self._get(game_id).to_dict()

    def summary(self) -> list[dict]:
        return [g.to_dict() for g in self._games.values()]


# 프로세스 전역 싱글톤
_tracker = CostTracker()


def get_tracker() -> CostTracker:
    return _tracker
