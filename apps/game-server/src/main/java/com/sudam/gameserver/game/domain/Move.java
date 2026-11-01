package com.sudam.gameserver.game.domain;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "moves",
       uniqueConstraints = @UniqueConstraint(columnNames = {"game_id", "move_number"}))
public class Move {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "game_id", nullable = false)
    private Game game;

    @Column(nullable = false)
    private int moveNumber;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 5)
    private Color color;

    private Integer row;
    private Integer col;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 10)
    private MoveSource source;

    private Float scoreLead;
    private Float winrate;

    @Column(nullable = false)
    private boolean retracted = false;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected Move() {}

    public static Move of(Game game, int moveNumber, Color color,
                          Integer row, Integer col, MoveSource source,
                          Float scoreLead, Float winrate) {
        Move m = new Move();
        m.game = game;
        m.moveNumber = moveNumber;
        m.color = color;
        m.row = row;
        m.col = col;
        m.source = source;
        m.scoreLead = scoreLead;
        m.winrate = winrate;
        return m;
    }

    public void retract() { this.retracted = true; }

    public Long getId() { return id; }
    public Game getGame() { return game; }
    public int getMoveNumber() { return moveNumber; }
    public Color getColor() { return color; }
    public Integer getRow() { return row; }
    public Integer getCol() { return col; }
    public MoveSource getSource() { return source; }
    public Float getScoreLead() { return scoreLead; }
    public Float getWinrate() { return winrate; }
    public boolean isRetracted() { return retracted; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
