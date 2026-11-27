import httpx2
from google import genai
from google.genai import errors, types

from apps.ai.config import GeminiConfig, get_gemini_config
from apps.ai.contracts import (
    ConversationMessage,
    GenerationRequest,
    GenerationResult,
    TokenCountRequest,
    TokenCountResult,
)


class ProviderError(Exception):
    """A provider request failed."""


class ProviderTimeoutError(ProviderError):
    """The provider request timed out."""


class ProviderResponseError(ProviderError):
    """The provider returned an unusable response."""


class ProviderBlockedError(ProviderResponseError):
    """The provider blocked the generation."""


def build_gemini_contents(
    messages: tuple[ConversationMessage, ...],
) -> list[types.Content]:
    """Translate NexaMind messages into Gemini contents."""
    return [
        types.Content(
            role="user" if message.role == "user" else "model",
            parts=[types.Part(text=message.content)],
        )
        for message in messages
    ]


def normalize_gemini_response(
    response: types.GenerateContentResponse,
    configured_model: str,
) -> GenerationResult:
    """Convert a Gemini response into a provider-neutral result."""

    if response.prompt_feedback and response.prompt_feedback.block_reason:
        raise ProviderBlockedError("Gemini blocked the prompt.")

    if not response.candidates:
        raise ProviderResponseError("Gemini returned no candidates.")

    candidate = response.candidates[0]

    if candidate.finish_reason not in (
        None,
        types.FinishReason.STOP,
        types.FinishReason.MAX_TOKENS,
    ):
        raise ProviderBlockedError(
            "Gemini did not produce an acceptable response."
        )

    if not candidate.content or not candidate.content.parts:
        raise ProviderResponseError(
            "Gemini returned no candidate content."
        )

    visible_text = "".join(
        part.text
        for part in candidate.content.parts
        if part.text and not part.thought
    ).strip()

    if not visible_text:
        raise ProviderResponseError(
            "Gemini returned no user-visible text."
        )

    usage = response.usage_metadata

    return GenerationResult(
        text=visible_text,
        model_name=response.model_version or configured_model,
        input_tokens=usage.prompt_token_count if usage else None,
        output_tokens=usage.candidates_token_count if usage else None,
        total_tokens=usage.total_token_count if usage else None,
        thinking_tokens=usage.thoughts_token_count if usage else None,
        finish_reason=(
            candidate.finish_reason.value
            if candidate.finish_reason
            else None
        ),
        response_id=response.response_id,
    )


class GeminiProvider:
    """Synchronous Gemini adapter with provider-neutral errors."""

    def __init__(
        self,
        config: GeminiConfig | None = None,
        client=None,
    ):
        self.config = config or get_gemini_config()
        self._owns_client = client is None

        self.client = client or genai.Client(
            api_key=self.config.api_key,
            http_options=types.HttpOptions(
                timeout=self.config.timeout_ms,
            ),
        )

    def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """Generate a response using the configured Gemini client."""

        generation_config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            max_output_tokens=self.config.max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_level=self.config.thinking_level,
            ),
        )

        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=build_gemini_contents(request.messages),
                config=generation_config,
            )
        except httpx2.TimeoutException as exc:
            raise ProviderTimeoutError(
                "The Gemini request timed out."
            ) from exc
        except (httpx2.ConnectError, errors.APIError) as exc:
            raise ProviderError(
                "The Gemini provider request failed."
            ) from exc

        return normalize_gemini_response(
            response,
            configured_model=self.config.model,
        )

    def count_tokens(
        self,
        request: TokenCountRequest,
    ) -> TokenCountResult:
        """Count the complete input context using Gemini."""

        count_config = types.CountTokensConfig(
            system_instruction=request.system_instruction,
        )

        try:
            response = self.client.models.count_tokens(
                model=self.config.model,
                contents=build_gemini_contents(request.messages),
                config=count_config,
            )
        except httpx2.TimeoutException as exc:
            raise ProviderTimeoutError(
                "The Gemini token-count request timed out."
            ) from exc
        except (httpx2.ConnectError, errors.APIError) as exc:
            raise ProviderError(
                "The Gemini token-count request failed."
            ) from exc

        if response.total_tokens is None or response.total_tokens < 0:
            raise ProviderResponseError(
                "Gemini returned an invalid token count."
            )

        return TokenCountResult(
            total_tokens=response.total_tokens,
        )

    def close(self):
        """Close the SDK client only when this adapter created it."""
        if self._owns_client:
            self.client.close()
