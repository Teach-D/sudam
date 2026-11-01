from __future__ import annotations

# SGF uses letters a-s for a 19x19 board (a=0, s=18)
_SGF_CHARS = "abcdefghijklmnopqrs"

# Korean column labels: 가 나 다 라 마 바 사 아 자 차 카 타 파 하 (14 chars, skip 'i')
# Standard Korean baduk notation skips 아 (which would be col 8) — no, actually
# Korean baduk uses: 가나다라마바사아자차카타파하 but column 8 (아) is used.
# Columns 0-18: 가(0) 나(1) 다(2) 라(3) 마(4) 바(5) 사(6) 아(7) 자(8) 차(9) 카(10) 타(11) 파(12) 하(13)
# Wait - 19x19 needs 19 columns. Korean standard uses 14 hangul syllables then numbers?
# Actually Korean baduk notation: columns are labeled with Korean letters A-T style
# Most common: 가 나 다 라 마 바 사 아 자 차 카 타 파 하 거 너 더 러 머 (19 cols)
# Rows are labeled 1-19 from bottom.
_KR_COLS = "가나다라마바사아자차카타파하거너더러머"
assert len(_KR_COLS) == 19  # noqa: S101


class Coordinate:
    """바둑판 좌표 변환.

    내부 표현: (row, col) — 0-indexed, row=0이 19줄(흑 시작 쪽 위), col=0이 왼쪽.
    SGF      : 'aa' = (0,0), 'as' = (0,18), 'sa' = (18,0)  (col먼저, row뒤 — SGF 표준)
    한국식   : '가1' = (18,0) ... '머19' = (0,18)  (row는 1-indexed from bottom)
    """

    @staticmethod
    def from_sgf(s: str) -> tuple[int, int]:
        """'cd' → (row, col). SGF는 (col, row) 순서임에 주의."""
        if len(s) != 2:
            raise ValueError(f"SGF coord must be 2 chars, got {s!r}")
        col = _SGF_CHARS.index(s[0])
        row = _SGF_CHARS.index(s[1])
        return row, col

    @staticmethod
    def to_sgf(row: int, col: int) -> str:
        return _SGF_CHARS[col] + _SGF_CHARS[row]

    @staticmethod
    def from_korean(s: str) -> tuple[int, int]:
        """'가1' → (18,0). 한국식은 아래부터 1행."""
        col_char = s[0]
        row_num = int(s[1:])
        col = _KR_COLS.index(col_char)
        row = 19 - row_num  # 1행 = row 18, 19행 = row 0
        return row, col

    @staticmethod
    def to_korean(row: int, col: int) -> str:
        row_num = 19 - row
        return _KR_COLS[col] + str(row_num)

    @staticmethod
    def from_numpy(r: int, c: int) -> tuple[int, int]:
        """numpy 인덱스와 내부 (row, col)은 동일하다."""
        return r, c

    @staticmethod
    def to_numpy(row: int, col: int) -> tuple[int, int]:
        return row, col

    @staticmethod
    def from_gtp(s: str) -> tuple[int, int]:
        """GTP 좌표 'A19' → (0, 0). GTP는 I를 건너뛰고 아래가 1행."""
        s = s.upper()
        col_char = s[0]
        row_num = int(s[1:])
        # GTP skips 'I'
        gtp_cols = "ABCDEFGHJKLMNOPQRST"
        col = gtp_cols.index(col_char)
        row = 19 - row_num
        return row, col

    @staticmethod
    def to_gtp(row: int, col: int) -> str:
        gtp_cols = "ABCDEFGHJKLMNOPQRST"
        return gtp_cols[col] + str(19 - row)
