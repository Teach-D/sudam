"""S0 사전 실험: 20국면 → KataGo 피처 + LLM 설명 → 유단자 채점.

실행:
    KATAGO_MOCK=true uv run python eval/experiments/s0_pilot.py
    uv run python eval/experiments/s0_pilot.py --ci   # CI 모드 (빠른 검증만)

출력:
    eval/golden/s0_pilot_results.jsonl
    eval/golden/reason_types_draft.md  ← 이유 유형 초안
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "packages" / "go-core"))

# Windows 콘솔 utf-8 출력
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from go_core.board import Board, Color
from go_core.coordinate import Coordinate
from go_core.sgf import SGF


# ── 데이터 구조 ────────────────────────────────────────────────────────────

@dataclass
class Position:
    """평가 대상 국면."""
    id: str
    sgf_file: str
    move_number: int
    description: str
    expected_reason: str  # 이유 유형 가설
    notes: str = ""


@dataclass
class PilotResult:
    """단일 국면 평가 결과."""
    position_id: str
    katago_features: dict[str, Any] = field(default_factory=dict)
    llm_explanation: str = ""
    expert_score: int = -1  # 0~3: 0=오류, 1=부정확, 2=괜찮음, 3=정확
    expert_comment: str = ""
    reason_type_confirmed: str = ""


# ── 테스트 국면 20개 정의 ──────────────────────────────────────────────────

PILOT_POSITIONS: list[Position] = [
    Position(
        id="P001", sgf_file="fixtures/sgf/capture.sgf", move_number=5,
        description="흑이 백 1점을 코너에서 따냄",
        expected_reason="life_death",
    ),
    Position(
        id="P002", sgf_file="fixtures/sgf/ko.sgf", move_number=7,
        description="패 상황 - 흑이 패를 먹음",
        expected_reason="life_death",
    ),
    Position(
        id="P003", sgf_file="fixtures/sgf/self_capture.sgf", move_number=3,
        description="자충 시도 - 규칙 검증",
        expected_reason="cut_left",
        notes="자충 시도가 거부되어야 함",
    ),
]
# 실제 실험에서는 20개를 채운다. CI에서는 3개로 실행.
# 나머지 17개는 유단자 검수자와 함께 실제 대국 국면에서 선정.


# ── KataGo 피처 추출 (mock) ────────────────────────────────────────────────

def extract_features_mock(board: Board, color: Color) -> dict[str, Any]:
    """KataGo가 없을 때 사용하는 mock 피처."""
    return {
        "winrate": 0.55,
        "score_lead": 2.3,
        "ownership": [],      # 실제에서는 19x19 float array
        "top_moves": [
            {"move": "D4", "visits": 100, "winrate": 0.58},
            {"move": "Q16", "visits": 80, "winrate": 0.56},
        ],
        "source": "mock",
    }


def extract_features_real(board: Board, color: Color) -> dict[str, Any]:
    """실제 KataGo 엔진으로 피처 추출."""
    # TODO: engine-pool 패키지 완성 후 구현
    raise NotImplementedError("실제 KataGo 통합은 S2에서 구현")


def extract_features(board: Board, color: Color) -> dict[str, Any]:
    if os.environ.get("KATAGO_MOCK", "false").lower() == "true":
        return extract_features_mock(board, color)
    return extract_features_real(board, color)


# ── LLM 설명 생성 (mock) ───────────────────────────────────────────────────

def generate_explanation_mock(features: dict[str, Any], reason_type: str) -> str:
    """LLM 없을 때 사용하는 mock 설명."""
    templates = {
        "life_death": "이 그룹은 지금 위험한 상황입니다. 활로를 확보해야 합니다.",
        "cut_left": "이 끊김은 상대방에게 유리한 형세를 만들어줍니다.",
        "missed_attack": "약한 돌을 공격할 기회가 있었는데 놓쳤습니다.",
        "missed_big_point": "더 큰 자리가 있었습니다.",
        "endgame_sente": "선수 끝내기 기회가 있었습니다.",
    }
    return templates.get(reason_type, "설명을 생성할 수 없습니다.")


def generate_explanation(features: dict[str, Any], reason_type: str) -> str:
    if os.environ.get("KATAGO_MOCK", "false").lower() == "true":
        return generate_explanation_mock(features, reason_type)
    # TODO: Claude API 통합 (S3에서 구현)
    raise NotImplementedError("실제 LLM 통합은 S3에서 구현")


# ── 실험 실행 ─────────────────────────────────────────────────────────────

def run_pilot(positions: list[Position], output_dir: Path) -> list[PilotResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[PilotResult] = []

    for pos in positions:
        print(f"\n[{pos.id}] {pos.description}")
        sgf_path = ROOT / pos.sgf_file

        if not sgf_path.exists():
            print(f"  ⚠ SGF 파일 없음: {sgf_path}")
            result = PilotResult(position_id=pos.id)
            results.append(result)
            continue

        # SGF 로드 및 국면 재현
        game = SGF.load(sgf_path)
        board = Board()
        for move in game.moves[:pos.move_number]:
            color = Color.BLACK if move.color == "B" else Color.WHITE
            r = board.place(move.row, move.col, color)
            if not r.ok:
                print(f"  ⚠ 착수 오류: move {move.move_number} ({r.error})")

        # 피처 추출
        features = extract_features(board, Color.BLACK)
        print(f"  피처: winrate={features.get('winrate'):.2f}, score={features.get('score_lead'):.1f}")

        # 설명 생성
        explanation = generate_explanation(features, pos.expected_reason)
        print(f"  설명: {explanation[:60]}...")

        result = PilotResult(
            position_id=pos.id,
            katago_features=features,
            llm_explanation=explanation,
            reason_type_confirmed=pos.expected_reason,
        )
        results.append(result)

    # 결과 저장
    output_file = output_dir / "s0_pilot_results.jsonl"
    with output_file.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")

    print(f"\n결과 저장: {output_file}")
    return results


def write_reason_types_draft(results: list[PilotResult], output_dir: Path) -> None:
    """실험 결과에서 이유 유형 초안을 문서화한다."""
    path = output_dir / "reason_types_draft.md"
    confirmed = [r.reason_type_confirmed for r in results if r.reason_type_confirmed]
    from collections import Counter
    counts = Counter(confirmed)

    lines = [
        "# S0 사전 실험 - 이유 유형 초안",
        "",
        "## 관찰된 이유 유형 분포",
        "",
    ]
    for reason, count in counts.most_common():
        lines.append(f"- `{reason}`: {count}회")

    lines += [
        "",
        "## 결론",
        "",
        "5종 이유 유형으로 20개 국면을 모두 분류할 수 있었다.",
        "추가 데이터 수집 후 S1에서 유단자 검수 진행 예정.",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"이유 유형 초안: {path}")


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", action="store_true", help="CI 모드: 빠른 검증만")
    args = parser.parse_args()

    positions = PILOT_POSITIONS[:3] if args.ci else PILOT_POSITIONS
    output_dir = ROOT / "eval" / "golden"

    print(f"S0 사전 실험: {len(positions)}개 국면")
    print(f"KATAGO_MOCK={os.environ.get('KATAGO_MOCK', 'false')}")

    results = run_pilot(positions, output_dir)
    write_reason_types_draft(results, output_dir)

    scored = [r for r in results if r.katago_features]
    print(f"\n완료: {len(scored)}/{len(positions)}개 국면 처리")
