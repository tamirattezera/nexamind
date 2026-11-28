class IdempotencyKeyReused(Exception):
    """Raised when an idempotency key is reused with different content."""

    error_code = "IDEMPOTENCY_KEY_REUSED"

    def __init__(self):
        super().__init__(
            "This idempotency key has already been used with different content."
        )


class ChatTurnAlreadyInProgress(Exception):
    """Raised when another generation is already active in the conversation."""

    error_code = "CHAT_TURN_ALREADY_IN_PROGRESS"

    def __init__(self):
        super().__init__(
            "A message is already being generated for this conversation."
        )


class GenerationRateLimitExceeded(Exception):
    """Raised when the authenticated user exceeds the generation rate limit."""

    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self):
        super().__init__(
            "The generation submission rate limit has been exceeded."
        )
