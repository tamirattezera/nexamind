class ContextLimitExceeded(Exception):
    """Raised when mandatory conversation context exceeds its token budget."""

    error_code = "CHAT_CONTEXT_LIMIT_EXCEEDED"

    def __init__(self):
        super().__init__(
            "The required conversation context exceeds the configured input token budget."
        )


class ContextUnavailable(Exception):
    """Raised when conversation context cannot be prepared."""

    error_code = "CHAT_CONTEXT_UNAVAILABLE"

    def __init__(self):
        super().__init__(
            "Conversation context is temporarily unavailable."
        )


class ContextSnapshotStale(Exception):
    """Internal signal that a prepared context snapshot is stale."""


class ContextChanged(Exception):
    """Raised when context remains stale after all preparation attempts."""

    error_code = "CHAT_CONTEXT_CHANGED"

    def __init__(self):
        super().__init__(
            "Conversation context changed repeatedly. Please retry your request."
        )
