"""Backward compatibility - re-export from transactions domain."""
from app.domains.transactions.import_service import MultiBankImportService

__all__ = ['MultiBankImportService']
