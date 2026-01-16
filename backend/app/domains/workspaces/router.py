"""Workspaces API router."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.shared.filtered_query import FilteredQueryContext, get_filtered_context
from .models import Workspace
from .service import WorkspaceService


router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ============================================================================
# Pydantic Models
# ============================================================================

class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None


class WorkspaceResponse(BaseModel):
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

@router.get("/", response_model=List[WorkspaceResponse])
def list_workspaces(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get all workspaces for the current user.
    
    Note: Workspaces are user-level entities (a user owns multiple workspaces).
    The workspace_id in ctx is not used here since we're listing all workspaces.
    """
    return WorkspaceService.get_workspaces(ctx.db, ctx.user_id)


@router.get("/active", response_model=Optional[WorkspaceResponse])
def get_active_workspace(ctx: FilteredQueryContext = Depends(get_filtered_context)):
    """Get the currently active workspace."""
    workspace = WorkspaceService.get_active_workspace(ctx.db, ctx.user_id)
    if not workspace:
        # Auto-create a default workspace if none exists
        workspace = WorkspaceService.ensure_default_workspace(ctx.db, ctx.user_id)
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Get a specific workspace."""
    workspace = WorkspaceService.get_workspace(ctx.db, workspace_id, ctx.user_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    return workspace


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    workspace_data: WorkspaceCreate,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Create a new workspace."""
    workspace = WorkspaceService.create_workspace(ctx.db, ctx.user_id, workspace_data.name)
    return workspace


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    workspace_data: WorkspaceUpdate,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Update a workspace's details."""
    workspace = WorkspaceService.update_workspace(ctx.db, workspace_id, ctx.user_id, workspace_data.name)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    return workspace


@router.put("/{workspace_id}/activate", response_model=WorkspaceResponse)
def activate_workspace(
    workspace_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Make a workspace the active context for the user."""
    workspace = WorkspaceService.activate_workspace(ctx.db, workspace_id, ctx.user_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    ctx: FilteredQueryContext = Depends(get_filtered_context)
):
    """Delete a workspace and all their associated data."""
    deleted = WorkspaceService.delete_workspace(ctx.db, workspace_id, ctx.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    return None
