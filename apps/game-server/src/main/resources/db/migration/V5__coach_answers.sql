CREATE TABLE coach_answers (
    id                BIGSERIAL    PRIMARY KEY,
    game_id           UUID         NOT NULL REFERENCES games(id),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    kind              VARCHAR(10)  NOT NULL CHECK (kind IN ('push', 'reply')),
    move_number       INT          NOT NULL,
    question_text     TEXT,
    answer_text       TEXT         NOT NULL,
    reason_type       VARCHAR(30),
    verified          BOOLEAN,
    analysis_snapshot JSONB,
    llm_model         VARCHAR(80),
    latency_ms        INT,
    rating            VARCHAR(4)   CHECK (rating IN ('up', 'down')),
    feedback_reason   VARCHAR(20)  CHECK (feedback_reason IN ('wrong', 'unclear', 'too_long', 'report'))
);

CREATE INDEX ON coach_answers (game_id, move_number);
CREATE INDEX ON coach_answers (rating, feedback_reason) WHERE rating = 'down';
