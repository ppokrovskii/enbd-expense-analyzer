"""Accounts API endpoints for managing user bank accounts."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_user_id
from app.services.account_service import AccountService
from app.models import UserAccount

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    """Request model for creating an account - simplified to name + value only."""
    name: str  # e.g., "current account" (will be normalized to "current-account")
    value: str  # e.g., "1234567890" or "****7890"
    bank: str = "ENBD"  # Default bank


class AccountResponse(BaseModel):
    """Response model for account data."""
    id: int
    account_name: str
    account_number: str
    bank: str
    is_primary: bool
    
    class Config:
        from_attributes = True


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Create a new user account configuration with simplified input.
    
    Args:
        account: Account data (name and value only)
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        Created account
        
    Note:
        - Name is normalized: spaces replaced with dashes, converted to lowercase
        - Example: "Current Account" -> "current-account"
        - User should create two separate records for full and masked values:
          1. name="current-account", value="1234567890"
          2. name="current-account-masked", value="****7890"
    """
    # Normalize account name: lowercase, replace spaces with dashes
    normalized_name = account.name.lower().replace(" ", "-")
    
    # Check if account with same name already exists for this user
    existing = db.query(UserAccount).filter(
        UserAccount.user_id == user_id,
        UserAccount.account_name == normalized_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account '{normalized_name}' already exists"
        )
    
    new_account = UserAccount(
        user_id=user_id,
        account_name=normalized_name,
        account_number=account.value,
        bank=account.bank,
        is_primary=False
    )
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    return new_account


@router.get("/", response_model=List[AccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    List all user accounts.
    
    Args:
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        List of user accounts
    """
    return AccountService.get_user_accounts(db, user_id)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """
    Delete a user account.
    
    Args:
        account_id: Account ID
        db: Database session
        user_id: User ID from dependency
        
    Returns:
        204 No Content on success
    """
    deleted = AccountService.delete_account(db, account_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

