package com.sudam.gameserver.operator.repository;

import com.sudam.gameserver.operator.domain.Message;
import com.sudam.gameserver.operator.domain.MessageType;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface MessageRepository extends JpaRepository<Message, Long> {
    List<Message> findByGameIdOrderByCreatedAtAsc(UUID gameId);
    List<Message> findByTypeAndReadFalseOrderByCreatedAtAsc(MessageType type);
}
