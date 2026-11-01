package com.sudam.gameserver.coach.controller;

import com.sudam.gameserver.coach.dto.CoachAnswerResponse;
import com.sudam.gameserver.coach.dto.FeedbackRequest;
import com.sudam.gameserver.coach.dto.SaveCoachAnswerRequest;
import com.sudam.gameserver.coach.service.CoachAnswerService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api")
public class CoachAnswerController {

    private final CoachAnswerService service;

    public CoachAnswerController(CoachAnswerService service) {
        this.service = service;
    }

    @PostMapping("/games/{gameId}/coach-answers")
    public ResponseEntity<CoachAnswerResponse> save(
            @PathVariable UUID gameId,
            @RequestBody SaveCoachAnswerRequest req
    ) {
        Long id = service.save(gameId, req);
        return ResponseEntity.status(HttpStatus.CREATED).body(new CoachAnswerResponse(id));
    }

    @PatchMapping("/coach-answers/{id}/feedback")
    public ResponseEntity<Void> feedback(
            @PathVariable Long id,
            @RequestBody FeedbackRequest req
    ) {
        service.applyFeedback(id, req);
        return ResponseEntity.noContent().build();
    }
}
