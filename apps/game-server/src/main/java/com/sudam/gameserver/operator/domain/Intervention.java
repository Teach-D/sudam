package com.sudam.gameserver.operator.domain;

import com.sudam.gameserver.game.domain.Game;
import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "interventions")
public class Intervention {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "game_id", nullable = false)
    private Game game;

    @Column(nullable = false)
    private int moveNumber;

    @Column(length = 30)
    private String reasonType;

    private Float interventionScore;
    private Float scoreDrop;

    @Column(columnDefinition = "TEXT")
    private String draftText;

    @Column(columnDefinition = "TEXT")
    private String sentText;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private InterventionStatus status = InterventionStatus.PENDING;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected Intervention() {}

    public static Intervention create(Game game, int moveNumber, String reasonType,
                                      float score, float scoreDrop, String draftText) {
        Intervention i = new Intervention();
        i.game = game;
        i.moveNumber = moveNumber;
        i.reasonType = reasonType;
        i.interventionScore = score;
        i.scoreDrop = scoreDrop;
        i.draftText = draftText;
        return i;
    }

    public void send(String finalText) {
        this.sentText = finalText;
        this.status = InterventionStatus.SENT;
    }

    public void skip() {
        this.status = InterventionStatus.SKIPPED;
    }

    public UUID getId() { return id; }
    public Game getGame() { return game; }
    public int getMoveNumber() { return moveNumber; }
    public String getReasonType() { return reasonType; }
    public Float getInterventionScore() { return interventionScore; }
    public Float getScoreDrop() { return scoreDrop; }
    public String getDraftText() { return draftText; }
    public String getSentText() { return sentText; }
    public InterventionStatus getStatus() { return status; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
