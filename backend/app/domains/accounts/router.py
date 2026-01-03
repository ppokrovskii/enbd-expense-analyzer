"""Accounts API endpoints for managing user bank accounts."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.dependencies import get_user_id
from .service import AccountService
from .models import UserAccount


router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    """Request model for creating an account."""
    name: str
    value: str
    bank: str = "ENBD"


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
    """Create a new user account configuration."""
    normalized_name = account.name.lower().replace(" ", "-")
    
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
    """List all user accounts."""
    return AccountService.get_user_accounts(db, user_id)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    """Delete a user account."""
    deleted = AccountService.delete_account(db, account_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

