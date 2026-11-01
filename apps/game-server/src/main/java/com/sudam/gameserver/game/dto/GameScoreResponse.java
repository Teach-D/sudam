package com.sudam.gameserver.game.dto;

import com.sudam.gameserver.game.domain.GameScore;

import java.util.UUID;

public record GameScoreResponse(
        UUID gameId,
        String method,
        float blackScore,
        float whiteScore,
        String result
) {
    public static GameScoreResponse from(GameScore s) {
        return new GameScoreResponse(
                s.getGame().getId(),
                s.getMethod(),
                s.getBlackScore(),
                s.getWhiteScore(),
                s.getResult()
        );
    }
}
