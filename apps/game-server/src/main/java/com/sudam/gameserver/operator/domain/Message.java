package com.sudam.gameserver.operator.domain;

import com.sudam.gameserver.game.domain.Game;
import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "messages")
public class Message {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "game_id", nullable = false)
    private Game game;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "intervention_id")
    private Intervention intervention;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private MessageType type;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(nullable = false)
    private boolean read = false;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected Message() {}

    public static Message coachPush(Game game, Intervention intervention, String content) {
        Message m = new Message();
        m.game = game;
        m.intervention = intervention;
        m.type = MessageType.COACH_PUSH;
        m.content = content;
        return m;
    }

    public static Message userQuestion(Game game, String content) {
        Message m = new Message();
        m.game = game;
        m.type = MessageType.USER_QUESTION;
        m.content = content;
        return m;
    }

    public static Message coachReply(Game game, Message question, String content) {
        Message m = new Message();
        m.game = game;
        m.type = MessageType.COACH_REPLY;
        m.content = content;
        return m;
    }

    public void markRead() { this.read = true; }

    public Long getId() { return id; }
    public Game getGame() { return game; }
    public Intervention getIntervention() { return intervention; }
    public MessageType getType() { return type; }
    public String getContent() { return content; }
    public boolean isRead() { return read; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
