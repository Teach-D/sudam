package com.sudam.gameserver.operator.service;

import com.sudam.gameserver.game.domain.Game;
import com.sudam.gameserver.game.repository.GameRepository;
import com.sudam.gameserver.operator.domain.*;
import com.sudam.gameserver.operator.dto.*;
import com.sudam.gameserver.operator.repository.InterventionRepository;
import com.sudam.gameserver.operator.repository.MessageRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.NoSuchElementException;
import java.util.UUID;

@Service
@Transactional
public class OperatorService {

    private final GameRepository games;
    private final InterventionRepository interventions;
    private final MessageRepository messages;

    public OperatorService(GameRepository games,
                           InterventionRepository interventions,
                           MessageRepository messages) {
        this.games = games;
        this.interventions = interventions;
        this.messages = messages;
    }

    // ── Interventions ────────────────────────────────────────────────────────

    public InterventionResponse createIntervention(CreateInterventionRequest req) {
        Game game = findGame(req.gameId());
        Intervention iv = Intervention.create(game, req.moveNumber(), req.reasonType(),
                                              req.interventionScore(), req.scoreDrop(),
                                              req.draftText());
        return InterventionResponse.from(interventions.save(iv));
    }

    @Transactional(readOnly = true)
    public List<InterventionResponse> getPendingInterventions() {
        return interventions.findByStatusOrderByCreatedAtAsc(InterventionStatus.PENDING)
                .stream().map(InterventionResponse::from).toList();
    }

    public InterventionResponse sendIntervention(UUID id, SendInterventionRequest req) {
        Intervention iv = findIntervention(id);
        iv.send(req.text());
        messages.save(Message.coachPush(iv.getGame(), iv, req.text()));
        return InterventionResponse.from(interventions.save(iv));
    }

    public InterventionResponse skipIntervention(UUID id) {
        Intervention iv = findIntervention(id);
        iv.skip();
        return InterventionResponse.from(interventions.save(iv));
    }

    // ── Messages ─────────────────────────────────────────────────────────────

    public MessageResponse addUserQuestion(UUID gameId, String content) {
        Game game = findGame(gameId);
        return MessageResponse.from(messages.save(Message.userQuestion(game, content)));
    }

    @Transactional(readOnly = true)
    public List<MessageResponse> getUnreadQuestions() {
        return messages.findByTypeAndReadFalseOrderByCreatedAtAsc(MessageType.USER_QUESTION)
                .stream().map(MessageResponse::from).toList();
    }

    public MessageResponse replyToQuestion(Long questionId, String content) {
        Message question = findMessage(questionId);
        question.markRead();
        messages.save(question);
        Message reply = Message.coachReply(question.getGame(), question, content);
        return MessageResponse.from(messages.save(reply));
    }

    @Transactional(readOnly = true)
    public List<MessageResponse> getGameMessages(UUID gameId) {
        findGame(gameId);
        return messages.findByGameIdOrderByCreatedAtAsc(gameId)
                .stream().map(MessageResponse::from).toList();
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private Game findGame(UUID id) {
        return games.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Game not found: " + id));
    }

    private Intervention findIntervention(UUID id) {
        return interventions.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Intervention not found: " + id));
    }

    private Message findMessage(Long id) {
        return messages.findById(id)
                .orElseThrow(() -> new NoSuchElementException("Message not found: " + id));
    }
}
