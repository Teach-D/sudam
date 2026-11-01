from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from ai_service.app import app


@pytest.fixture
def empty_board():
    return [[0] * 19 for _ in range(19)]


@pytest.mark.asyncio
async def test_coach_push_returns_utterance(empty_board):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/coach/push", json={
            "game_id": "test-1",
            "board_state": empty_board,
            "reason_type": "life_death",
            "score_drop": 12.0,
            "move_number": 40,
            "color_that_moved": "B",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "utterance" in data
    assert len(data["utterance"]) > 0
    assert "hints" in data
    assert len(data["hints"]) == 3


@pytest.mark.asyncio
async def test_coach_push_all_reason_types(empty_board):
    reason_types = ["life_death", "cut_left", "missed_attack", "missed_big_point", "endgame_sente"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for rt in reason_types:
            resp = await client.post("/api/coach/push", json={
                "game_id": "test-rt",
                "board_state": empty_board,
                "reason_type": rt,
                "score_drop": 5.0,
                "move_number": 50,
                "color_that_moved": "B",
            })
            assert resp.status_code == 200, f"failed for {rt}"
            assert resp.json()["utterance"]


@pytest.mark.asyncio
async def test_coach_question_variation_type(empty_board):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/coach/question", json={
            "game_id": "test-q",
            "board_state": empty_board,
            "move_number": 30,
            "question_text": "최선 수가 어디인가요?",
            "color_that_moved": "B",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_type"] == "variation"
    assert data["answer"]


@pytest.mark.asyncio
async def test_coach_question_reason_type(empty_board):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/coach/question", json={
            "game_id": "test-q2",
            "board_state": empty_board,
            "move_number": 30,
            "question_text": "왜 그 수가 나쁜가요?",
            "color_that_moved": "B",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_type"] == "reason"


@pytest.mark.asyncio
async def test_coach_push_hint_steps_ordered(empty_board):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/coach/push", json={
            "game_id": "test-hints",
            "board_state": empty_board,
            "reason_type": "cut_left",
            "score_drop": 6.0,
            "move_number": 55,
            "color_that_moved": "W",
        })
    data = resp.json()
    steps = [h["step"] for h in data["hints"]]
    assert steps == [1, 2, 3]
    labels = [h["label"] for h in data["hints"]]
    assert labels == ["①", "②", "③"]
