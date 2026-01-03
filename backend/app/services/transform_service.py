"""Backward compatibility - re-export from transactions domain."""
from app.domains.transactions.service import TransactionService


class TransformService:
    """Backward compatible wrapper around TransactionService."""
    
    @staticmethod
    def extract_merchant(description, details):
        return TransactionService.extract_merchant(description, details)
    
    @staticmethod
    def calculate_signed_amount(amount, debit_credit):
        return TransactionService.calculate_signed_amount(amount, debit_credit)
    
    @staticmethod
    def calculate_week_start(date):
        return TransactionService.calculate_week_start(date)
    
    @staticmethod
    def is_internal_transfer(description, details, merchant):
        return TransactionService.is_internal_transfer(description, details, merchant)
    
    def transform_transaction(self, transaction):
        return TransactionService.transform_transaction(transaction)


__all__ = ['TransformService']
