package com.sudam.gameserver.game.event;

import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

import java.util.UUID;

@Component
public class GameEventPublisher {

    private final SimpMessagingTemplate messaging;

    public GameEventPublisher(SimpMessagingTemplate messaging) {
        this.messaging = messaging;
    }

    public void publish(UUID gameId, String type, Object payload) {
        messaging.convertAndSend("/topic/game/" + gameId, new GameEvent(type, payload));
    }
}
