"""Service for managing user bank accounts."""
from typing import List, Dict
from sqlalchemy.orm import Session
from .models import UserAccount


class AccountService:
    """Service for managing user bank accounts and account variables."""
    
    @staticmethod
    def create_account(db: Session, user_id: str, account_data: dict) -> UserAccount:
        """Create a new user account configuration."""
        account = UserAccount(
            user_id=user_id,
            account_name=account_data['account_name'],
            account_number=account_data.get('account_number'),
            account_number_masked=account_data.get('account_number_masked'),
            bank=account_data['bank'],
            is_primary=account_data.get('is_primary', False)
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account
    
    @staticmethod
    def get_user_accounts(db: Session, user_id: str) -> List[UserAccount]:
        """Get all accounts for a user."""
        return db.query(UserAccount).filter_by(user_id=user_id).all()
    
    @staticmethod
    def get_account_variables(db: Session, user_id: str) -> Dict[str, str]:
        """
        Returns variable substitution map for categorization rules.
        
        Generates variables like:
        - {current_account} -> "1234"
        - {own_account} -> "1234|5678" (all account numbers)
        """
        accounts = AccountService.get_user_accounts(db, user_id)
        variables = {}
        
        for account in accounts:
            if account.account_number:
                variables[f"{{{account.account_name}}}"] = account.account_number
                variables[f"{{{account.account_name}_masked}}"] = account.account_number_masked or account.account_number
        
        # Add generic {own_account} that matches any user account
        all_numbers = [a.account_number for a in accounts if a.account_number]
        if all_numbers:
            variables["{own_account}"] = "|".join(all_numbers)
        
        return variables
    
    @staticmethod
    def delete_account(db: Session, account_id: int, user_id: str) -> bool:
        """Delete a user account."""
        account = db.query(UserAccount).filter_by(id=account_id, user_id=user_id).first()
        if not account:
            return False
        db.delete(account)
        db.commit()
        return True

