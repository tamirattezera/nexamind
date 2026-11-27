from apps.conversations.models import ChatTurn, Message


MAX_HISTORY_CANDIDATES = 100


def get_eligible_history_messages(
    conversation,
    current_user_message,
) -> tuple[Message, ...]:
    """
    Retrieve bounded historical candidates and retain only complete,
    successfully completed user-assistant exchanges.
    """
    candidates = list(
        Message.objects.filter(conversation=conversation)
        .select_related(
            "user_chat_turn",
            "assistant_chat_turn",
        )
        .exclude(id=current_user_message.id)
        .order_by("-created_at", "-id")[:MAX_HISTORY_CANDIDATES]
    )

    candidates.reverse()
    candidates_by_id = {
        message.id: message
        for message in candidates
    }

    eligible_messages = []

    for message in candidates:
        if message.role == Message.Role.USER:
            try:
                turn = message.user_chat_turn
            except ChatTurn.DoesNotExist:
                continue

            counterpart_id = turn.assistant_message_id
            counterpart_role = Message.Role.ASSISTANT

        elif message.role == Message.Role.ASSISTANT:
            try:
                turn = message.assistant_chat_turn
            except ChatTurn.DoesNotExist:
                continue

            counterpart_id = turn.user_message_id
            counterpart_role = Message.Role.USER

        else:
            continue

        if (
            turn.status != ChatTurn.Status.COMPLETED
            or turn.conversation_id != conversation.id
        ):
            continue

        counterpart = candidates_by_id.get(counterpart_id)

        if counterpart is None or counterpart.role != counterpart_role:
            continue

        eligible_messages.append(message)

    return tuple(eligible_messages)
