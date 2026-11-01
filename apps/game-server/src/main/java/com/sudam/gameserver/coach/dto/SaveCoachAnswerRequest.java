package com.sudam.gameserver.coach.dto;

import java.util.Map;

public record SaveCoachAnswerRequest(
        String kind,
        int moveNumber,
        String questionText,
        String answerText,
        String reasonType,
        Boolean verified,
        Map<String, Object> analysisSnapshot,
        String llmModel,
        Integer latencyMs
) {}
