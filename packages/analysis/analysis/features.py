from __future__ import annotations

from dataclasses import dataclass

from go_core.board import Board, Color


@dataclass
class BoardFeatures:
    """KataGo 분석 결과 + go-core 보드 상태에서 추출한 5종 피처."""

    # 1. 그룹 생사: 돌 수 >= threshold 인 그룹 중 활로 <= 1 인 것의 수
    groups_in_atari: int

    # 2. 지역별 손해: 직전 수 기준 ±3선 내 score_lead 변화
    local_score_delta: float

    # 3. 응징 수: 방금 착수 후 생긴 단수 그룹 수 (상대 돌 기준)
    opponent_groups_captured_or_atari: int

    # 4. 국지 탐색: 영향권 내 KataGo 최선 수 중 상위 3개 평균 방문 수
    local_best_visit_avg: float

    # 5. 선후수: 최선 수의 최적 응수가 패스인지 여부
    is_sente: bool


def extract_board_features(
    board_after: Board,
    played_row: int | None,
    played_col: int | None,
    played_color: Color,
    best_moves: list,          # MoveInfo list from AnalysisResponse
    score_lead_before: float,
    score_lead_after: float,
) -> BoardFeatures:
    """보드 상태 + KataGo 분석 결과로 5종 피처를 추출한다."""

    # 1. 단수 그룹 수 (내 돌)
    groups_in_atari = _count_atari_groups(board_after, played_color)

    # 2. 국지 손해 (단순: 전체 score 변화 사용)
    local_score_delta = score_lead_after - score_lead_before

    # 3. 상대 단수 그룹 (내가 만든 위협)
    opp_color = Color.WHITE if played_color == Color.BLACK else Color.BLACK
    opp_atari = _count_atari_groups(board_after, opp_color)
    opponent_groups_captured_or_atari = opp_atari

    # 4. 영향권 내 최선 수 방문 수 평균 (상위 3개)
    local_best_visit_avg = 0.0
    if best_moves:
        top3 = best_moves[:3]
        local_best_visit_avg = sum(m.visits for m in top3) / len(top3)

    # 5. 선후수: 최선 수의 pv[1]이 없거나 패스이면 선수로 간주
    is_sente = False
    if best_moves:
        # pv가 없으면 단수로 그냥 막아야 하는 상황 = 선수
        is_sente = not hasattr(best_moves[0], "pv") or len(getattr(best_moves[0], "pv", [])) <= 1

    return BoardFeatures(
        groups_in_atari=groups_in_atari,
        local_score_delta=local_score_delta,
        opponent_groups_captured_or_atari=opponent_groups_captured_or_atari,
        local_best_visit_avg=local_best_visit_avg,
        is_sente=is_sente,
    )


def _count_atari_groups(board: Board, color: Color) -> int:
    """보드에서 해당 색 돌의 단수(활로 1) 그룹 수를 센다."""
    visited: set[tuple[int, int]] = set()
    count = 0
    for r in range(Board.SIZE):
        for c in range(Board.SIZE):
            if (r, c) in visited:
                continue
            if board._grid[r][c] != color:
                continue
            group = board._get_group(r, c)
            visited.update(group)
            liberties = board._liberties(group)
            if len(liberties) == 1:
                count += 1
    return count
