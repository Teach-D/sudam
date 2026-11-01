package com.sudam.gameserver.coach.domain;

import com.sudam.gameserver.coach.dto.SaveCoachAnswerRequest;
import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@Entity
@Table(name = "coach_answers")
public class CoachAnswer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private UUID gameId;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false, length = 10)
    private String kind;

    @Column(nullable = false)
    private int moveNumber;

    @Column(columnDefinition = "TEXT")
    private String questionText;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String answerText;

    @Column(length = 30)
    private String reasonType;

    private Boolean verified;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> analysisSnapshot;

    @Column(length = 80)
    private String llmModel;

    private Integer latencyMs;

    @Column(length = 4)
    private String rating;

    @Column(length = 20)
    private String feedbackReason;

    protected CoachAnswer() {}

    public static CoachAnswer create(UUID gameId, SaveCoachAnswerRequest req) {
        CoachAnswer a = new CoachAnswer();
        a.gameId = gameId;
        a.kind = req.kind();
        a.moveNumber = req.moveNumber();
        a.questionText = req.questionText();
        a.answerText = req.answerText();
        a.reasonType = req.reasonType();
        a.verified = req.verified();
        a.analysisSnapshot = req.analysisSnapshot();
        a.llmModel = req.llmModel();
        a.latencyMs = req.latencyMs();
        return a;
    }

    public void applyFeedback(String rating, String feedbackReason) {
        this.rating = rating;
        this.feedbackReason = feedbackReason;
    }

    public Long getId() { return id; }
    public UUID getGameId() { return gameId; }
    public Instant getCreatedAt() { return createdAt; }
    public String getKind() { return kind; }
    public int getMoveNumber() { return moveNumber; }
    public String getQuestionText() { return questionText; }
    public String getAnswerText() { return answerText; }
    public String getReasonType() { return reasonType; }
    public Boolean getVerified() { return verified; }
    public Map<String, Object> getAnalysisSnapshot() { return analysisSnapshot; }
    public String getLlmModel() { return llmModel; }
    public Integer getLatencyMs() { return latencyMs; }
    public String getRating() { return rating; }
    public String getFeedbackReason() { return feedbackReason; }
}
