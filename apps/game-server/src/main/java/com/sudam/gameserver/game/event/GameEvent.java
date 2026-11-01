package com.sudam.gameserver.game.event;

/**
 * STOMP 이벤트 래퍼. type으로 구분:
 * move.play, move.ai, coach.pause, coach.resume, game.end
 */
public record GameEvent(String type, Object payload) {}
