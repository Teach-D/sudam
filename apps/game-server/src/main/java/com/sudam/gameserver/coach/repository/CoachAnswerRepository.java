package com.sudam.gameserver.coach.repository;

import com.sudam.gameserver.coach.domain.CoachAnswer;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface CoachAnswerRepository extends JpaRepository<CoachAnswer, Long> {
    List<CoachAnswer> findByGameIdOrderByCreatedAtAsc(UUID gameId);
    List<CoachAnswer> findByRatingAndFeedbackReason(String rating, String feedbackReason);
}
