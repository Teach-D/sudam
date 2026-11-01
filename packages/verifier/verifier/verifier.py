from __future__ import annotations

from go_core.board import Board, Color
from .schema import CoachClaim, VariationMove

# 이유 유형별 템플릿 (검증 실패 시 대체)
TEMPLATE_FALLBACKS: dict[str, str] = {
    "life_death": "{color}이 방금 큰 그룹의 생사에 영향을 주는 수를 두었습니다. "
                  "점수 차이가 약 {drop:.1f}집 발생했습니다.",
    "cut_left": "{color}의 돌이 끊겨 약한 그룹이 생겼습니다. "
                "점수 차이가 약 {drop:.1f}집 발생했습니다.",
    "missed_attack": "{color}이 약한 상대 돌을 공격할 기회를 놓쳤습니다. "
                     "점수 차이가 약 {drop:.1f}집입니다.",
    "missed_big_point": "{color}이 국지적으로 큰 자리를 놓쳤습니다. "
                        "점수 차이가 약 {drop:.1f}집입니다.",
    "endgame_sente": "{color}이 선수 끝내기 기회를 놓쳤습니다. "
                     "점수 차이가 약 {drop:.1f}집입니다.",
}


def verify(
    claim: CoachClaim,
    board_state: list[list[int]],
    color_that_moved: str = "B",
) -> CoachClaim:
    """
    주장을 검증한다.

    검사 순서:
      1. 좌표 존재: 수순의 모든 좌표가 보드 안에 있는지
      2. 수순 증명: 보드에서 수순을 실제로 재생해 규칙 위반 없는지
      3. 그룹 상태: affected_coords가 비어 있지 않으면 해당 좌표에 돌이 있는지

    실패 → verification_error 설정 + template_fallback 텍스트로 utterance 교체.
    성공 → verified=True.
    """
    # 1. 좌표 존재
    for mv in claim.variation:
        if not (0 <= mv.row <= 18 and 0 <= mv.col <= 18):
            return _fallback(claim, f"out-of-bounds coord ({mv.row},{mv.col})", color_that_moved)

    # 2. 수순 증명 — 수순이 있을 때만 재생
    if claim.variation:
        error = _play_sequence(board_state, claim.variation)
        if error:
            return _fallback(claim, error, color_that_moved)

    # 3. 그룹 상태: affected_coords 돌 존재 확인
    for r, c in claim.affected_coords:
        if not (0 <= r <= 18 and 0 <= c <= 18):
            return _fallback(claim, f"affected coord out of bounds ({r},{c})", color_that_moved)
        if board_state[r][c] == 0:
            return _fallback(claim, f"no stone at affected coord ({r},{c})", color_that_moved)

    return claim.model_copy(update={"verified": True, "verification_error": ""})


def _play_sequence(
    board_state: list[list[int]],
    moves: list[VariationMove],
) -> str:
    """
    보드 상태 위에서 수순을 재생한다.
    규칙 위반이 있으면 에러 메시지를 반환하고, 없으면 "" 반환.
    """
    board = _board_from_state(board_state)
    for mv in moves:
        color = Color.BLACK if mv.color == "B" else Color.WHITE
        result = board.place(mv.row, mv.col, color)
        if not result.ok:
            return (
                f"illegal move at ({mv.row},{mv.col}) color={mv.color}: {result.error}"
            )
    return ""


def _board_from_state(state: list[list[int]]) -> Board:
    """list[list[int]] (0=빈, 1=흑, 2=백) → Board."""
    board = Board()
    for r, row in enumerate(state):
        for c, v in enumerate(row):
            if v == 1:
                board._grid[r][c] = Color.BLACK
            elif v == 2:
                board._grid[r][c] = Color.WHITE
    return board


def _fallback(claim: CoachClaim, reason: str, color_that_moved: str) -> CoachClaim:
    color_name = "흑" if color_that_moved == "B" else "백"
    template = TEMPLATE_FALLBACKS.get(
        claim.reason_type,
        "{color}이 실수를 했습니다 ({drop:.1f}집).",
    )
    fallback_text = template.format(color=color_name, drop=claim.score_drop)
    return claim.model_copy(
        update={
            "utterance": fallback_text,
            "variation": [],
            "verified": False,
            "verification_error": reason,
        }
    )
