"""Backward compatibility - re-export parsers from transactions domain."""
from app.domains.transactions.parsers.enbd_parser import ENBDParser
from app.domains.transactions.parsers.fab_parser import FABParser
from app.domains.transactions.parsers.wio_parser import WIOParser
from app.domains.transactions.parsers.base_parser import BankParser

__all__ = ['BankParser', 'ENBDParser', 'FABParser', 'WIOParser']

