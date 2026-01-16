"""Tests for LLM error handling - ensuring user-friendly error messages."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.shared.exceptions import (
    LLMError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMServiceUnavailableError,
    LLMContextLengthError,
    parse_openai_error,
)


client = TestClient(app)


class TestExceptionParsing:
    """Test that OpenAI errors are correctly parsed into user-friendly exceptions."""
    
    def test_parse_quota_exceeded_error(self):
        """Test quota exceeded error detection."""
        error = Exception("Error code: 429 - insufficient_quota")
        result = parse_openai_error(error)
        assert isinstance(result, LLMQuotaExceededError)
        assert result.error_code == "quota_exceeded"
        assert "quota" in result.user_message.lower()
        
    def test_parse_rate_limit_error(self):
        """Test rate limit error detection."""
        error = Exception("Error code: 429 - rate_limit_exceeded")
        result = parse_openai_error(error)
        assert isinstance(result, LLMRateLimitError)
        assert result.error_code == "rate_limit"
        assert "high demand" in result.user_message.lower() or "wait" in result.user_message.lower()
        
    def test_parse_authentication_error(self):
        """Test authentication error detection."""
        error = Exception("Error code: 401 - invalid_api_key")
        result = parse_openai_error(error)
        assert isinstance(result, LLMAuthenticationError)
        assert result.error_code == "auth_error"
        
    def test_parse_service_unavailable_error(self):
        """Test service unavailable error detection."""
        error = Exception("Error code: 503 - service_unavailable")
        result = parse_openai_error(error)
        assert isinstance(result, LLMServiceUnavailableError)
        assert result.error_code == "service_unavailable"
        
    def test_parse_context_length_error(self):
        """Test context length exceeded error detection."""
        error = Exception("maximum context length exceeded")
        result = parse_openai_error(error)
        assert isinstance(result, LLMContextLengthError)
        assert result.error_code == "context_length_exceeded"
        assert "fewer merchants" in result.user_message.lower()
        
    def test_parse_generic_error(self):
        """Test that unknown errors are wrapped gracefully."""
        error = Exception("Something unexpected happened")
        result = parse_openai_error(error)
        assert isinstance(result, LLMError)
        assert result.error_code == "llm_error"
        assert "try again" in result.user_message.lower()


class TestAIBulkSuggestErrorResponses:
    """Test that AI bulk suggest endpoint returns proper error responses."""
    
    @patch('app.domains.categories.router.LLMCategorizationService')
    def test_quota_exceeded_returns_503_with_user_message(self, mock_service_class):
        """Test that quota exceeded returns 503 with user-friendly message."""
        # Setup mock to raise quota exceeded error
        mock_instance = MagicMock()
        mock_instance.bulk_suggest_categories.side_effect = LLMQuotaExceededError("Original error")
        mock_service_class.return_value = mock_instance
        
        response = client.post(
            "/api/categories/ai-bulk-suggest",
            json={"merchants": ["TEST MERCHANT"], "days": 30, "level": "global", "limit": 10},
            headers={"X-User-Id": "test-user", "X-Workspace-Id": "1"}
        )
        
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error_code"] == "quota_exceeded"
        assert "user_message" in data["detail"]
        assert "quota" in data["detail"]["user_message"].lower()
        
    @patch('app.domains.categories.router.LLMCategorizationService')
    def test_rate_limit_returns_503_with_user_message(self, mock_service_class):
        """Test that rate limit returns 503 with user-friendly message."""
        mock_instance = MagicMock()
        mock_instance.bulk_suggest_categories.side_effect = LLMRateLimitError("Rate limited")
        mock_service_class.return_value = mock_instance
        
        response = client.post(
            "/api/categories/ai-bulk-suggest",
            json={"merchants": ["TEST MERCHANT"], "days": 30, "level": "global", "limit": 10},
            headers={"X-User-Id": "test-user", "X-Workspace-Id": "1"}
        )
        
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error_code"] == "rate_limit"
        assert "wait" in data["detail"]["user_message"].lower() or "demand" in data["detail"]["user_message"].lower()


class TestExceptionMessages:
    """Test that exception messages are user-friendly."""
    
    def test_quota_exceeded_message_is_helpful(self):
        """Test quota exceeded provides actionable message."""
        error = LLMQuotaExceededError()
        assert "temporarily unavailable" in error.user_message.lower()
        assert "try again" in error.user_message.lower() or "contact" in error.user_message.lower()
        
    def test_rate_limit_message_is_helpful(self):
        """Test rate limit provides actionable message."""
        error = LLMRateLimitError()
        assert "wait" in error.user_message.lower() or "moment" in error.user_message.lower()
        
    def test_context_length_message_suggests_solution(self):
        """Test context length error suggests reducing input."""
        error = LLMContextLengthError()
        assert "fewer" in error.user_message.lower() or "less" in error.user_message.lower()
