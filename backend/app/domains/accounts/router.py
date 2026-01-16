"""Accounts API endpoints for managing user bank accounts."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
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
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Create a new user account configuration.
    
    Note: Accounts are user-level, not person-specific. Bank accounts
    can have transactions for multiple persons (e.g., family members).
    """
    normalized_name = account.name.lower().replace(" ", "-")
    
    # Accounts are user-level (shared across workspaces)
    existing = ctx.query_no_workspace_filter(UserAccount).filter(
        UserAccount.account_name == normalized_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account '{normalized_name}' already exists"
        )
    
    new_account = UserAccount(
        user_id=ctx.user_id,
        account_name=normalized_name,
        account_number=account.value,
        bank=account.bank,
        is_primary=False
    )
    
    ctx.db.add(new_account)
    ctx.commit()
    ctx.refresh(new_account)
    
    return new_account


@router.get("/", response_model=List[AccountResponse])
def list_accounts(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """List all user accounts.
    
    Note: Accounts are user-level, not person-specific.
    """
    return AccountService.get_user_accounts(ctx.db, ctx.user_id)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Delete a user account."""
    deleted = AccountService.delete_account(ctx.db, account_id, ctx.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
