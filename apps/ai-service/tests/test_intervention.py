from __future__ import annotations

from fastapi.testclient import TestClient


def test_check_triggers_on_large_drop(client: TestClient):
    payload = {
        "game_id": "g1",
        "move_number": 40,
        "score_before": 5.0,
        "score_after": -7.0,
        "winrate_before": 0.62,
        "winrate_after": 0.38,
        "score_stdev": 2.0,
        "interventions_so_far": 0,
        "last_intervention_move": 0,
    }
    r = client.post("/api/intervention/check", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["triggered"] is True
    assert data["reason_type"] == "life_death"
    assert data["score_drop"] == 12.0


def test_check_no_trigger_on_small_drop(client: TestClient):
    payload = {
        "game_id": "g1",
        "move_number": 40,
        "score_before": 2.0,
        "score_after": 1.5,
        "winrate_before": 0.52,
        "winrate_after": 0.51,
        "score_stdev": 2.0,
        "interventions_so_far": 0,
        "last_intervention_move": 0,
    }
    r = client.post("/api/intervention/check", json=payload)
    assert r.status_code == 200
    assert r.json()["triggered"] is False


def test_draft_returns_text(client: TestClient):
    payload = {
        "game_id": "g1",
        "board_state": [[0] * 19 for _ in range(19)],
        "reason_type": "life_death",
        "score_drop": 12.0,
        "move_number": 40,
        "color_that_moved": "B",
    }
    r = client.post("/api/intervention/draft", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert len(data["draft_text"]) > 10
    assert data["reason_type"] == "life_death"
