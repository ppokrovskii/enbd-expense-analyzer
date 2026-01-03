"""Accounts domain - User bank account management."""
from .router import router
from .models import UserAccount
from .service import AccountService

__all__ = ['router', 'UserAccount', 'AccountService']

