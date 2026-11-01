package com.sudam.gameserver.game.dto;

import com.sudam.gameserver.game.domain.Game;

import java.time.LocalDateTime;
import java.util.UUID;

public record GameResponse(
        UUID id,
        String status,
        String mode,
        int boardSize,
        float komi,
        int moveCount,
        long blackTimeMs,
        long whiteTimeMs,
        boolean clockPaused,
        LocalDateTime createdAt
) {
    public static GameResponse from(Game g) {
        return new GameResponse(
                g.getId(),
                g.getStatus().name(),
                g.getMode().name(),
                g.getBoardSize(),
                g.getKomi(),
                g.getMoveCount(),
                g.getBlackTimeMs(),
                g.getWhiteTimeMs(),
                g.isClockPaused(),
                g.getCreatedAt()
        );
    }
}
