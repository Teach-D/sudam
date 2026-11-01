package com.sudam.gameserver.operator.dto;

import com.sudam.gameserver.operator.domain.Intervention;

import java.time.LocalDateTime;
import java.util.UUID;

public record InterventionResponse(
        UUID id,
        UUID gameId,
        int moveNumber,
        String reasonType,
        Float interventionScore,
        Float scoreDrop,
        String draftText,
        String sentText,
        String status,
        LocalDateTime createdAt
) {
    public static InterventionResponse from(Intervention i) {
        return new InterventionResponse(
                i.getId(),
                i.getGame().getId(),
                i.getMoveNumber(),
                i.getReasonType(),
                i.getInterventionScore(),
                i.getScoreDrop(),
                i.getDraftText(),
                i.getSentText(),
                i.getStatus().name(),
                i.getCreatedAt()
        );
    }
}
