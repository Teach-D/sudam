from __future__ import annotations

from fastapi.testclient import TestClient


def _empty_board() -> list[list[int]]:
    return [[0] * 19 for _ in range(19)]


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_move_returns_valid_coords_on_empty_board(client: TestClient):
    payload = {
        "game_id": "test-game",
        "board_state": _empty_board(),
        "move_number": 1,
        "color": "B",
    }
    r = client.post("/api/move", json=payload)
    assert r.status_code == 200
    data = r.json()
    if not data["is_pass"]:
        assert 0 <= data["row"] <= 18
        assert 0 <= data["col"] <= 18


def test_move_returns_empty_intersection(client: TestClient):
    board = _empty_board()
    # Fill all but bottom-right corner
    for r in range(19):
        for c in range(19):
            if not (r == 18 and c == 18):
                board[r][c] = 1 if (r + c) % 2 == 0 else 2

    payload = {
        "game_id": "test-game",
        "board_state": board,
        "move_number": 361,
        "color": "B",
    }
    r = client.post("/api/move", json=payload)
    assert r.status_code == 200
    data = r.json()
    # Only valid move is (18,18) or pass
    if not data["is_pass"]:
        assert data["row"] == 18
        assert data["col"] == 18


def test_move_str_is_korean(client: TestClient):
    payload = {
        "game_id": "g1",
        "board_state": _empty_board(),
        "move_number": 1,
        "color": "B",
    }
    r = client.post("/api/move", json=payload)
    data = r.json()
    if not data["is_pass"]:
        # Korean coordinate starts with a hangul syllable
        assert "가" <= data["move_str"][0] <= "힣"
