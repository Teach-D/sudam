package com.sudam.gameserver.operator.repository;

import com.sudam.gameserver.operator.domain.Intervention;
import com.sudam.gameserver.operator.domain.InterventionStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface InterventionRepository extends JpaRepository<Intervention, UUID> {
    List<Intervention> findByStatusOrderByCreatedAtAsc(InterventionStatus status);
    List<Intervention> findByGameIdOrderByCreatedAtAsc(UUID gameId);
}
