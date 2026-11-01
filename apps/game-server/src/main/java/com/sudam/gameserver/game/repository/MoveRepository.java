package com.sudam.gameserver.game.repository;

import com.sudam.gameserver.game.domain.Move;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface MoveRepository extends JpaRepository<Move, Long> {
    List<Move> findByGameIdOrderByMoveNumberAsc(UUID gameId);
    Optional<Move> findTopByGameIdAndRetractedFalseOrderByMoveNumberDesc(UUID gameId);
}
