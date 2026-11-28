from apps.ai.config import GeminiConfig
from apps.ai.contracts import (
    GenerationRequest,
    GenerationResult,
    TokenCountRequest,
    TokenCountResult,
)
from apps.ai.providers.gemini import GeminiProvider


def count_tokens(
    request: TokenCountRequest,
    *,
    config: GeminiConfig | None = None,
) -> TokenCountResult:
    """
    Count input tokens through the configured provider.

    An explicit configuration keeps token counting consistent
    across all context-preparation attempts.
    """
    provider = GeminiProvider(config=config) if config is not None else GeminiProvider()

    try:
        return provider.count_tokens(request)
    finally:
        provider.close()


def generate_response(
    request: GenerationRequest,
    *,
    config: GeminiConfig | None = None,
) -> GenerationResult:
    """
    Generate an AI response through the configured provider.

    An explicit configuration keeps generation consistent
    with the configuration used during context preparation.
    The service owns the provider instance and its client lifecycle.
    """
    provider = GeminiProvider(config=config) if config is not None else GeminiProvider()

    try:
        return provider.generate(request)
    finally:
        provider.close()
