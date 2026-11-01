from __future__ import annotations

"""
F3  흐름: coach_push → intent_parse → variation_generate → utterance → verify → result
F3-B흐름: user_question → classify_question → handle_per_type → result
"""

import os
import re
import time
from typing import Any, Literal, TypedDict

from langgraph.graph import StateGraph, END

from go_core.coordinate import Coordinate
from verifier.schema import CoachClaim, VariationMove
from verifier.verifier import verify as verify_claim, TEMPLATE_FALLBACKS

from .hints import build_hints, HintStep
from .tools import get_board_facts, play_variation

_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# 질문 응답용 KataGo 분석 깊이 — AI 착수보다 깊게 두어야 좌표·승률 품질 확보.
# CPU(Eigen) 환경에선 32가 ~5-10초로 timeout 안전한 상한.
_QUESTION_VISITS = int(os.getenv("KATAGO_QUESTION_VISITS", "32"))
# 학생 지목 좌표 2차 평가는 가볍게 — 1위 대비 수치 차이만 보여주면 되므로 상위 수준의 정확도 불필요.
_USER_MOVE_VISITS = int(os.getenv("KATAGO_USER_MOVE_VISITS", "16"))

_GTP_COLS = list("ABCDEFGHJKLMNOPQRST")


# ── 공유 상태 정의 ────────────────────────────────────────────────────────────

class CoachState(TypedDict):
    # 입력
    board_state: list[list[int]]
    reason_type: str
    score_drop: float
    move_number: int
    color_that_moved: str          # "B" | "W"
    best_move_korean: str

    # 중간 상태
    intent: str                    # 사범이 말하려는 핵심
    variation_moves: list[dict]    # play_variation 결과
    utterance_text: str            # 통합 LLM 호출에서 함께 생성된 발화. utterance 노드가 CoachClaim 조립에 사용.
    board_facts: dict

    # 출력
    claim: CoachClaim | None
    hints: list[HintStep]
    cost: dict[str, Any]           # token / time 측정


class QuestionState(TypedDict):
    board_state: list[list[int]]
    move_number: int
    question_text: str
    color_that_moved: str
    move_history: list[tuple[str, str]]  # [("B","D4"), ...] 수순 전체
    conversation_history: list[dict]    # [{role, text, move_number}] 최대 10턴

    question_type: str             # "variation" | "reason" | "concept" | "other"
    answer_text: str
    variation_moves: list[dict]
    cost: dict[str, Any]


# ── F3 노드 ───────────────────────────────────────────────────────────────────

def _node_intent_parse(state: CoachState) -> CoachState:
    """이유 유형 → 사범의 의도(한 문장) 결정."""
    _INTENTS = {
        "life_death": "큰 그룹이 단수에 걸렸습니다. 생사를 확인하세요.",
        "cut_left": "돌이 끊겨 약한 그룹이 생겼습니다.",
        "missed_attack": "약한 상대 돌을 공격할 기회를 놓쳤습니다.",
        "missed_big_point": "국지적으로 큰 자리를 선점하지 못했습니다.",
        "endgame_sente": "선수 끝내기 기회를 놓쳤습니다.",
    }
    intent = _INTENTS.get(state["reason_type"], "실수가 있었습니다.")
    return {**state, "intent": intent}


def _node_board_facts(state: CoachState) -> CoachState:
    """보드 사실 수집 (그룹 단수 여부 등)."""
    facts = get_board_facts(state["board_state"])
    return {**state, "board_facts": facts}


async def _node_variation_generate(state: CoachState) -> CoachState:
    """
    변화 수순 + 사범 발화를 **한 번의 LLM 호출**로 함께 생성한다.
    기존엔 variation / utterance 노드가 LLM을 각각 1회씩 직렬 호출해 지연이 2배였다.
    """
    t0 = time.perf_counter()
    input_tokens, output_tokens = 0, 0

    if _GEMINI_KEY:
        moves, utterance, in_tok, out_tok = await _llm_generate_variation_and_utterance(state)
        input_tokens += in_tok
        output_tokens += out_tok
        # LLM이 발화를 못 뽑으면 템플릿으로 폴백 (검증기가 걸러주긴 하지만 안전망).
        if not utterance:
            utterance = _template_utterance(state)
    else:
        moves = _template_variation(state)
        utterance = _template_utterance(state)

    elapsed = time.perf_counter() - t0
    prev_cost = state.get("cost") or {}
    # 호환성 유지: 기존 cost 키 그대로 두되 utterance_* 는 0으로 (coach.py의 record_llm이 합산해서 쓰므로 영향 없음).
    cost = {
        **prev_cost,
        "variation_ms": round(elapsed * 1000),
        "variation_input_tokens": input_tokens,
        "variation_output_tokens": output_tokens,
        "utterance_ms": 0,
        "utterance_input_tokens": 0,
        "utterance_output_tokens": 0,
    }
    return {**state, "variation_moves": moves, "utterance_text": utterance, "cost": cost}


def _node_utterance(state: CoachState) -> CoachState:
    """CoachClaim 조립 전용. 발화는 variation_generate에서 이미 생성됨."""
    utterance = state.get("utterance_text") or _template_utterance(state)
    return {**state, "claim": CoachClaim(
        reason_type=state["reason_type"],
        utterance=utterance,
        variation=[
            VariationMove(
                row=m["row"], col=m["col"], color=m["color"], label=m.get("label", "")
            )
            for m in state.get("variation_moves", [])
        ],
        score_drop=state["score_drop"],
    )}


def _node_verify(state: CoachState) -> CoachState:
    """검증기 통과."""
    claim = state["claim"]
    if claim is None:
        return state
    verified = verify_claim(claim, state["board_state"], state["color_that_moved"])
    return {**state, "claim": verified}


def _node_hints(state: CoachState) -> CoachState:
    """단계형 힌트 3단계 생성."""
    hints = build_hints(
        reason_type=state["reason_type"],
        score_drop=state["score_drop"],
        color_that_moved=state["color_that_moved"],
        best_move_korean=state.get("best_move_korean", ""),
        board_facts=state.get("board_facts"),
    )
    return {**state, "hints": hints}


# ── F3-B 노드 ─────────────────────────────────────────────────────────────────

def _node_classify_question(state: QuestionState) -> QuestionState:
    """
    질문 유형 4종 분류.
    variation / reason / concept / other
    """
    text = state["question_text"].lower()
    if any(k in text for k in (
        "수순", "어디", "몇", "착수", "최선", "어느",
        "어디에", "어디다", "어떤 수", "좋은 수", "최선수",
        "두어야", "둬야", "놔야", "어디로", "어느 곳",
    )):
        q_type = "variation"
    elif any(k in text for k in (
        "왜", "이유", "때문", "근거", "어째서",
        "왜요", "왜냐", "어떻게", "어떤 이유", "뭐가 문제",
        "왜 나쁜", "왜 안", "왜 그",
    )):
        q_type = "reason"
    elif any(k in text for k in (
        "뜻", "규칙", "용어", "무슨", "개념", "정의",
        "뭐야", "뭔가요", "무엇인가", "무엇이",
    )):
        q_type = "concept"
    else:
        # 분류 불명확 → reason으로 fallback (사용자 질문 대부분이 '왜/어떻게'에 해당)
        q_type = "reason"
    return {**state, "question_type": q_type}


async def _node_handle_variation_question(state: QuestionState) -> QuestionState:
    """수순 관련 질문 처리."""
    t0 = time.perf_counter()
    input_tokens, output_tokens = 0, 0

    analysis = await _fetch_position_analysis(
        state["board_state"], state["color_that_moved"], state.get("move_history") or [],
        question_text=state.get("question_text", ""),
    )
    moves = _variation_moves_from_analysis(analysis, state["color_that_moved"])

    if _GEMINI_KEY:
        answer, in_tok, out_tok = await _llm_answer_variation(state, analysis)
        input_tokens += in_tok
        output_tokens += out_tok
    else:
        answer = _data_only_variation_answer(analysis, state["color_that_moved"])

    elapsed = time.perf_counter() - t0
    cost = {"answer_ms": round(elapsed * 1000), "answer_input_tokens": input_tokens,
            "answer_output_tokens": output_tokens}
    return {**state, "answer_text": answer, "variation_moves": moves, "cost": cost}


async def _node_handle_reason_question(state: QuestionState) -> QuestionState:
    """이유 관련 질문 처리."""
    t0 = time.perf_counter()
    input_tokens, output_tokens = 0, 0

    analysis = await _fetch_position_analysis(
        state["board_state"], state["color_that_moved"], state.get("move_history") or [],
        question_text=state.get("question_text", ""),
    )

    if _GEMINI_KEY:
        answer, in_tok, out_tok = await _llm_answer_reason(state, analysis)
        input_tokens += in_tok
        output_tokens += out_tok
    else:
        answer = _data_only_reason_answer(analysis, state["color_that_moved"])

    elapsed = time.perf_counter() - t0
    cost = {"answer_ms": round(elapsed * 1000), "answer_input_tokens": input_tokens,
            "answer_output_tokens": output_tokens}
    return {**state, "answer_text": answer, "variation_moves": [], "cost": cost}


def _node_handle_concept_question(state: QuestionState) -> QuestionState:
    """용어/개념 질문 처리 (S8 이후 확장 예정, 현재 간단 응답)."""
    answer = "바둑 용어나 개념은 현재 간단히 답변드립니다. 더 자세한 내용은 기보 해설서를 참고하세요."
    return {**state, "answer_text": answer, "variation_moves": [],
            "cost": {"answer_ms": 0, "answer_input_tokens": 0, "answer_output_tokens": 0}}


def _node_handle_other_question(state: QuestionState) -> QuestionState:
    answer = "질문을 이해하지 못했습니다. 수순, 이유, 또는 용어에 대해 질문해 주세요."
    return {**state, "answer_text": answer, "variation_moves": [],
            "cost": {"answer_ms": 0, "answer_input_tokens": 0, "answer_output_tokens": 0}}


def _route_question(state: QuestionState) -> str:
    return state["question_type"]


# ── 그래프 빌드 ───────────────────────────────────────────────────────────────

def _build_coach_graph() -> Any:
    g = StateGraph(CoachState)
    g.add_node("intent_parse", _node_intent_parse)
    g.add_node("board_facts", _node_board_facts)
    g.add_node("variation_generate", _node_variation_generate)
    g.add_node("utterance", _node_utterance)
    g.add_node("verify", _node_verify)
    g.add_node("hints", _node_hints)

    g.set_entry_point("intent_parse")
    g.add_edge("intent_parse", "board_facts")
    g.add_edge("board_facts", "variation_generate")
    g.add_edge("variation_generate", "utterance")
    g.add_edge("utterance", "verify")
    g.add_edge("verify", "hints")
    g.add_edge("hints", END)

    return g.compile()


def _build_question_graph() -> Any:
    g = StateGraph(QuestionState)
    g.add_node("classify_question", _node_classify_question)
    g.add_node("variation", _node_handle_variation_question)
    g.add_node("reason", _node_handle_reason_question)
    g.add_node("concept", _node_handle_concept_question)
    g.add_node("other", _node_handle_other_question)

    g.set_entry_point("classify_question")
    g.add_conditional_edges(
        "classify_question",
        _route_question,
        {"variation": "variation", "reason": "reason",
         "concept": "concept", "other": "other"},
    )
    for node in ("variation", "reason", "concept", "other"):
        g.add_edge(node, END)

    return g.compile()


_coach_graph = _build_coach_graph()
_question_graph = _build_question_graph()


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────

async def run_coach_push(
    board_state: list[list[int]],
    reason_type: str,
    score_drop: float,
    move_number: int,
    color_that_moved: str,
    best_move_korean: str = "",
) -> dict[str, Any]:
    """F3 흐름 실행 → claim + hints + cost 반환."""
    initial: CoachState = {
        "board_state": board_state,
        "reason_type": reason_type,
        "score_drop": score_drop,
        "move_number": move_number,
        "color_that_moved": color_that_moved,
        "best_move_korean": best_move_korean,
        "intent": "",
        "variation_moves": [],
        "utterance_text": "",
        "board_facts": {},
        "claim": None,
        "hints": [],
        "cost": {},
    }
    result: CoachState = await _coach_graph.ainvoke(initial)
    claim = result["claim"]
    cost = dict(result["cost"])
    cost["model"] = _GEMINI_MODEL if _GEMINI_KEY else ""
    return {
        "utterance": claim.utterance if claim else "",
        "verified": claim.verified if claim else False,
        "verification_error": claim.verification_error if claim else "",
        "variation": [
            {"row": m.row, "col": m.col, "color": m.color, "label": m.label}
            for m in (claim.variation if claim else [])
        ],
        "hints": [
            {"step": h.step, "label": h.label, "text": h.text}
            for h in result["hints"]
        ],
        "cost": cost,
    }


async def run_coach_question(
    board_state: list[list[int]],
    move_number: int,
    question_text: str,
    color_that_moved: str = "B",
    move_history: list[tuple[str, str]] | None = None,
    conversation_history: list[dict] | None = None,
) -> dict[str, Any]:
    """F3-B 흐름 실행 → answer + variation + cost 반환."""
    initial: QuestionState = {
        "board_state": board_state,
        "move_number": move_number,
        "question_text": question_text,
        "color_that_moved": color_that_moved,
        "move_history": list(move_history or []),
        "conversation_history": list(conversation_history or []),
        "question_type": "",
        "answer_text": "",
        "variation_moves": [],
        "cost": {},
    }
    result: QuestionState = await _question_graph.ainvoke(initial)
    cost = dict(result["cost"])
    cost["model"] = _GEMINI_MODEL if _GEMINI_KEY else ""
    return {
        "question_type": result["question_type"],
        "answer": result["answer_text"],
        "variation": result["variation_moves"],
        "cost": cost,
    }


# ── LLM 헬퍼 (GEMINI_API_KEY 있을 때, Gemini OpenAI 호환 API) ────────────────

def _llm_client():
    from openai import OpenAI
    return OpenAI(api_key=_GEMINI_KEY, base_url=_GEMINI_BASE_URL)


def _llm_chat(prompt: str, max_tokens: int = 200) -> tuple[str, int, int]:
    """Gemini(OpenAI 호환) 호출 → (text, input_tokens, output_tokens).
    동기 함수 — asyncio.to_thread 로 감싸서 호출해야 이벤트 루프 블로킹 없음."""
    client = _llm_client()
    resp = client.chat.completions.create(
        model=_GEMINI_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        timeout=15,
    )
    text = resp.choices[0].message.content or ""
    return text.strip(), resp.usage.prompt_tokens, resp.usage.completion_tokens


async def _llm_chat_async(prompt: str, max_tokens: int = 200) -> tuple[str, int, int]:
    """_llm_chat을 스레드에서 실행해 이벤트 루프를 블로킹하지 않는다."""
    import asyncio
    return await asyncio.to_thread(_llm_chat, prompt, max_tokens)


async def _llm_generate_variation_and_utterance(
    state: CoachState,
) -> tuple[list[dict], str, int, int]:
    """최선 수순 + 사범 발화를 **한 번의 Gemini 호출**로 함께 생성.

    기존엔 variation / utterance를 각각 호출해 RTT·토큰이 2배였다. 통합 프롬프트로
    LLM이 변화도를 떠올리면서 그 근거를 발화에 녹여 쓰도록 유도한다 — 발화가 수순과
    모순될 가능성도 줄어든다.
    """
    try:
        import json as _json
        color_name = "흑" if state["color_that_moved"] == "B" else "백"
        board_info = state.get("board_facts", {})
        atari_groups = [g for g in board_info.get("groups", []) if g["in_atari"]]
        atari_info = f" 단수 그룹 {len(atari_groups)}개 있음." if atari_groups else ""
        prompt = (
            f"바둑 분석. {color_name}이 방금 착수했고 {state['score_drop']:.1f}집 손실. "
            f"수 번호: {state['move_number']}.\n"
            f"이유: {state['reason_type']}. 의도: {state['intent']}.{atari_info}\n\n"
            "변화 수순(최대 3수)과 사범 발화를 **하나의 JSON 객체**로 답하세요:\n"
            '{"variation":[{"row":int,"col":int,"color":"B"|"W"},...],'
            '"utterance":"한국어 2문장 이내의 간결한 설명"}\n\n'
            "제약:\n"
            "- 모호한 표현(두터움·맛·기세) 금지. 구체적 근거만.\n"
            "- 발화는 variation에 담긴 수순을 전제로 왜 손해인지 설명.\n"
            "- JSON만. 다른 말 없이."
        )
        # max_tokens: variation 100 + utterance 150 여유 포함 → 300.
        text, in_tok, out_tok = await _llm_chat_async(prompt, max_tokens=300)
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        data = _json.loads(text)
        variation = data.get("variation") or []
        utterance = (data.get("utterance") or "").strip()
        # variation 형식 검증(필수 키 누락 시 폴백).
        if not isinstance(variation, list) or any(
            not isinstance(m, dict) or {"row", "col", "color"} - m.keys() for m in variation
        ):
            variation = []
        return variation, utterance, in_tok, out_tok
    except Exception:
        return [], "", 0, 0


def _template_variation(state: CoachState) -> list[dict]:
    return []


def _template_utterance(state: CoachState) -> str:
    color_name = "흑" if state["color_that_moved"] == "B" else "백"
    template = TEMPLATE_FALLBACKS.get(state["reason_type"], "{color}이 실수를 했습니다 ({drop:.1f}집).")
    return template.format(color=color_name, drop=state["score_drop"])


def _resolve_colors(state: QuestionState, analysis: dict) -> tuple[str, str]:
    """KataGo 수순 기반 추론(analysis['to_move'])을 UI 입력보다 우선한다.
    반환: (color_name=방금 둔 색 한글, next_color=다음 둘 색 한글)
    """
    to_move = analysis.get("to_move")
    if to_move in ("B", "W"):
        if to_move == "B":
            return "백", "흑"
        return "흑", "백"
    # 분석 실패 시 UI 값 폴백
    if state["color_that_moved"] == "B":
        return "흑", "백"
    return "백", "흑"


_COACH_RULES = (
    "엄격한 규칙:\n"
    "1. 좌표와 지점명은 위 분석 블록에 **적힌 그대로** 복사해서 쓰세요. 좌표를 "
    "다른 숫자로 바꾸거나, 분석에 없는 지점명(소목·화점·삼삼 등)을 임의로 붙이지 마세요.\n"
    "1-a. '다음 수' 후보들의 승률·집차는 모두 **{next_color} 기준**입니다. 색을 "
    "섞어 쓰지 마세요 (예: 흑 집차로 환산해 다시 쓰지 말 것).\n"
    "2. 모호한 추상 표현(두터움·맛·기세·흐름·판국·배치) 금지. **분석 블록에 적힌 "
    "승률·집차·PV·단수 그룹·국소 전술 사실**에서 끌어낼 수 있는 사실만 쓰세요. "
    "블록에 없는 사실(돌 사이 거리, 집 크기 추정 등)은 **지어내지 마세요**.\n"
    "3. 학생이 지목한 자리에 대한 국소 전술 블록이 있으면 **반드시 활용**하세요:\n"
    "   - 블록에 '따낸다', '단수로 몰 수 있다', '자충', '활로 N' 같은 사실이 "
    "적혀 있으면 그걸 그대로 서술해 왜 좋은/나쁜 수인지 설명하세요.\n"
    "   - PV가 있으면 '이 자리에 두면 상대가 X로 받아 Y로 전개됩니다' 식으로 "
    "구체적 수순을 인용하세요.\n"
    "   - 승률·집차 숫자로 1위 추천 수 대비 손해/이득 규모를 명시하세요.\n"
    "4. 국소 전술 블록이 '둘 수 없는 자리'로 나오면 그 사실(불법 수)을 먼저 알려 "
    "주세요."
)


async def _llm_answer_variation(
    state: QuestionState, analysis: dict
) -> tuple[str, int, int]:
    try:
        color_name, next_color = _resolve_colors(state, analysis)
        context = _format_analysis_context(analysis, next_color)
        user_gtp = _extract_coord_from_question(state.get("question_text", ""))
        to_move = analysis.get("to_move")
        board_facts = _format_board_facts(state["board_state"], user_gtp, to_move)

        conv_block = _format_conversation_history(state.get("conversation_history") or [])
        prompt = (
            f"당신은 노련한 바둑 사범입니다. {color_name}이 {state['move_number']}수를 두었고, "
            f"지금은 {next_color} 차례입니다.\n"
            f"{context}"
            f"{board_facts}\n"
            f"{conv_block}"
            f"학생 질문: {state['question_text']}\n\n"
            + _COACH_RULES.format(next_color=next_color)
            + "\n\n"
            "답변 포맷:\n"
            "- 학생이 지목한 자리의 평가(또는 1~2개 상위 후보)와 1순위 추천 수의 차이를 수치로 설명\n"
            "- 국소 전술 사실(따냄/단수/활로/자충)이 있으면 반드시 그걸 인용해 "
            "왜 그 수인지/왜 안 좋은지를 서술\n"
            "- PV가 있으면 상대 응수를 수순으로 명시\n"
            "- 이전 대화가 있으면 맥락을 이어받아 답변 (예: '그럼 X 말고 Y는?' 같은 후속 질문 처리)\n"
            "- 3~4문장, 간결하게"
        )
        text, in_tok, out_tok = await _llm_chat_async(prompt, max_tokens=400)
        return text, in_tok, out_tok
    except Exception:
        return _data_only_variation_answer(analysis, state["color_that_moved"]), 0, 0


async def _llm_answer_reason(
    state: QuestionState, analysis: dict
) -> tuple[str, int, int]:
    try:
        color_name, next_color = _resolve_colors(state, analysis)
        context = _format_analysis_context(analysis, next_color)
        user_gtp = _extract_coord_from_question(state.get("question_text", ""))
        to_move = analysis.get("to_move")
        board_facts = _format_board_facts(state["board_state"], user_gtp, to_move)

        conv_block = _format_conversation_history(state.get("conversation_history") or [])
        prompt = (
            f"당신은 노련한 바둑 사범입니다. {color_name}이 {state['move_number']}수를 두었습니다.\n"
            f"{context}"
            f"{board_facts}\n"
            f"{conv_block}"
            f"학생 질문: {state['question_text']}\n\n"
            + _COACH_RULES.format(next_color=next_color)
            + "\n\n"
            "답변 포맷:\n"
            "- 1순위 추천 수와 학생이 지목한 자리(또는 2순위)의 승률·집차 차이로 손실 규모 설명\n"
            "- '왜 손해인지'는 국소 전술 사실(따냄/단수/활로/자충)이나 PV(상대 응수)로 "
            "구체적으로 서술. 두 가지가 모두 있으면 둘 다 활용.\n"
            "- 이전 대화가 있으면 맥락을 이어받아 답변 (예: '그럼 X 말고 Y는?' 같은 후속 질문 처리)\n"
            "- 3~4문장, 간결하게"
        )
        return await _llm_chat_async(prompt, max_tokens=400)
    except Exception:
        return _data_only_reason_answer(analysis, state["color_that_moved"]), 0, 0


# ── 포지션 분석 헬퍼 ───────────────────────────────────────────────────────────

async def _fetch_position_analysis(
    board_state: list[list[int]],
    color_that_moved: str,
    move_history: list[tuple[str, str]] | None = None,
    question_text: str = "",
) -> dict:
    """engine_pool로 현재 포지션을 분석해 상위 수·승률·집수를 반환.

    KataGo cfg는 reportAnalysisWinratesAs=SIDETOMOVE라서 수치는 "둘 차례" 기준으로
    들어온다. 여기서 흑 기준으로 변환해 저장한다 (양수 집차 = 흑 유리).

    move_history가 있으면 moves 수순으로 쿼리한다. initialStones + initialPlayer
    조합은 돌수-차례 불일치를 KataGo가 "흑 pass"로 추정해 집차가 왜곡된다.

    question_text에서 좌표가 추출되고 그 좌표가 top3에 없으면 allowMoves로
    2차 쿼리를 날려 user_move 평가를 얻는다.
    """
    try:
        from engine_pool.pool import get_pool
        from engine_pool.types import AnalysisRequest, Priority

        pool = get_pool()
        to_move = "W" if color_that_moved == "B" else "B"
        if move_history:
            base_moves = list(move_history)
            req = AnalysisRequest(
                board_size=19,
                moves=base_moves,
                board_grid=None,
                initial_player=None,
                priority=Priority.ANALYSIS,
                max_visits=_QUESTION_VISITS,
            )
        else:
            base_moves = []
            req = AnalysisRequest(
                board_size=19,
                moves=[],
                board_grid=board_state,
                initial_player=to_move,
                priority=Priority.ANALYSIS,
                max_visits=_QUESTION_VISITS,
            )
        resp = await pool.analyze(req)

        # 변환 기준은 KataGo 응답의 current_player를 신뢰한다 (수순 기반 쿼리에선
        # KataGo가 수순 끝의 반대편으로 자동 판정하므로, 호출자가 넘긴
        # color_that_moved가 틀려도 수치가 뒤집히지 않음).
        actual_to_move = resp.current_player or to_move

        def _to_black(wr: float, sl: float) -> tuple[float, float]:
            if actual_to_move == "B":
                return wr, sl
            return 1.0 - wr, -sl

        root_wr_b, root_sl_b = _to_black(resp.winrate, resp.score_lead)
        top_moves = [
            {
                "gtp": m.move,
                "coord": _gtp_to_label(m.move),
                **dict(zip(
                    ("winrate_black", "score_lead"),
                    _to_black(m.winrate, m.score_lead),
                )),
                "pv": list(m.pv),
                "order": m.order,
            }
            for m in resp.best_moves[:3]
        ]

        result: dict[str, Any] = {
            "winrate_black": root_wr_b,
            "score_lead": root_sl_b,  # +면 흑 유리
            "top_moves": top_moves,
            # KataGo 수순 기반으로 추론한 '다음 둘 색'. UI color_that_moved가
            # 어긋나도 수치/표현이 뒤틀리지 않도록 하향 소비자에게 전달.
            "to_move": actual_to_move,
        }

        # 2차 쿼리: 학생이 질문에서 지목한 좌표가 있을 때만 그 수를 평가한다.
        # 지목이 없으면 2차 쿼리 자체를 건너뛰어 응답 지연 ~절반 절감.
        user_gtp = _extract_coord_from_question(question_text)
        print(
            f"[USER_MOVE] q={question_text[:60]!r} extracted={user_gtp}",
            flush=True,
        )
        if user_gtp:
            matched = next((m for m in top_moves if m["gtp"] == user_gtp), None)
            if matched:
                # top3 안에 이미 있으면 2차 쿼리 없이 복사.
                result["user_move"] = {
                    "gtp": matched["gtp"],
                    "coord": matched["coord"],
                    "winrate_black": matched["winrate_black"],
                    "score_lead": matched["score_lead"],
                    "pv": matched["pv"],
                    "in_top": True,
                }
                print(f"[USER_MOVE] {user_gtp} is in top3, skip 2nd query", flush=True)
            else:
                try:
                    # 2차 쿼리는 1차 대비 가볍게 — 상위 랭킹을 다시 계산할 필요 없이
                    # 지목 좌표 하나의 승률·집차 수치만 뽑으면 되므로.
                    req2 = AnalysisRequest(
                        board_size=19,
                        moves=list(base_moves),
                        board_grid=None if base_moves else board_state,
                        initial_player=None if base_moves else to_move,
                        allow_moves=[user_gtp],
                        priority=Priority.ANALYSIS,
                        max_visits=_USER_MOVE_VISITS,
                    )
                    resp2 = await pool.analyze(req2)
                    user_mi = next(
                        (m for m in resp2.best_moves if m.move == user_gtp),
                        None,
                    )
                    if user_mi:
                        user_wr_b, user_sl_b = _to_black(
                            user_mi.winrate, user_mi.score_lead
                        )
                        result["user_move"] = {
                            "gtp": user_mi.move,
                            "coord": _gtp_to_label(user_mi.move),
                            "winrate_black": user_wr_b,
                            "score_lead": user_sl_b,
                            "pv": list(user_mi.pv),
                            "in_top": False,
                        }
                        print(
                            f"[USER_MOVE] 2nd query OK: wr={user_wr_b:.3f} sl={user_sl_b:+.2f}",
                            flush=True,
                        )
                    else:
                        print(
                            f"[USER_MOVE] 2nd query returned no match for {user_gtp}; "
                            f"moves_returned={[m.move for m in resp2.best_moves]}",
                            flush=True,
                        )
                except Exception as e:
                    print(f"[USER_MOVE] 2nd query failed: {e!r}", flush=True)

        return result
    except Exception:
        return {}


# 좌하 귀 기준 1-based (x, y) → 지점명. 네 귀는 대칭으로 변환해 매칭한다.
_CORNER_POINTS = {
    (4, 4): "화점",
    (3, 3): "삼삼",
    (3, 4): "소목", (4, 3): "소목",
    (3, 5): "외목", (5, 3): "외목",
    (4, 5): "고목", (5, 4): "고목",
    (3, 6): "대고목", (6, 3): "대고목",
}
_SIDE_POINTS = {
    (10, 4): "하변 화점",
    (10, 16): "상변 화점",
    (4, 10): "좌변 화점",
    (16, 10): "우변 화점",
}


def _point_name(x: int, y: int) -> str:
    """(x, y) 1-based → '우상 소목' 같은 지점명. 특수 지점 아니면 ''."""
    if (x, y) == (10, 10):
        return "천원"
    for quadrant, (lx, ly) in (
        ("좌하", (x, y)),
        ("우하", (20 - x, y)),
        ("좌상", (x, 20 - y)),
        ("우상", (20 - x, 20 - y)),
    ):
        if (lx, ly) in _CORNER_POINTS:
            return f"{quadrant} {_CORNER_POINTS[(lx, ly)]}"
    if (x, y) in _SIDE_POINTS:
        return _SIDE_POINTS[(x, y)]
    return ""


def _gtp_to_label(gtp: str) -> str:
    """GTP → '16-4' 또는 '16-4(우상 화점)' 식 숫자-숫자 + 지점명."""
    if not gtp or gtp.upper() in ("PASS", ""):
        return "패스"
    try:
        col_char = gtp[0].upper()
        row_num = int(gtp[1:])
        col = _GTP_COLS.index(col_char)
        x = col + 1
        y = row_num
        base = f"{x}-{y}"
        name = _point_name(x, y)
        return f"{base}({name})" if name else base
    except Exception:
        return gtp


def _xy_to_gtp(x: int, y: int, board_size: int = 19) -> str | None:
    """1-based (x, y) 내부 표시 좌표 → GTP. 범위 밖이면 None."""
    if not (1 <= x <= board_size and 1 <= y <= board_size):
        return None
    col = x - 1
    if col >= len(_GTP_COLS):
        return None
    return f"{_GTP_COLS[col]}{y}"


# "15-12", "15−12", "15—12" 등 x-y 포맷. 공백 허용.
# \b 대신 (?<!\d)/(?!\d)로 숫자 경계만 확인한다 — 한글 조사("15-12는")는
# 유니코드 word character라 \b가 매칭 안 되는 버그 회피.
_XY_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[-−—]\s*(\d{1,2})(?!\d)")
# "P12", "R 3" 등 GTP 포맷 (단독으로 서 있을 때만, I 제외).
_GTP_PATTERN = re.compile(r"(?<![A-Za-z])([A-HJ-Ta-hj-t])\s*(\d{1,2})(?!\d)")


def _extract_coord_from_question(text: str, board_size: int = 19) -> str | None:
    """질문 텍스트에서 좌표를 뽑아 GTP로 반환. 추출 실패 시 None."""
    if not text:
        return None
    m = _XY_PATTERN.search(text)
    if m:
        x, y = int(m.group(1)), int(m.group(2))
        gtp = _xy_to_gtp(x, y, board_size)
        if gtp:
            return gtp
    m = _GTP_PATTERN.search(text)
    if m:
        col_char = m.group(1).upper()
        row_num = int(m.group(2))
        if col_char in _GTP_COLS and 1 <= row_num <= board_size:
            return f"{col_char}{row_num}"
    return None


def _rowcol_to_gtp(row: int, col: int) -> str:
    """0-indexed (row, col) → GTP ('C3' 등). 범위 밖이면 빈 문자열."""
    if not (0 <= col < len(_GTP_COLS) and 0 <= row < 19):
        return ""
    return f"{_GTP_COLS[col]}{19 - row}"


def _local_tactical_facts(
    board_state: list[list[int]], user_gtp: str, to_move: str
) -> dict | None:
    """학생이 지목한 자리에 to_move 색이 두는 경우의 국소 전술 사실.

    모호한 좌표 거리 대신 실제 수를 시뮬레이션해 **따냄·자신 활로·자충·
    상대 그룹 단수 유도** 같은 바둑 사실을 뽑는다.
    """
    from go_core.board import Board, Color

    rc = _gtp_to_rowcol(user_gtp)
    if not rc:
        return None
    row, col = rc

    board = Board()
    for r, srow in enumerate(board_state):
        for c, v in enumerate(srow):
            if v == 1:
                board._grid[r][c] = Color.BLACK
            elif v == 2:
                board._grid[r][c] = Color.WHITE

    color = Color.BLACK if to_move == "B" else Color.WHITE
    opp = color.opponent()

    sim = board.copy()
    result = sim.place(row, col, color)
    if not result.ok:
        return {"legal": False, "error": result.error}

    my_group = sim._get_group(row, col)
    my_libs = sim._liberties(my_group)
    captured = list(result.captured)

    # 돌 놓은 뒤의 보드에서 인접 상대 그룹 상태를 조사한다.
    opp_adj_groups: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for nr, nc in sim._neighbors(row, col):
        if sim._grid[nr][nc] == opp and (nr, nc) not in seen:
            g = sim._get_group(nr, nc)
            seen.update(g)
            libs = sim._liberties(g)
            sample = min(g)
            opp_adj_groups.append({
                "size": len(g),
                "liberties": len(libs),
                "sample_gtp": _rowcol_to_gtp(sample[0], sample[1]),
            })

    cap_sample = min(captured) if captured else None
    return {
        "legal": True,
        "my_liberties": len(my_libs),
        "my_group_size": len(my_group),
        "self_atari": len(my_libs) == 1 and not captured,
        "captures": len(captured),
        "capture_sample_gtp": _rowcol_to_gtp(*cap_sample) if cap_sample else "",
        "adjacent_opponent_groups": opp_adj_groups,
    }


def _format_local_tactical(facts: dict, user_gtp: str) -> str:
    coord = _gtp_to_label(user_gtp)
    if not facts.get("legal"):
        return f"학생이 지목한 자리({coord})는 둘 수 없습니다 ({facts.get('error')})."
    parts = [f"학생이 지목한 자리({coord})에 두면:"]
    if facts["captures"]:
        sample = _gtp_to_label(facts.get("capture_sample_gtp", ""))
        parts.append(
            f"  - 상대 돌 {facts['captures']}점을 따낸다"
            + (f" (예: {sample})" if sample and sample != "패스" else "")
        )
    atari_opp = [g for g in facts["adjacent_opponent_groups"] if g["liberties"] == 1]
    if atari_opp:
        samples = ", ".join(
            f"{_gtp_to_label(g['sample_gtp'])} 그룹({g['size']}점)"
            for g in atari_opp
            if g.get("sample_gtp")
        )
        if samples:
            parts.append(f"  - 인접한 상대 그룹을 단수로 몰 수 있다: {samples}")
    other_opp = [g for g in facts["adjacent_opponent_groups"] if g["liberties"] >= 2]
    if other_opp:
        samples = ", ".join(
            f"{_gtp_to_label(g['sample_gtp'])} 그룹({g['size']}점, 활로 {g['liberties']})"
            for g in other_opp
            if g.get("sample_gtp")
        )
        if samples:
            parts.append(f"  - 인접한 상대 그룹(아직 여유 있음): {samples}")
    if facts["self_atari"]:
        parts.append("  - 놓은 돌이 즉시 단수(활로 1)")
    else:
        parts.append(
            f"  - 놓은 돌 그룹: {facts['my_group_size']}점, 활로 {facts['my_liberties']}"
        )
    return "\n".join(parts)


def _gtp_to_rowcol(gtp: str) -> tuple[int, int] | None:
    if not gtp or gtp.upper() in ("PASS", ""):
        return None
    try:
        col_char = gtp[0].upper()
        row_num = int(gtp[1:])
        col = _GTP_COLS.index(col_char)
        row = 19 - row_num
        if 0 <= row < 19 and 0 <= col < 19:
            return row, col
    except Exception:
        return None
    return None


def _variation_moves_from_analysis(
    analysis: dict, color_that_moved: str
) -> list[dict]:
    """UI가 바둑판에 그릴 수 있도록 상위 수를 (row,col,color) 포맷으로 변환."""
    next_color = "W" if color_that_moved == "B" else "B"
    moves: list[dict] = []
    for i, m in enumerate(analysis.get("top_moves", [])[:1], start=1):
        rc = _gtp_to_rowcol(m.get("gtp", ""))
        if rc:
            moves.append({
                "row": rc[0], "col": rc[1], "color": next_color, "label": str(i),
            })
    return moves


def _format_pv(pv: list[str], max_moves: int = 3) -> str:
    """PV 목록을 '응수: Q3 → R4' 형식으로 포맷. 비어있으면 빈 문자열."""
    if not pv:
        return ""
    labels = [_gtp_to_label(m) for m in pv[1:1 + max_moves] if m]
    if not labels:
        return ""
    return " 응수: " + " → ".join(labels)


def _format_analysis_context(analysis: dict, next_color: str) -> str:
    """모든 '다음 수 후보'의 수치는 next_color(다음 둘 색) 기준으로 통일한다.
    - 승률: 그 수를 둔 뒤 next_color가 이길 확률
    - 집차: 양수면 next_color 유리, 음수면 상대 유리
    현재 포지션 블록만 흑/백 둘 다 표시한다 (관측 편의).
    """
    if not analysis:
        return ""
    wr_b = analysis.get("winrate_black", 0.5)
    sl_b = analysis.get("score_lead", 0.0)
    top = analysis.get("top_moves", [])
    user_move = analysis.get("user_move")
    sign = 1 if next_color == "흑" else -1  # 흑 기준 → next_color 기준 변환 부호

    if sl_b >= 0:
        score_str = f"흑 {sl_b:+.1f}집 우세"
    else:
        score_str = f"백 {abs(sl_b):+.1f}집 우세"
    lines = [
        f"현재 승률: 흑 {wr_b*100:.1f}% / 백 {(1-wr_b)*100:.1f}%, 집차: {score_str}",
        f"(아래 '다음 수' 후보의 승률·집차는 모두 {next_color} 기준입니다.)",
    ]
    if top:
        lines.append(f"{next_color} 다음 수 상위 후보:")
        for i, m in enumerate(top, 1):
            wr_nc = m["winrate_black"] if next_color == "흑" else 1.0 - m["winrate_black"]
            sl_nc = sign * m["score_lead"]
            pv_str = _format_pv(m.get("pv", []))
            lines.append(
                f"  {i}. {m['coord']} — {next_color} 승률 {wr_nc*100:.1f}%, "
                f"{next_color} 집차 {sl_nc:+.1f}.{pv_str}"
            )
    if user_move:
        wr_nc = (
            user_move["winrate_black"] if next_color == "흑"
            else 1.0 - user_move["winrate_black"]
        )
        sl_nc = sign * user_move["score_lead"]
        top_sl_nc = sign * top[0]["score_lead"] if top else sl_nc
        diff = sl_nc - top_sl_nc  # next_color 기준, 음수면 1위 대비 손해
        in_top_note = " (상위 후보에 포함됨)" if user_move.get("in_top") else ""
        pv_str = _format_pv(user_move.get("pv", []))
        lines.append(
            f"학생이 지목한 자리{in_top_note}: {user_move['coord']} — "
            f"{next_color} 승률 {wr_nc*100:.1f}%, {next_color} 집차 {sl_nc:+.1f} "
            f"(1위 대비 {next_color} {diff:+.1f}집 차이, 음수면 손해).{pv_str}"
        )
    return "\n".join(lines) + "\n"


def _format_board_facts(
    board_state: list[list[int]],
    user_gtp: str | None = None,
    to_move: str | None = None,
) -> str:
    """국소 전술 사실 블록.

    - 현재 단수 그룹: 좌표·색·크기까지 명시 (단순 개수가 아니라 LLM 이 지목 가능하게)
    - 학생 좌표가 있으면 그 자리에 두는 수를 **시뮬레이션** 해서 따냄/활로/자충/
      상대 그룹 단수 유도 같은 바둑 사실을 뽑는다. 좌표 거리 같은 모호한 수치는
      제공하지 않는다 (LLM 이 공허한 서술에 의존하는 걸 방지).
    """
    facts = get_board_facts(board_state)
    atari_groups = [g for g in facts.get("groups", []) if g["in_atari"]]
    lines: list[str] = []
    if atari_groups:
        samples: list[str] = []
        for g in atari_groups[:3]:
            if not g["coords"]:
                continue
            r, c = g["coords"][0]
            gtp = _rowcol_to_gtp(r, c)
            if not gtp:
                continue
            color_ko = "흑" if g["color"] == "B" else "백"
            samples.append(f"{_gtp_to_label(gtp)}({color_ko} {g['size']}점)")
        if samples:
            overflow = (
                f" 외 {len(atari_groups) - len(samples)}개"
                if len(atari_groups) > len(samples) else ""
            )
            lines.append(
                "현재 단수에 걸린 그룹: " + ", ".join(samples) + overflow
            )
        else:
            lines.append(f"현재 단수에 걸린 그룹: {len(atari_groups)}개")
    if user_gtp and to_move in ("B", "W"):
        local = _local_tactical_facts(board_state, user_gtp, to_move)
        if local:
            lines.append(_format_local_tactical(local, user_gtp))
    return ("\n".join(lines) + "\n") if lines else ""


def _format_conversation_history(history: list[dict]) -> str:
    """이전 대화 블록을 프롬프트용 문자열로 변환. 비어있으면 빈 문자열 반환."""
    if not history:
        return ""
    lines = ["이전 대화:"]
    cur_move: int | None = None
    for turn in history:
        move_num = turn.get("move_number", 0)
        if move_num != cur_move:
            lines.append(f"[{move_num}수 시점]")
            cur_move = move_num
        role = "학생" if turn.get("role") == "user" else "사범"
        lines.append(f"{role}: {turn.get('text', '')}")
    return "\n".join(lines) + "\n\n"


def _data_only_variation_answer(analysis: dict, color_that_moved: str) -> str:
    """LLM 없이 KataGo 분석 데이터만으로 수순 답변 조립. 수치는 next_color 기준."""
    top = analysis.get("top_moves", [])
    if not top:
        return "지금은 분석할 수 있는 유의미한 수가 없습니다. 조금 더 두신 뒤 다시 물어보세요."
    to_move = analysis.get("to_move")
    if to_move in ("B", "W"):
        next_color = "흑" if to_move == "B" else "백"
    else:
        next_color = "백" if color_that_moved == "B" else "흑"
    sign = 1 if next_color == "흑" else -1
    best = top[0]
    best_wr = best["winrate_black"] if next_color == "흑" else 1.0 - best["winrate_black"]
    best_sl = sign * best["score_lead"]
    msg = (
        f"지금 {next_color} 차례라면 {best['coord']} 자리가 최선입니다 "
        f"({next_color} 승률 {best_wr*100:.1f}%, {next_color} 집차 {best_sl:+.1f})."
    )
    um = analysis.get("user_move")
    if um:
        um_wr = um["winrate_black"] if next_color == "흑" else 1.0 - um["winrate_black"]
        um_sl = sign * um["score_lead"]
        diff = um_sl - best_sl
        msg += (
            f" 학생이 지목한 {um['coord']}는 {next_color} 승률 {um_wr*100:.1f}%, "
            f"{next_color} 집차 {um_sl:+.1f}로 1순위 대비 {diff:+.1f}집 차이가 납니다."
        )
    elif len(top) >= 2:
        second_sl = sign * top[1]["score_lead"]
        msg += (
            f" 차선은 {top[1]['coord']}({next_color} 집차 {second_sl:+.1f})이지만 "
            f"1순위와 집·승률 차이만큼 손해입니다."
        )
    return msg


def _data_only_reason_answer(analysis: dict, color_that_moved: str) -> str:
    """LLM 없이 KataGo 분석 데이터만으로 이유 답변 조립. 수치는 next_color 기준."""
    top = analysis.get("top_moves", [])
    if not top:
        return "현재 포지션에서 뚜렷한 손해 요인을 찾지 못했습니다."
    to_move = analysis.get("to_move")
    if to_move in ("B", "W"):
        color_name = "백" if to_move == "B" else "흑"
        next_color = "흑" if to_move == "B" else "백"
    else:
        color_name = "흑" if color_that_moved == "B" else "백"
        next_color = "백" if color_that_moved == "B" else "흑"
    sign = 1 if next_color == "흑" else -1
    best = top[0]
    sl = analysis.get("score_lead", 0.0)  # 흑 기준 유지
    if sl >= 0:
        pos_str = f"흑이 {sl:+.1f}집 유리"
    else:
        pos_str = f"백이 {abs(sl):+.1f}집 유리"
    best_sl_nc = sign * best["score_lead"]
    msg = (
        f"{color_name}이 둔 뒤 현재 평가는 {pos_str}입니다. "
        f"지금 {next_color} 입장에서는 {best['coord']} 자리가 최선이며 "
        f"{next_color} 집차 {best_sl_nc:+.1f} 기준으로 평가됩니다."
    )
    um = analysis.get("user_move")
    if um:
        um_sl_nc = sign * um["score_lead"]
        diff = um_sl_nc - best_sl_nc
        msg += (
            f" 학생이 지목한 {um['coord']}는 {next_color} 집차 {um_sl_nc:+.1f}로 "
            f"1순위 대비 {diff:+.1f}집 손해입니다."
        )
    else:
        msg += (
            " 방금 수가 더 좋았으려면 상대의 다음 수(약한 돌 또는 큰 자리) 선점을 "
            "막는 방향으로 두어야 했습니다."
        )
    return msg
