"""Backward compatibility - re-export from transactions domain."""
from app.domains.transactions.service import TransactionService as TransactionQueryService

__all__ = ['TransactionQueryService']
