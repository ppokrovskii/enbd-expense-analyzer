"""Backward compatibility - re-export from categories domain."""
from app.domains.categories.llm_service import LLMCategorizationService

__all__ = ['LLMCategorizationService']
