"""Workspaces domain service."""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from .models import Workspace
from app.domains.categories.models import Category

# Default categories to create for each new workspace
DEFAULT_CATEGORIES = [
    {"name": "Groceries", "color": "#22c55e"},
    {"name": "Dining & Restaurants", "color": "#f97316"},
    {"name": "Transport", "color": "#3b82f6"},
    {"name": "Shopping", "color": "#ec4899"},
    {"name": "Entertainment", "color": "#a855f7"},
    {"name": "Utilities", "color": "#64748b"},
    {"name": "Healthcare", "color": "#ef4444"},
    {"name": "Travel", "color": "#06b6d4"},
    {"name": "Subscriptions", "color": "#8b5cf6"},
    {"name": "Income", "color": "#10b981"},
    {"name": "Transfer", "color": "#6b7280"},
    {"name": "Other", "color": "#9ca3af"},
]


class WorkspaceService:
    """Service for managing workspaces."""
    
    @staticmethod
    def get_workspaces(db: Session, user_id: str) -> List[Workspace]:
        """Get all workspaces for a user."""
        return db.query(Workspace).filter(Workspace.user_id == user_id).order_by(Workspace.name).all()
    
    @staticmethod
    def get_workspace(db: Session, workspace_id: int, user_id: str) -> Optional[Workspace]:
        """Get a specific workspace, ensuring it belongs to the user."""
        return db.query(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id
        ).first()
    
    @staticmethod
    def get_active_workspace(db: Session, user_id: str) -> Optional[Workspace]:
        """Get the currently active workspace for a user."""
        return db.query(Workspace).filter(
            Workspace.user_id == user_id,
            Workspace.is_active == True
        ).first()
    
    @staticmethod
    def create_workspace(db: Session, user_id: str, name: str, skip_default_categories: bool = False) -> Workspace:
        """Create a new workspace for a user.
        
        If this is the first workspace, make it active automatically.
        Creates default categories for the new workspace unless skip_default_categories=True.
        """
        # Check if user has any workspaces
        existing_count = db.query(Workspace).filter(Workspace.user_id == user_id).count()
        is_first = existing_count == 0
        
        workspace = Workspace(
            user_id=user_id,
            name=name,
            is_active=is_first,  # First workspace is auto-active
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        
        # Create default categories for the new workspace
        if not skip_default_categories:
            WorkspaceService._create_default_categories(db, user_id, workspace.id)
        
        return workspace
    
    @staticmethod
    def _create_default_categories(db: Session, user_id: str, workspace_id: int) -> None:
        """Create default categories for a workspace."""
        for cat_data in DEFAULT_CATEGORIES:
            category = Category(
                user_id=user_id,
                workspace_id=workspace_id,
                name=cat_data["name"],
                color=cat_data["color"],
                created_at=datetime.utcnow()
            )
            db.add(category)
        db.commit()
    
    @staticmethod
    def update_workspace(db: Session, workspace_id: int, user_id: str, name: Optional[str] = None) -> Optional[Workspace]:
        """Update a workspace's details."""
        workspace = WorkspaceService.get_workspace(db, workspace_id, user_id)
        if not workspace:
            return None
        
        if name:
            workspace.name = name
        workspace.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(workspace)
        return workspace
    
    @staticmethod
    def activate_workspace(db: Session, workspace_id: int, user_id: str) -> Optional[Workspace]:
        """Make a workspace active, deactivating any currently active workspace."""
        workspace = WorkspaceService.get_workspace(db, workspace_id, user_id)
        if not workspace:
            return None
        
        # Deactivate all other workspaces for this user
        db.query(Workspace).filter(
            Workspace.user_id == user_id,
            Workspace.id != workspace_id
        ).update({"is_active": False})
        
        # Activate the selected workspace
        workspace.is_active = True
        workspace.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(workspace)
        return workspace
    
    @staticmethod
    def delete_workspace(db: Session, workspace_id: int, user_id: str) -> bool:
        """Delete a workspace and all their data.
        
        Note: This cascades to delete all related data (transactions, categories, etc.)
        when workspace_id foreign keys are added with ON DELETE CASCADE.
        
        Returns True if deleted, False if not found.
        """
        workspace = WorkspaceService.get_workspace(db, workspace_id, user_id)
        if not workspace:
            return False
        
        # Check if this is the active workspace
        was_active = workspace.is_active
        
        db.delete(workspace)
        db.commit()
        
        # If we deleted the active workspace, activate another one if available
        if was_active:
            remaining = db.query(Workspace).filter(Workspace.user_id == user_id).first()
            if remaining:
                remaining.is_active = True
                db.commit()
        
        return True
    
    @staticmethod
    def ensure_default_workspace(db: Session, user_id: str) -> Workspace:
        """Ensure a user has at least one workspace, creating default if needed.
        
        This is useful for migration or first-time setup.
        """
        active = WorkspaceService.get_active_workspace(db, user_id)
        if active:
            return active
        
        # Check if user has any workspaces
        existing = db.query(Workspace).filter(Workspace.user_id == user_id).first()
        if existing:
            # Make the first one active
            existing.is_active = True
            db.commit()
            return existing
        
        # Create default workspace
        return WorkspaceService.create_workspace(db, user_id, "Default")
