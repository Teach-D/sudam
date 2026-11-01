-- S1: 판 단위 로그 + 운영자 메시지

CREATE TABLE games (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status      VARCHAR(20) NOT NULL DEFAULT 'WAITING',
    board_size  INT NOT NULL DEFAULT 19,
    komi        REAL         NOT NULL DEFAULT 6.5,
    move_count  INT NOT NULL DEFAULT 0,
    started_at  TIMESTAMP,
    ended_at    TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE moves (
    id           BIGSERIAL PRIMARY KEY,
    game_id      UUID NOT NULL REFERENCES games(id),
    move_number  INT NOT NULL,
    color        VARCHAR(5) NOT NULL,   -- BLACK, WHITE
    row          INT,                   -- NULL = pass
    col          INT,                   -- NULL = pass
    source       VARCHAR(10) NOT NULL,  -- HUMAN, AI
    score_lead   REAL,
    winrate      REAL,
    created_at   TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (game_id, move_number)
);

CREATE TABLE interventions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id             UUID NOT NULL REFERENCES games(id),
    move_number         INT NOT NULL,
    reason_type         VARCHAR(30),
    intervention_score  REAL,
    score_drop          REAL,
    draft_text          TEXT,
    sent_text           TEXT,
    status              VARCHAR(10) NOT NULL DEFAULT 'PENDING',  -- PENDING, SENT, SKIPPED
    created_at          TIMESTAMP NOT NULL DEFAULT now()
);

-- 운영자↔사용자 메시지 (S1-4, S1-5)
CREATE TABLE messages (
    id              BIGSERIAL PRIMARY KEY,
    game_id         UUID NOT NULL REFERENCES games(id),
    intervention_id UUID REFERENCES interventions(id),
    type            VARCHAR(20) NOT NULL,  -- COACH_PUSH, USER_QUESTION, COACH_REPLY
    content         TEXT NOT NULL,
    read            BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_moves_game ON moves(game_id, move_number);
CREATE INDEX idx_interventions_game ON interventions(game_id);
CREATE INDEX idx_messages_game ON messages(game_id, created_at);
CREATE INDEX idx_messages_unread ON messages(game_id, read) WHERE read = false;
