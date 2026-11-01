package com.sudam.gameserver.operator.dto;

import java.util.UUID;

public record CreateInterventionRequest(
        UUID gameId,
        int moveNumber,
        String reasonType,
        float interventionScore,
        float scoreDrop,
        String draftText
) {}
