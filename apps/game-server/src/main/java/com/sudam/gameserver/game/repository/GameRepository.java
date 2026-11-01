package com.sudam.gameserver.game.repository;

import com.sudam.gameserver.game.domain.Game;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.UUID;

public interface GameRepository extends JpaRepository<Game, UUID> {

    @Query("SELECT g FROM Game g WHERE g.blackPlayerId = :userId OR g.whitePlayerId = :userId ORDER BY g.createdAt DESC")
    List<Game> findByPlayerId(UUID userId);
}
