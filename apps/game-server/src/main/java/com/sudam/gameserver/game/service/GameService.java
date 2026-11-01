package com.sudam.gameserver.game.service;

import com.sudam.gameserver.game.domain.*;
import com.sudam.gameserver.game.dto.*;
import com.sudam.gameserver.game.event.GameEventPublisher;
import com.sudam.gameserver.game.repository.GameRepository;
import com.sudam.gameserver.game.repository.GameScoreRepository;
import com.sudam.gameserver.game.repository.MoveRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.UUID;

@Service
@Transactional
public class GameService {

    private final GameRepository games;
    private final MoveRepository moves;
    private final GameScoreRepository scores;
    private final GameEventPublisher events;

    public GameService(GameRepository games, MoveRepository moves,
                       GameScoreRepository scores, GameEventPublisher events) {
        this.games = games;
        this.moves = moves;
        this.scores = scores;
        this.events = events;
    }

    public GameResponse createGame(CreateGameRequest req) {
        return createGame(req, null);
    }

    public GameResponse createGame(CreateGameRequest req, UUID blackPlayerId) {
        Game game = Game.create(req.boardSize(), req.komi(), req.mode());
        if (blackPlayerId != null) game.setBlackPlayerId(blackPlayerId);
        if (req.aiRank() != null) game.setAiRank(req.aiRank());
        game.start();
        return GameResponse.from(games.save(game));
    }

    @Transactional(readOnly = true)
    public GameResponse getGame(UUID id) {
        return GameResponse.from(findGame(id));
    }

    public MoveResponse logMove(UUID gameId, LogMoveRequest req) {
        Game game = findGame(gameId);
        int nextMoveNumber = game.getMoveCount() + 1;
        Color color = Color.valueOf(req.color());
        MoveSource source = MoveSource.valueOf(req.source());

        Move move = Move.of(game, nextMoveNumber, color, req.row(), req.col(),
                            source, req.scoreLead(), req.winrate());
        game.incrementMoveCount();
        games.save(game);
        Move saved = moves.save(move);

        // STOMP 이벤트 발행
        // winrate/scoreLead 가 null 이면 아예 payload 에서 뺀다. 과거엔 0.5/0 으로 폴백했는데
        // 클라이언트가 그걸 반영하면서 수를 둘 때마다 승률바가 50/50 으로 깜빡였다.
        String eventType = source == MoveSource.AI ? "move.ai" : "move.play";
        Map<String, Object> payload = new HashMap<>();
        payload.put("moveNumber", saved.getMoveNumber());
        payload.put("color", color.name());
        payload.put("row", req.row());
        payload.put("col", req.col());
        if (req.scoreLead() != null) payload.put("scoreLead", req.scoreLead());
        if (req.winrate() != null) payload.put("winrate", req.winrate());
        events.publish(gameId, eventType, payload);

        return MoveResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public List<MoveResponse> getMoves(UUID gameId) {
        findGame(gameId);
        return moves.findByGameIdOrderByMoveNumberAsc(gameId)
                    .stream()
                    .map(MoveResponse::from)
                    .toList();
    }

    /** S2-1: PLAYING → COACH_PAUSE */
    public GameResponse pauseForCoach(UUID gameId, PauseForCoachRequest req) {
        Game game = findGame(gameId);
        game.pauseForCoach();
        games.save(game);
        events.publish(gameId, "coach.pause", Map.of(
                "moveNumber", game.getMoveCount(),
                "reasonType", req.reasonType() != null ? req.reasonType() : "",
                "interventionScore", req.interventionScore(),
                "scoreDrop", req.scoreDrop()
        ));
        return GameResponse.from(game);
    }

    /** S2-1: COACH_PAUSE → ANSWERING */
    public GameResponse startAnswering(UUID gameId) {
        Game game = findGame(gameId);
        game.startAnswering();
        return GameResponse.from(games.save(game));
    }

    /** S2-1/S2-3: COACH_PAUSE/ANSWERING → PLAYING */
    public GameResponse resumeGame(UUID gameId) {
        Game game = findGame(gameId);
        game.resume();
        games.save(game);
        events.publish(gameId, "coach.resume", Map.of("moveNumber", game.getMoveCount()));
        return GameResponse.from(game);
    }

    /** S2-4: 직전 수 무르기 */
    public TakebackResponse takeback(UUID gameId) {
        Game game = findGame(gameId);
        Move lastMove = moves.findTopByGameIdAndRetractedFalseOrderByMoveNumberDesc(gameId)
                .orElseThrow(() -> new IllegalStateException("No moves to take back"));
        lastMove.retract();
        moves.save(lastMove);

        // moveCount 는 살아있는 수 기준으로 재계산
        long activeCount = moves.findByGameIdOrderByMoveNumberAsc(gameId)
                .stream().filter(m -> !m.isRetracted()).count();
        // Game 엔티티의 moveCount를 직접 조정하기 위해 새 메서드 없이 현재 값에서 -1
        // (S3에서 필요 시 Game에 setMoveCount 추가)
        events.publish(gameId, "move.retract", Map.of(
                "retractedMoveNumber", lastMove.getMoveNumber(),
                "newMoveCount", (int) activeCount
        ));
        return new TakebackResponse((int) activeCount, lastMove.getMoveNumber());
    }

    /** S2-5: 계가 + 종료 (SGF 자동 저장) */
    public GameScoreResponse endGameWithScore(UUID gameId, GameScoreRequest req) {
        Game game = findGame(gameId);
        game.finish();

        List<Move> moveList = moves.findByGameIdOrderByMoveNumberAsc(gameId)
                .stream().filter(m -> !m.isRetracted()).toList();

        GameScore score = GameScore.of(game, req.method(), req.blackScore(), req.whiteScore());
        scores.save(score);

        game.setSgfContent(buildSgf(game, moveList, score.getResult()));
        games.save(game);

        events.publish(gameId, "game.end", Map.of(
                "result", score.getResult(),
                "blackScore", score.getBlackScore(),
                "whiteScore", score.getWhiteScore()
        ));
        return GameScoreResponse.from(score);
    }

    @Transactional(readOnly = true)
    public List<GameListResponse> getUserGames(UUID userId) {
        return games.findByPlayerId(userId).stream()
                .map(g -> {
                    GameScore score = scores.findTopByGameIdOrderByCreatedAtDesc(g.getId()).orElse(null);
                    return GameListResponse.from(g, score);
                })
                .toList();
    }

    @Transactional(readOnly = true)
    public String getSgf(UUID gameId) {
        Game game = findGame(gameId);
        if (game.getSgfContent() != null) return game.getSgfContent();
        // 진행 중인 게임도 다운로드 가능
        List<Move> moveList = moves.findByGameIdOrderByMoveNumberAsc(gameId)
                .stream().filter(m -> !m.isRetracted()).toList();
        return buildSgf(game, moveList, null);
    }

    private static String buildSgf(Game game, List<Move> moveList, String result) {
        StringBuilder sb = new StringBuilder();
        sb.append("(;GM[1]FF[4]SZ[").append(game.getBoardSize()).append(']');
        sb.append("KM[").append(game.getKomi()).append(']');
        if (result != null) sb.append("RE[").append(result).append(']');
        for (Move m : moveList) {
            String color = m.getColor() == Color.BLACK ? "B" : "W";
            if (m.getRow() == null) {
                sb.append(';').append(color).append("[]");
            } else {
                char c = (char) ('a' + m.getCol());
                char r = (char) ('a' + m.getRow());
                sb.append(';').append(color).append('[').append(c).append(r).append(']');
            }
        }
        sb.append(')');
        return sb.toString();
    }

    private Game findGame(UUID id) {
        return games.findById(id)
                    .orElseThrow(() -> new NoSuchElementException("Game not found: " + id));
    }
}
