package com.sudam.gameserver.operator.domain;

public enum MessageType {
    COACH_PUSH,     // operator → user (개입 설명)
    USER_QUESTION,  // user → operator
    COACH_REPLY     // operator → user (질문 답변)
}
