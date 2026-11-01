from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VariationMove(BaseModel):
    """수순 안의 단일 착수."""
    row: int = Field(ge=0, le=18)
    col: int = Field(ge=0, le=18)
    color: Literal["B", "W"]
    label: str = ""  # ①②③ 등 표시용


class CoachClaim(BaseModel):
    """
    코치 에이전트가 만든 주장.
    verifier를 통과한 것만 사용자에게 노출한다.
    """
    reason_type: str                   # ReasonType value
    utterance: str                     # 사범이 말할 텍스트
    variation: list[VariationMove] = Field(default_factory=list)

    # 근거 데이터
    score_drop: float = 0.0
    affected_coords: list[tuple[int, int]] = Field(default_factory=list)

    # 검증 결과 (verifier가 채운다)
    verified: bool = False
    verification_error: str = ""

    def as_fallback(self, reason: str) -> "CoachClaim":
        """검증 실패 시 template_fallback으로 교체된 사본 반환."""
        return self.model_copy(
            update={
                "utterance": self.utterance,
                "variation": [],
                "verified": False,
                "verification_error": reason,
            }
        )
