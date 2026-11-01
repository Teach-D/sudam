"""Ad-hoc QA: 어긋난 color_that_moved를 보내도 ai-service가 KataGo 수순으로 보정하는지."""
import io
import json
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

mh = [
    ["B","Q16"],["W","D16"],["B","Q4"],["W","D4"],["B","F3"],["W","C6"],["B","R7"],
    ["W","R17"],["B","R16"],["W","Q17"],["B","P16"],["W","P17"],["B","O17"],["W","O18"],
    ["B","N17"],["W","N18"],["B","M17"],["W","O3"],["B","M3"],["W","K3"],["B","L5"],
    ["W","H3"],["B","P3"],["W","O4"],["B","L3"],["W","K4"],["B","N5"],["W","P6"],
    ["B","Q5"],["W","P8"],["B","M8"],
]
# 수순 끝이 B M8이므로 "방금 둔 색"은 B. 그러나 UI 버그를 흉내 내서 "W"를 보냄.
GTP_COLS = "ABCDEFGHJKLMNOPQRST"
board = [[0] * 19 for _ in range(19)]
for color, gtp in mh:
    col = GTP_COLS.index(gtp[0])
    row = 19 - int(gtp[1:])
    board[row][col] = 1 if color == "B" else 2

body = json.dumps({
    "game_id": "qa_colorfix",
    "board_state": board,
    "move_number": len(mh),
    "question_text": "6-17은 어때?",
    "color_that_moved": "W",  # 의도적으로 틀린 값
    "move_history": mh,
}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/coach/question",
    data=body,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=180) as r:
    data = json.loads(r.read().decode("utf-8"))
    print("ANSWER:", data["answer"])
