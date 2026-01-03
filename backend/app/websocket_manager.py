"""Backward compatibility - re-export from notifications domain."""
from app.domains.notifications.manager import ws_manager, ConnectionManager

__all__ = ['ws_manager', 'ConnectionManager']
