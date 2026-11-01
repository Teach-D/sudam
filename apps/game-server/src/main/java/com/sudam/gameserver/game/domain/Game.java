package com.sudam.gameserver.game.domain;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.UUID;

// black_player_id / white_player_id are nullable to support guest play

@Entity
@Table(name = "games")
public class Game {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private GameStatus status = GameStatus.WAITING;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 24)
    private GameMode mode = GameMode.AI_VS_HUMAN;

    @Column(nullable = false)
    private int boardSize = 19;

    @Column(nullable = false)
    private float komi = 6.5f;

    @Column(nullable = false)
    private int moveCount = 0;

    @Column(name = "black_player_id")
    private UUID blackPlayerId;

    @Column(name = "white_player_id")
    private UUID whitePlayerId;

    @Column(length = 20)
    private String aiRank;

    @Column(columnDefinition = "TEXT")
    private String sgfContent;

    @Column(nullable = false)
    private long blackTimeMs = 0;

    @Column(nullable = false)
    private long whiteTimeMs = 0;

    @Column(nullable = false)
    private boolean clockPaused = false;

    private LocalDateTime clockStartedAt;

    private LocalDateTime startedAt;
    private LocalDateTime endedAt;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected Game() {}

    public static Game create(int boardSize, float komi) {
        return create(boardSize, komi, GameMode.AI_VS_HUMAN);
    }

    public static Game create(int boardSize, float komi, GameMode mode) {
        Game g = new Game();
        g.boardSize = boardSize;
        g.komi = komi;
        g.mode = mode;
        return g;
    }

    public void start() {
        this.status = GameStatus.PLAYING;
        this.startedAt = LocalDateTime.now();
        this.clockStartedAt = LocalDateTime.now();
        this.clockPaused = false;
    }

    /** PLAYING → COACH_PAUSE: 개입 중 시계 자동 정지 */
    public void pauseForCoach() {
        if (status != GameStatus.PLAYING) {
            throw new IllegalStateException("Can only pause from PLAYING, was: " + status);
        }
        flushClock();
        this.status = GameStatus.COACH_PAUSE;
        this.clockPaused = true;
    }

    /** COACH_PAUSE → ANSWERING */
    public void startAnswering() {
        if (status != GameStatus.COACH_PAUSE) {
            throw new IllegalStateException("Must be in COACH_PAUSE to start answering, was: " + status);
        }
        this.status = GameStatus.ANSWERING;
    }

    /** COACH_PAUSE / ANSWERING → PLAYING */
    public void resume() {
        if (status != GameStatus.COACH_PAUSE && status != GameStatus.ANSWERING) {
            throw new IllegalStateException("Cannot resume from " + status);
        }
        this.status = GameStatus.PLAYING;
        this.clockPaused = false;
        this.clockStartedAt = LocalDateTime.now();
    }

    public void finish() {
        flushClock();
        this.status = GameStatus.FINISHED;
        this.endedAt = LocalDateTime.now();
    }

    public void incrementMoveCount() {
        flushClock();
        this.moveCount++;
        if (!clockPaused) {
            this.clockStartedAt = LocalDateTime.now();
        }
    }

    /** 현재 플레이어의 경과 시간을 누적한다. */
    private void flushClock() {
        if (clockStartedAt == null || clockPaused) return;
        long elapsed = Duration.between(clockStartedAt, LocalDateTime.now()).toMillis();
        // moveCount 홀수 = 흑 차례(moveCount 0이면 흑이 첫 수)
        if (moveCount % 2 == 0) {
            blackTimeMs += elapsed;
        } else {
            whiteTimeMs += elapsed;
        }
        clockStartedAt = null;
    }

    public void setBlackPlayerId(UUID id) { this.blackPlayerId = id; }
    public void setWhitePlayerId(UUID id) { this.whitePlayerId = id; }
    public void setSgfContent(String sgf) { this.sgfContent = sgf; }
    public void setAiRank(String rank) { this.aiRank = rank; }

    public UUID getId() { return id; }
    public GameStatus getStatus() { return status; }
    public GameMode getMode() { return mode; }
    public int getBoardSize() { return boardSize; }
    public float getKomi() { return komi; }
    public int getMoveCount() { return moveCount; }
    public long getBlackTimeMs() { return blackTimeMs; }
    public long getWhiteTimeMs() { return whiteTimeMs; }
    public boolean isClockPaused() { return clockPaused; }
    public LocalDateTime getStartedAt() { return startedAt; }
    public LocalDateTime getEndedAt() { return endedAt; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public UUID getBlackPlayerId() { return blackPlayerId; }
    public UUID getWhitePlayerId() { return whitePlayerId; }
    public String getSgfContent() { return sgfContent; }
    public String getAiRank() { return aiRank; }
}
