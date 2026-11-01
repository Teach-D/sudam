package com.sudam.gameserver.game.domain;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "game_scores")
public class GameScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "game_id", nullable = false)
    private Game game;

    @Column(nullable = false, length = 20)
    private String method = "territory";

    @Column(nullable = false)
    private float blackScore;

    @Column(nullable = false)
    private float whiteScore;

    @Column(nullable = false, length = 10)
    private String result;  // "B+5.5" or "W+3.0"

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected GameScore() {}

    public static GameScore of(Game game, String method, float blackScore, float whiteScore) {
        float diff = blackScore - whiteScore;
        String result = diff > 0
                ? String.format("B+%.1f", diff)
                : String.format("W+%.1f", -diff);

        GameScore s = new GameScore();
        s.game = game;
        s.method = method;
        s.blackScore = blackScore;
        s.whiteScore = whiteScore;
        s.result = result;
        return s;
    }

    public Long getId() { return id; }
    public Game getGame() { return game; }
    public String getMethod() { return method; }
    public float getBlackScore() { return blackScore; }
    public float getWhiteScore() { return whiteScore; }
    public String getResult() { return result; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
