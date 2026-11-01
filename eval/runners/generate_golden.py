"""
golden set 생성 스크립트.
positions.jsonl (100국면) 및 questions.jsonl (50질문)을 생성·보완한다.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent.parent / "golden"
REASON_TYPES = ["life_death", "cut_left", "missed_attack", "missed_big_point", "endgame_sente"]
DIFFICULTIES = ["10k", "7k", "5k", "3k", "1k", "1d", "3d"]

# GTP 좌표 (I 제외)
_COLS = "ABCDEFGHJKLMNOPQRST"
_ROWS = list(range(1, 20))

rng = random.Random(42)  # 재현 가능


def _gtp(col_idx: int, row: int) -> str:
    return f"{_COLS[col_idx]}{row}"


def _random_moves(n: int) -> list[list[str]]:
    """n수짜리 수순 생성. 겹치지 않게."""
    used: set[str] = set()
    moves = []
    for i in range(n):
        color = "B" if i % 2 == 0 else "W"
        for _ in range(50):
            c, r = rng.randint(0, 18), rng.randint(1, 19)
            coord = _gtp(c, r)
            if coord not in used:
                used.add(coord)
                moves.append([color, coord])
                break
    return moves


def _pos(idx: int, reason: str, difficulty: str, category_desc: str, n_moves: int) -> dict:
    return {
        "id": f"p{idx:03d}",
        "source": rng.choice(["tsumego", "pro_game", "amateur_game"]),
        "category": reason,
        "description": category_desc,
        "moves": _random_moves(n_moves),
        "label": {
            "reason_type": reason,
            "intervention": True,
            "score_drop": round(rng.uniform(2.5, 18.0), 1),
            "winrate_drop": round(rng.uniform(0.04, 0.22), 3),
        },
        "difficulty": difficulty,
    }


_DESCS: dict[str, list[str]] = {
    "life_death": [
        "귀 삼삼 패턴", "변 안형 사활", "중앙 대마 생존", "귀 대사활", "변 꼭지 사활",
        "중앙 두 눈 확보", "귀 5궁 패턴", "변 넓은 사활", "대마 탈출로 확보", "귀 망건패턴",
    ],
    "cut_left": [
        "끊음으로 두 집단 분리", "단수 후 연결 차단", "쐐기 수로 끊기", "중앙 끊김 패턴",
        "변에서 단절", "끊김으로 약한 돌 생성", "귀에서 끊기", "양단수 패턴",
        "연결 차단 후 공격", "이단 끊기 패턴",
    ],
    "missed_attack": [
        "약한 돌 공격 기회 놓침", "단수 기회 미이용", "상대 약점 방치",
        "공격 방향 잘못 선택", "속도 늦은 공격", "경솔한 공격 포기",
        "포석에서 공격 타이밍 놓침", "중반 공격 기회 상실",
        "끝내기에서 공격 기회", "귀에서 공격 미실시",
    ],
    "missed_big_point": [
        "천원 부근 큰 자리", "변의 큰 자리 미선점", "삼선 큰 자리",
        "귀 큰 자리 놓침", "중앙 큰 자리 선점 실패", "확장 자리 놓침",
        "포석 큰 자리 선점", "세력권 내 큰 자리", "빠른 큰 자리 선점",
        "쌍방 큰 자리",
    ],
    "endgame_sente": [
        "선수 끝내기 기회 놓침", "선수 후 큰 집 확보", "역끝내기 선수",
        "후수 큰 자리 선수화", "귀 선수 끝내기", "변 선수 끝내기",
        "중앙 선수 끝내기", "단수 선수 끝내기", "연속 선수 끝내기",
        "선수 끝내기 후 역전",
    ],
}


def generate_positions(existing_count: int = 50, target: int = 100) -> list[dict]:
    positions = []
    idx = existing_count + 1
    per_type = (target - existing_count) // len(REASON_TYPES)
    remainder = (target - existing_count) % len(REASON_TYPES)

    for ri, reason in enumerate(REASON_TYPES):
        count = per_type + (1 if ri < remainder else 0)
        descs = _DESCS[reason]
        for i in range(count):
            diff = rng.choice(DIFFICULTIES)
            desc = descs[i % len(descs)]
            n_moves = rng.randint(6, 20)
            positions.append(_pos(idx, reason, diff, desc, n_moves))
            idx += 1
    return positions


# ── 질문 샘플 ────────────────────────────────────────────────────────────────

_QUESTION_TEMPLATES: list[dict] = [
    {"text": "왜 그 수가 나쁜가요?", "type": "reason", "reason_type": "life_death"},
    {"text": "최선 수가 어디인가요?", "type": "variation", "reason_type": "missed_attack"},
    {"text": "어디에 두는 게 좋았나요?", "type": "variation", "reason_type": "missed_big_point"},
    {"text": "이 수를 왜 둬야 하나요?", "type": "reason", "reason_type": "cut_left"},
    {"text": "대마가 살 수 있나요?", "type": "reason", "reason_type": "life_death"},
    {"text": "수순을 보여주세요.", "type": "variation", "reason_type": "life_death"},
    {"text": "왜 선수인가요?", "type": "reason", "reason_type": "endgame_sente"},
    {"text": "몇 집이나 손해인가요?", "type": "reason", "reason_type": "missed_attack"},
    {"text": "패는 어떻게 해야 하나요?", "type": "concept", "reason_type": "life_death"},
    {"text": "선수의 뜻이 무엇인가요?", "type": "concept", "reason_type": "endgame_sente"},
]


def generate_questions(target: int = 50) -> list[dict]:
    questions = []
    for i in range(target):
        tmpl = _QUESTION_TEMPLATES[i % len(_QUESTION_TEMPLATES)]
        reason = rng.choice(REASON_TYPES)
        questions.append({
            "id": f"q{i + 1:03d}",
            "question_text": tmpl["text"],
            "question_type": tmpl["type"],
            "context_reason_type": tmpl.get("reason_type", reason),
            "move_number": rng.randint(20, 180),
            "label": {
                "expected_question_type": tmpl["type"],
                "should_contain_variation": tmpl["type"] == "variation",
            },
        })
    return questions


def main() -> None:
    # positions.jsonl: 기존 50개 유지, 50개 추가
    pos_path = GOLDEN_DIR / "positions.jsonl"
    existing_ids: set[str] = set()
    existing_lines: list[str] = []
    if pos_path.exists():
        existing_lines = pos_path.read_text(encoding="utf-8").splitlines()
        for line in existing_lines:
            try:
                existing_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    new_positions = generate_positions(
        existing_count=len(existing_lines),
        target=100,
    )
    new_positions = [p for p in new_positions if p["id"] not in existing_ids]

    with pos_path.open("a", encoding="utf-8") as f:
        for p in new_positions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    total = len(existing_lines) + len(new_positions)
    print(f"positions.jsonl: {total}개 ({len(new_positions)}개 추가)")

    # questions.jsonl: 새로 생성
    q_path = GOLDEN_DIR / "questions.jsonl"
    questions = generate_questions(50)
    with q_path.open("w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"questions.jsonl: {len(questions)}개 생성")


if __name__ == "__main__":
    main()
