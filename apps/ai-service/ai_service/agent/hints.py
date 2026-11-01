from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HintStep:
    step: int          # 1, 2, 3
    label: str         # ①②③
    text: str
    variation_moves: list[dict] | None = None  # play_variation 결과


def build_hints(
    reason_type: str,
    score_drop: float,
    color_that_moved: str,
    best_move_korean: str = "",
    board_facts: dict | None = None,
) -> list[HintStep]:
    """
    3단계 힌트를 생성한다.

    ① 방향 힌트 — "무엇이 문제인가"
    ② 목적지 힌트 — "어디가 올바른 자리인가"
    ③ 정답 힌트  — "구체적인 수"

    ANTHROPIC_API_KEY 없는 경우 템플릿 기반으로 생성.
    """
    color_name = "흑" if color_that_moved == "B" else "백"

    _templates: dict[str, list[str]] = {
        "life_death": [
            f"{color_name}의 대마가 위험에 처했습니다. 단수를 피할 방법을 찾아보세요.",
            f"활로를 늘리거나 탈출로를 만드는 방향을 생각해 보세요.",
            f"최선 수는 {best_move_korean or '이 근처'}입니다. 활로가 몇 개인지 확인하세요.",
        ],
        "cut_left": [
            f"{color_name}의 돌이 끊겨 약해졌습니다. 어떤 돌이 위험한지 파악해 보세요.",
            f"끊긴 돌을 연결하거나 먼저 다른 곳에서 이득을 취할 수도 있습니다.",
            f"최선 수는 {best_move_korean or '연결점 근처'}입니다.",
        ],
        "missed_attack": [
            f"상대 {color_name}의 약한 돌을 공격할 기회가 있었습니다.",
            f"약한 돌의 활로를 줄이는 방향을 생각해 보세요.",
            f"최선 수는 {best_move_korean or '상대 약점 근처'}입니다.",
        ],
        "missed_big_point": [
            f"이 근방에 큰 자리가 있었습니다. 세력과 실리를 모두 고려해 보세요.",
            f"양쪽으로 영향을 미치는 곳이 어디인지 찾아보세요.",
            f"최선 수는 {best_move_korean or '국면의 핵심'}입니다.",
        ],
        "endgame_sente": [
            f"선수 끝내기 기회가 있었습니다. 상대가 반드시 받아야 하는 수를 찾아보세요.",
            f"선수로 집을 줄일 수 있는 곳을 확인해 보세요.",
            f"최선 수는 {best_move_korean or '끝내기 급소'}입니다.",
        ],
    }

    texts = _templates.get(
        reason_type,
        [
            "실수가 있었습니다. 어디가 문제인지 생각해 보세요.",
            "더 좋은 수가 있었습니다.",
            f"최선 수는 {best_move_korean or '이 근처'}입니다.",
        ],
    )

    labels = ["①", "②", "③"]
    return [
        HintStep(step=i + 1, label=labels[i], text=texts[i])
        for i in range(3)
    ]
