package com.sudam.gameserver.game.dto;

import com.sudam.gameserver.game.domain.Move;

import java.time.LocalDateTime;

public record MoveResponse(
        Long id,
        int moveNumber,
        String color,
        Integer row,
        Integer col,
        String source,
        Float scoreLead,
        Float winrate,
        boolean retracted,
        LocalDateTime createdAt
) {
    public static MoveResponse from(Move m) {
        return new MoveResponse(
                m.getId(),
                m.getMoveNumber(),
                m.getColor().name(),
                m.getRow(),
                m.getCol(),
                m.getSource().name(),
                m.getScoreLead(),
                m.getWinrate(),
                m.isRetracted(),
                m.getCreatedAt()
        );
    }
}
