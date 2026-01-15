"""Custom exceptions for the application."""


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    
    def __init__(self, message: str, user_message: str, error_code: str = "llm_error"):
        super().__init__(message)
        self.message = message
        self.user_message = user_message
        self.error_code = error_code


class LLMQuotaExceededError(LLMError):
    """Raised when OpenAI API quota is exceeded."""
    
    def __init__(self, original_message: str = ""):
        super().__init__(
            message=f"OpenAI quota exceeded: {original_message}",
            user_message=(
                "AI categorization is temporarily unavailable. "
                "The OpenAI API quota has been exceeded. Please try again later or "
                "contact the administrator to check the billing status."
            ),
            error_code="quota_exceeded"
        )


class LLMRateLimitError(LLMError):
    """Raised when OpenAI API rate limit is hit."""
    
    def __init__(self, original_message: str = ""):
        super().__init__(
            message=f"OpenAI rate limit hit: {original_message}",
            user_message=(
                "AI categorization is temporarily unavailable due to high demand. "
                "Please wait a moment and try again."
            ),
            error_code="rate_limit"
        )


class LLMAuthenticationError(LLMError):
    """Raised when OpenAI API key is invalid."""
    
    def __init__(self, original_message: str = ""):
        super().__init__(
            message=f"OpenAI authentication failed: {original_message}",
            user_message=(
                "AI categorization is not available. "
                "The API key configuration is invalid. Please contact the administrator."
            ),
            error_code="auth_error"
        )


class LLMServiceUnavailableError(LLMError):
    """Raised when OpenAI API is unavailable."""
    
    def __init__(self, original_message: str = ""):
        super().__init__(
            message=f"OpenAI service unavailable: {original_message}",
            user_message=(
                "AI categorization service is temporarily unavailable. "
                "Please try again in a few minutes."
            ),
            error_code="service_unavailable"
        )


class LLMContextLengthError(LLMError):
    """Raised when input is too long for the model."""
    
    def __init__(self, original_message: str = ""):
        super().__init__(
            message=f"OpenAI context length exceeded: {original_message}",
            user_message=(
                "Too many merchants selected for AI categorization. "
                "Please select fewer merchants and try again."
            ),
            error_code="context_length_exceeded"
        )


def parse_openai_error(error) -> LLMError:
    """Parse an OpenAI API error and return the appropriate custom exception."""
    error_str = str(error).lower()
    error_message = str(error)
    
    # Check for quota exceeded
    if "insufficient_quota" in error_str or "quota" in error_str:
        return LLMQuotaExceededError(error_message)
    
    # Check for rate limit
    if "rate_limit" in error_str or "429" in error_str:
        return LLMRateLimitError(error_message)
    
    # Check for authentication errors
    if "invalid_api_key" in error_str or "authentication" in error_str or "401" in error_str:
        return LLMAuthenticationError(error_message)
    
    # Check for service unavailable
    if "503" in error_str or "service_unavailable" in error_str or "overloaded" in error_str:
        return LLMServiceUnavailableError(error_message)
    
    # Check for context length errors
    if "context_length" in error_str or "maximum context" in error_str:
        return LLMContextLengthError(error_message)
    
    # Default to generic LLM error
    return LLMError(
        message=error_message,
        user_message=(
            "An error occurred while processing with AI. "
            "Please try again later."
        ),
        error_code="llm_error"
    )
