-- S2: 상태 머신, 대국 시계, 고쳐 두기, 계가

ALTER TABLE games
    ADD COLUMN black_time_ms    BIGINT  NOT NULL DEFAULT 0,
    ADD COLUMN white_time_ms    BIGINT  NOT NULL DEFAULT 0,
    ADD COLUMN clock_paused     BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN clock_started_at TIMESTAMP;

ALTER TABLE moves
    ADD COLUMN retracted BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE game_scores (
    id          BIGSERIAL PRIMARY KEY,
    game_id     UUID         NOT NULL REFERENCES games(id),
    method      VARCHAR(20)  NOT NULL DEFAULT 'territory',
    black_score REAL NOT NULL,
    white_score REAL NOT NULL,
    result      VARCHAR(10)  NOT NULL,  -- "B+5.5" or "W+3.0"
    created_at  TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE INDEX idx_game_scores_game ON game_scores(game_id);
