package com.sudam.gameserver.game.dto;

public record GameScoreRequest(
        String method,       // "territory" or "area"
        float blackScore,
        float whiteScore
) {}
