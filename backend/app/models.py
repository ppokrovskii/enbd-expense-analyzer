"""Backward compatibility - re-export models from domain modules."""
# Transaction domain models
from app.domains.transactions.models import Transaction, UnparsedFile

# Category domain models
from app.domains.categories.models import Category, Rule, LLMCache

# Chat domain models
from app.domains.chat.models import ChatSession, ChatMessage, ChatContext, TokenUsage

# Account domain models
from app.domains.accounts.models import UserAccount

# Jobs domain models
from app.domains.jobs.models import BackgroundJob

__all__ = [
    # Transactions
    'Transaction',
    'UnparsedFile',
    # Categories
    'Category',
    'Rule',
    'LLMCache',
    # Chat
    'ChatSession',
    'ChatMessage',
    'ChatContext',
    'TokenUsage',
    # Accounts
    'UserAccount',
    # Jobs
    'BackgroundJob',
]
