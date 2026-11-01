-- S4: 회원 인증, 기보 저장

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname      VARCHAR(100),
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

ALTER TABLE games
    ADD COLUMN black_player_id UUID REFERENCES users(id),
    ADD COLUMN white_player_id UUID REFERENCES users(id),
    ADD COLUMN sgf_content     TEXT;

CREATE INDEX idx_refresh_tokens_user  ON refresh_tokens(user_id);
CREATE INDEX idx_games_black_player   ON games(black_player_id);
CREATE INDEX idx_games_white_player   ON games(white_player_id);
