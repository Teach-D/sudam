package com.sudam.gameserver.game.dto;

import com.sudam.gameserver.game.domain.GameMode;

public record CreateGameRequest(
        int boardSize,
        float komi,
        GameMode mode
) {
    public CreateGameRequest {
        if (boardSize != 9 && boardSize != 13 && boardSize != 19)
            throw new IllegalArgumentException("boardSize must be 9, 13, or 19");
        if (mode == null) mode = GameMode.AI_VS_HUMAN;
    }
}
