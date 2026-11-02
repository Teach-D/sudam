from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import IntEnum

# CPU에서 응답 지연 핵심 변수. 호출자가 명시 안 하면 이 기본값이 쓰인다.
# AI 착수와 분석/질문 모두에 쓰이는 범용 상한이므로 보수적으로.
_DEFAULT_MAX_VISITS = int(os.getenv("KATAGO_MAX_VISITS", "4"))

# AI 착수용 — 지도대국 상대 수준이면 충분. CPU에서 체감 지연 결정 요인.
KATAGO_PLAY_VISITS = int(os.getenv("KATAGO_PLAY_VISITS", "4"))

# 사범 질문 답변용 — 좌표 평가 안정성이 중요하지만 상위 수 수치 품질만 필요.
KATAGO_QUESTION_VISITS = int(os.getenv("KATAGO_QUESTION_VISITS", "16"))

# 2차 쿼리(allowMoves로 학생 지목 자리 평가) — 1차보다 가볍게.
KATAGO_USER_MOVE_VISITS = int(os.getenv("KATAGO_USER_MOVE_VISITS", "8"))


class Priority(IntEnum):
    AI_MOVE = 0   # AI 착수용 — 최고 우선순위
    ANALYSIS = 1  # 개입 판단용 — 낮은 우선순위


@dataclass
class MoveInfo:
    move: str
    visits: int
    winrate: float
    score_lead: float
    order: int
    pv: list[str] = field(default_factory=list)  # 응수 예상 수순 (최대 5수)


@dataclass
class AnalysisRequest:
    board_size: int
    moves: list[tuple[str, str]]  # [("B", "D4"), ("W", "Q16"), ...]
    rules: str = "korean"
    komi: float = 6.5
    max_visits: int = field(default_factory=lambda: _DEFAULT_MAX_VISITS)
    priority: Priority = Priority.ANALYSIS
    request_id: str = ""
    board_grid: list[list[int]] | None = None  # 0=empty,1=black,2=white (mock heuristic용)
    # board_grid와 함께 쓸 때 차례를 명시한다. pass 트릭으로 차례를 넘기면
    # KataGo가 "흑이 자발적으로 패스"로 간주해 집차가 백 쪽으로 왜곡된다.
    initial_player: str | None = None  # "B" | "W"
    # 설정 시 KataGo가 루트에서 이 수들만 평가하도록 제한한다 (학생이 지목한
    # 특정 수를 평가하기 위한 2차 쿼리에 사용).
    allow_moves: list[str] | None = None  # ["O7", ...] GTP
    # Human SL 급수 프로필 — AI 착수 요청에만 사용. 분석/사범 쿼리는 None으로 둔다.
    # KataGo는 humanSLProfile 없는 쿼리를 일반 강도로 응답한다.
    human_rank: str | None = None  # "preaz_10k" | "preaz_5k" | "preaz_1d" | "preaz_5d"


@dataclass
class AnalysisResponse:
    request_id: str
    turn_number: int
    current_player: str
    score_lead: float
    winrate: float
    score_stdev: float
    best_moves: list[MoveInfo] = field(default_factory=list)
