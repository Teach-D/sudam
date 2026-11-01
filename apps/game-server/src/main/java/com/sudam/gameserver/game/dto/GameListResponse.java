package com.sudam.gameserver.game.dto;

import com.sudam.gameserver.game.domain.Game;
import com.sudam.gameserver.game.domain.GameScore;

import java.time.LocalDateTime;
import java.util.UUID;

public record GameListResponse(
        UUID id,
        String status,
        String mode,
        int boardSize,
        float komi,
        int moveCount,
        String result,
        LocalDateTime startedAt,
        LocalDateTime endedAt,
        LocalDateTime createdAt
) {
    public static GameListResponse from(Game game, GameScore score) {
        return new GameListResponse(
                game.getId(),
                game.getStatus().name(),
                game.getMode().name(),
                game.getBoardSize(),
                game.getKomi(),
                game.getMoveCount(),
                score != null ? score.getResult() : null,
                game.getStartedAt(),
                game.getEndedAt(),
                game.getCreatedAt()
        );
    }
}
