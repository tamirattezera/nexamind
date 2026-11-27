from apps.ai.contracts import (
    GenerationRequest,
    GenerationResult,
    TokenCountRequest,
    TokenCountResult,
)
from apps.ai.providers.gemini import GeminiProvider


def count_tokens(request: TokenCountRequest) -> TokenCountResult:
    """
    Count input tokens through the configured provider.

    The service owns the provider instance and its client lifecycle.
    """
    provider = GeminiProvider()

    try:
        return provider.count_tokens(request)
    finally:
        provider.close()


def generate_response(request: GenerationRequest) -> GenerationResult:
    """
    Generate an AI response through the configured provider.

    The service owns the provider instance and its client lifecycle.
    """
    provider = GeminiProvider()

    try:
        return provider.generate(request)
    finally:
        provider.close()
