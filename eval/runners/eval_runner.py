"""
`make eval` 진입점.

채점 항목:
  1. classifier: positions.jsonl 각 국면에 대해 분류기 결과 vs 라벨 일치율
  2. question_type: questions.jsonl 각 질문에 대해 분류 결과 vs 라벨 일치율
  3. utterance (선택): ANTHROPIC_API_KEY 있으면 utterance 생성 후 샘플 확인
출력: eval/golden/report_<timestamp>.json
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 패키지 경로 추가
ROOT = Path(__file__).parent.parent.parent
for pkg in ("packages/analysis", "packages/go-core", "packages/verifier", "packages/engine-pool"):
    sys.path.insert(0, str(ROOT / pkg))

from analysis.analyzer import PositionFeatures
from analysis.classifier import classify, ReasonType

GOLDEN_DIR = ROOT / "eval" / "golden"
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
RUN_LIVE = os.getenv("EVAL_LIVE", "false").lower() == "true"


# ── 1. Classifier 정확도 ──────────────────────────────────────────────────────

def eval_classifier(positions: list[dict]) -> dict:
    total = correct = skipped = 0
    errors: list[dict] = []

    for pos in positions:
        label = pos.get("label", {})
        expected = label.get("reason_type")
        if not expected:
            skipped += 1
            continue

        score_drop = label.get("score_drop", 5.0)
        winrate_drop = label.get("winrate_drop", 0.08)
        move_number = len(pos.get("moves", [])) + 20

        current = PositionFeatures(
            turn_number=move_number,
            current_player="B",
            score_lead=-score_drop,
            winrate=0.5 - winrate_drop,
        )
        previous = PositionFeatures(
            turn_number=move_number - 1,
            current_player="W",
            score_lead=0.0,
            winrate=0.5,
        )

        predicted = classify(current, previous)
        total += 1
        if predicted is not None and predicted.value == expected:
            correct += 1
        else:
            errors.append({
                "id": pos["id"],
                "expected": expected,
                "predicted": predicted.value if predicted else None,
            })

    accuracy = correct / total if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "skipped": skipped,
        "accuracy": round(accuracy, 4),
        "errors": errors[:10],  # 최대 10개만 리포트
    }


# ── 2. 질문 유형 분류 정확도 ──────────────────────────────────────────────────

def _classify_question_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("수순", "어디", "몇", "착수", "최선", "어느")):
        return "variation"
    if any(k in t for k in ("왜", "이유", "때문", "근거", "어째서")):
        return "reason"
    if any(k in t for k in ("뜻", "규칙", "용어", "무슨", "개념", "정의")):
        return "concept"
    return "other"


def eval_question_classifier(questions: list[dict]) -> dict:
    total = correct = 0
    errors: list[dict] = []

    for q in questions:
        expected = q.get("label", {}).get("expected_question_type", q.get("question_type"))
        if not expected:
            continue
        predicted = _classify_question_type(q["question_text"])
        total += 1
        if predicted == expected:
            correct += 1
        else:
            errors.append({
                "id": q["id"],
                "text": q["question_text"],
                "expected": expected,
                "predicted": predicted,
            })

    accuracy = correct / total if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "errors": errors[:10],
    }


# ── 3. 라이브 utterance 검사 (선택) ──────────────────────────────────────────

async def eval_live_utterance(positions: list[dict], sample_n: int = 20) -> dict:
    import httpx
    sample = positions[:sample_n]
    results = []
    t0 = time.perf_counter()

    async with httpx.AsyncClient(base_url=AI_SERVICE_URL, timeout=30.0) as client:
        for pos in sample:
            label = pos.get("label", {})
            reason_type = label.get("reason_type", "life_death")
            score_drop = label.get("score_drop", 5.0)
            board = [[0] * 19 for _ in range(19)]

            try:
                resp = await client.post("/api/coach/push", json={
                    "game_id": pos["id"],
                    "board_state": board,
                    "reason_type": reason_type,
                    "score_drop": score_drop,
                    "move_number": 40,
                    "color_that_moved": "B",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    results.append({
                        "id": pos["id"],
                        "utterance": data["utterance"],
                        "verified": data["verified"],
                        "hints_count": len(data["hints"]),
                        "cost": data.get("cost", {}),
                        "ok": True,
                    })
                else:
                    results.append({"id": pos["id"], "ok": False, "status": resp.status_code})
            except Exception as e:
                results.append({"id": pos["id"], "ok": False, "error": str(e)})

    elapsed = time.perf_counter() - t0
    ok_count = sum(1 for r in results if r.get("ok"))
    verified_count = sum(1 for r in results if r.get("verified"))
    total_input_tokens = sum(
        r.get("cost", {}).get("utterance_input_tokens", 0) for r in results
    )
    total_output_tokens = sum(
        r.get("cost", {}).get("utterance_output_tokens", 0) for r in results
    )

    return {
        "sample_size": sample_n,
        "ok_count": ok_count,
        "verified_count": verified_count,
        "elapsed_s": round(elapsed, 2),
        "avg_ms_per_position": round(elapsed * 1000 / sample_n, 1) if sample_n else 0,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "samples": results[:5],
    }


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    positions_path = GOLDEN_DIR / "positions.jsonl"
    questions_path = GOLDEN_DIR / "questions.jsonl"

    positions = [json.loads(l) for l in positions_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    questions = [json.loads(l) for l in questions_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"positions: {len(positions)}개  questions: {len(questions)}개")

    report: dict = {
        "timestamp": datetime.now().isoformat(),
        "positions_count": len(positions),
        "questions_count": len(questions),
    }

    # 1. Classifier
    print("Classifier 평가 중...")
    cls_result = eval_classifier(positions)
    report["classifier"] = cls_result
    print(f"  정확도: {cls_result['accuracy']:.1%}  ({cls_result['correct']}/{cls_result['total']})")

    # 2. 질문 유형 분류
    print("질문 유형 분류 평가 중...")
    q_result = eval_question_classifier(questions)
    report["question_classifier"] = q_result
    print(f"  정확도: {q_result['accuracy']:.1%}  ({q_result['correct']}/{q_result['total']})")

    # 3. 라이브 utterance (선택)
    if RUN_LIVE:
        print("라이브 utterance 평가 중 (AI 서비스 필요)...")
        live_result = await eval_live_utterance(positions, sample_n=20)
        report["live_utterance"] = live_result
        print(f"  성공: {live_result['ok_count']}/20  검증됨: {live_result['verified_count']}/20")
        print(f"  평균 응답시간: {live_result['avg_ms_per_position']}ms")
    else:
        print("라이브 평가 건너뜀 (EVAL_LIVE=true 로 활성화)")

    # 결과 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = GOLDEN_DIR / f"report_{ts}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n리포트 저장: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
