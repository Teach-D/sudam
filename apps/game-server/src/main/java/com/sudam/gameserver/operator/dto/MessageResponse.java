package com.sudam.gameserver.operator.dto;

import com.sudam.gameserver.operator.domain.Message;

import java.time.LocalDateTime;
import java.util.UUID;

public record MessageResponse(
        Long id,
        UUID gameId,
        String type,
        String content,
        boolean read,
        LocalDateTime createdAt
) {
    public static MessageResponse from(Message m) {
        return new MessageResponse(
                m.getId(),
                m.getGame().getId(),
                m.getType().name(),
                m.getContent(),
                m.isRead(),
                m.getCreatedAt()
        );
    }
}
