package com.sudam.gameserver.game.repository;

import com.sudam.gameserver.game.domain.Game;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface GameRepository extends JpaRepository<Game, UUID> {}
