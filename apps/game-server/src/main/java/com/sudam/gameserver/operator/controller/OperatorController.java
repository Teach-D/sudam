package com.sudam.gameserver.operator.controller;

import com.sudam.gameserver.operator.dto.*;
import com.sudam.gameserver.operator.service.OperatorService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/operator")
public class OperatorController {

    private final OperatorService service;

    public OperatorController(OperatorService service) {
        this.service = service;
    }

    // ── Interventions ────────────────────────────────────────────────────────

    @PostMapping("/interventions")
    public ResponseEntity<InterventionResponse> create(@RequestBody CreateInterventionRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.createIntervention(req));
    }

    @GetMapping("/interventions")
    public List<InterventionResponse> pending() {
        return service.getPendingInterventions();
    }

    @PostMapping("/interventions/{id}/send")
    public InterventionResponse send(@PathVariable UUID id,
                                     @RequestBody SendInterventionRequest req) {
        return service.sendIntervention(id, req);
    }

    @PostMapping("/interventions/{id}/skip")
    public InterventionResponse skip(@PathVariable UUID id) {
        return service.skipIntervention(id);
    }

    // ── Messages ─────────────────────────────────────────────────────────────

    @PostMapping("/games/{gameId}/questions")
    public ResponseEntity<MessageResponse> addQuestion(
            @PathVariable UUID gameId,
            @RequestBody Map<String, String> body) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(service.addUserQuestion(gameId, body.get("content")));
    }

    @GetMapping("/questions")
    public List<MessageResponse> unreadQuestions() {
        return service.getUnreadQuestions();
    }

    @PostMapping("/questions/{id}/reply")
    public MessageResponse reply(@PathVariable Long id,
                                 @RequestBody Map<String, String> body) {
        return service.replyToQuestion(id, body.get("content"));
    }

    @GetMapping("/games/{gameId}/messages")
    public List<MessageResponse> gameMessages(@PathVariable UUID gameId) {
        return service.getGameMessages(gameId);
    }
}
