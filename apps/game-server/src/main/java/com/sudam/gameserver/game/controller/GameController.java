package com.sudam.gameserver.game.controller;

import com.sudam.gameserver.game.dto.*;
import com.sudam.gameserver.game.service.GameService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/games")
public class GameController {

    private final GameService service;

    public GameController(GameService service) {
        this.service = service;
    }

    @PostMapping
    public ResponseEntity<GameResponse> create(@RequestBody CreateGameRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.createGame(req));
    }

    @GetMapping("/{id}")
    public GameResponse get(@PathVariable UUID id) {
        return service.getGame(id);
    }

    // S2-2: STOMP 이벤트도 함께 발행
    @PostMapping("/{id}/moves")
    public ResponseEntity<MoveResponse> logMove(
            @PathVariable UUID id,
            @RequestBody LogMoveRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.logMove(id, req));
    }

    @GetMapping("/{id}/moves")
    public List<MoveResponse> getMoves(@PathVariable UUID id) {
        return service.getMoves(id);
    }

    // S2-1: PLAYING → COACH_PAUSE
    @PostMapping("/{id}/pause")
    public GameResponse pause(
            @PathVariable UUID id,
            @RequestBody PauseForCoachRequest req) {
        return service.pauseForCoach(id, req);
    }

    // S2-1: COACH_PAUSE → ANSWERING
    @PostMapping("/{id}/answering")
    public GameResponse startAnswering(@PathVariable UUID id) {
        return service.startAnswering(id);
    }

    // S2-1/S2-3: COACH_PAUSE/ANSWERING → PLAYING (시계 재개)
    @PostMapping("/{id}/resume")
    public GameResponse resume(@PathVariable UUID id) {
        return service.resumeGame(id);
    }

    // S2-4: 고쳐 두기
    @PostMapping("/{id}/takeback")
    public TakebackResponse takeback(@PathVariable UUID id) {
        return service.takeback(id);
    }

    // S2-5: 계가 + 게임 종료
    @PostMapping("/{id}/score")
    public ResponseEntity<GameScoreResponse> endWithScore(
            @PathVariable UUID id,
            @RequestBody GameScoreRequest req) {
        return ResponseEntity.status(HttpStatus.CREATED).body(service.endGameWithScore(id, req));
    }
}
