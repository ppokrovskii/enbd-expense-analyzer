"""Persons API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .models import Person
from .service import PersonService


router = APIRouter(prefix="/api/persons", tags=["persons"])


# ============================================================================
# Pydantic Models
# ============================================================================

class PersonCreate(BaseModel):
    name: str


class PersonUpdate(BaseModel):
    name: Optional[str] = None


class PersonResponse(BaseModel):
    id: int
    user_id: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=List[PersonResponse])
def list_persons(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get all persons for the current user.
    
    Note: Persons are user-level entities (a user owns multiple persons).
    The person_id in ctx is not used here since we're listing all persons.
    """
    return PersonService.get_persons(ctx.db, ctx.user_id)


@router.get("/active", response_model=Optional[PersonResponse])
def get_active_person(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get the currently active person."""
    person = PersonService.get_active_person(ctx.db, ctx.user_id)
    if not person:
        # Auto-create a default person if none exists
        person = PersonService.ensure_default_person(ctx.db, ctx.user_id)
    return person


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(
    person_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get a specific person."""
    person = PersonService.get_person(ctx.db, person_id, ctx.user_id)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    return person


@router.post("/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(
    person_data: PersonCreate,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Create a new person."""
    person = PersonService.create_person(ctx.db, ctx.user_id, person_data.name)
    return person


@router.put("/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: int,
    person_data: PersonUpdate,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Update a person's details."""
    person = PersonService.update_person(ctx.db, person_id, ctx.user_id, person_data.name)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    return person


@router.put("/{person_id}/activate", response_model=PersonResponse)
def activate_person(
    person_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Make a person the active context for the user."""
    person = PersonService.activate_person(ctx.db, person_id, ctx.user_id)
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Delete a person and all their associated data."""
    deleted = PersonService.delete_person(ctx.db, person_id, ctx.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found"
        )
    return None
