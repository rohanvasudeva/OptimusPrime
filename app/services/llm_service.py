import os

from groq import Groq


class LLMServiceError(Exception):
    """A safe, user-facing failure from the LLM provider."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class LLMService:

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise LLMServiceError("The AI service is not configured.", 503)

        # Do not let the provider SDK retry for longer than a web request should
        # reasonably remain open. Errors are translated below into safe messages.
        self.client = Groq(api_key=api_key, timeout=30.0, max_retries=0)

    def generate_response(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
                messages=messages,
                temperature=0.7,
            )
            choices = getattr(response, "choices", None) or []
            content = getattr(getattr(choices[0], "message", None), "content", None) if choices else None
        except Exception as exc:
            raise self._to_service_error(exc) from exc

        if not content:
            raise LLMServiceError("The AI returned an empty response. Please try again.", 502)

        return content

    def stream_response(self, messages):
        """Yield non-empty text deltas from Groq as they become available."""
        try:
            response = self.client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
                messages=messages,
                temperature=0.7,
                stream=True,
            )

            for chunk in response:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                content = getattr(getattr(choices[0], "delta", None), "content", None)
                if content:
                    yield content
        except Exception as exc:
            raise self._to_service_error(exc) from exc

    @staticmethod
    def _to_service_error(exc: Exception) -> LLMServiceError:
        status_code = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        status_code = status_code or getattr(response, "status_code", None)
        error_name = type(exc).__name__.lower()

        if status_code == 429 or "ratelimit" in error_name:
            return LLMServiceError("The AI is rate limited. Please try again shortly.", 429)
        if "timeout" in error_name:
            return LLMServiceError("The AI request timed out. Please try again.", 504)
        if "connection" in error_name or "connect" in error_name:
            return LLMServiceError("The AI service is temporarily unavailable. Please try again.", 503)
        return LLMServiceError("Unable to generate an AI response right now. Please try again.", 502)
