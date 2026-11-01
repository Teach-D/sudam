package com.sudam.gameserver.coach.service;

import com.sudam.gameserver.coach.domain.CoachAnswer;
import com.sudam.gameserver.coach.dto.FeedbackRequest;
import com.sudam.gameserver.coach.dto.SaveCoachAnswerRequest;
import com.sudam.gameserver.coach.repository.CoachAnswerRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.UUID;

@Service
@Transactional
public class CoachAnswerService {

    private final CoachAnswerRepository repo;

    public CoachAnswerService(CoachAnswerRepository repo) {
        this.repo = repo;
    }

    public Long save(UUID gameId, SaveCoachAnswerRequest req) {
        return repo.save(CoachAnswer.create(gameId, req)).getId();
    }

    public void applyFeedback(Long id, FeedbackRequest req) {
        CoachAnswer answer = repo.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
        answer.applyFeedback(req.rating(), req.feedbackReason());
    }
}
