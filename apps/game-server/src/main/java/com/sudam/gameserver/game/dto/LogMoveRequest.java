package com.sudam.gameserver.game.dto;

public record LogMoveRequest(
        String color,      // "BLACK" or "WHITE"
        Integer row,       // null = pass
        Integer col,       // null = pass
        String source,     // "HUMAN" or "AI"
        Float scoreLead,
        Float winrate
) {}
