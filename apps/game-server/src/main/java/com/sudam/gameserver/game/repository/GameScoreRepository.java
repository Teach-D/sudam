package com.sudam.gameserver.game.repository;

import com.sudam.gameserver.game.domain.GameScore;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface GameScoreRepository extends JpaRepository<GameScore, Long> {
    Optional<GameScore> findTopByGameIdOrderByCreatedAtDesc(UUID gameId);
}
