class ContextLimitExceeded(Exception):
    """Raised when mandatory conversation context exceeds its token budget."""

    error_code = "CHAT_CONTEXT_LIMIT_EXCEEDED"

    def __init__(self):
        super().__init__(
            "The required conversation context exceeds the configured input token budget."
        )
