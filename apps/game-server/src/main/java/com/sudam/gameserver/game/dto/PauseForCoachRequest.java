package com.sudam.gameserver.game.dto;

public record PauseForCoachRequest(
        String reasonType,      // life_death, cut_left, ...
        float interventionScore,
        float scoreDrop
) {}
