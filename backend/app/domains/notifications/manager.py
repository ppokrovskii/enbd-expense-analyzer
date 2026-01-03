"""WebSocket connection manager for real-time updates."""
from fastapi import WebSocket
from typing import Dict, List
import json


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages to clients."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a WebSocket connection and register it for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"✅ WebSocket connected for user: {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                print(f"❌ WebSocket disconnected for user: {user_id}")
            except ValueError:
                pass
    
    async def send_job_progress(self, user_id: str, job_id: str, progress: int, processed: int, total: int):
        """Send job progress update to all connections for a user."""
        if user_id not in self.active_connections:
            return
        
        message = {
            "type": "job_progress",
            "job_id": job_id,
            "progress": progress,
            "processed": processed,
            "total": total
        }
        
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        for conn in dead_connections:
            self.disconnect(conn, user_id)
    
    async def send_job_complete(self, user_id: str, job_id: str, result: dict):
        """Send job completion notification to all connections for a user."""
        if user_id not in self.active_connections:
            return
        
        message = {"type": "job_complete", "job_id": job_id, "result": result}
        
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        for conn in dead_connections:
            self.disconnect(conn, user_id)
    
    async def send_rules_applied(self, user_id: str, job_id: str, transactions_updated: int, by_category: dict):
        """
        Send rule application result notification - optimized for toaster display.
        
        Example message:
        {
            "type": "rules_applied",
            "job_id": "...",
            "transactions_updated": 15,
            "by_category": {"Groceries": 10, "Transport": 5},
            "toast_message": "Categorized 15 transactions (Groceries: 10, Transport: 5)"
        }
        """
        if user_id not in self.active_connections:
            return
        
        # Build toast-friendly message
        if transactions_updated == 0:
            toast_message = "No transactions matched the applied rules"
        elif by_category:
            details = ", ".join([f"{cat}: {count}" for cat, count in by_category.items()])
            toast_message = f"Categorized {transactions_updated} transactions ({details})"
        else:
            toast_message = f"Categorized {transactions_updated} transactions"
        
        message = {
            "type": "rules_applied",
            "job_id": job_id,
            "transactions_updated": transactions_updated,
            "by_category": by_category,
            "toast_message": toast_message
        }
        
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        for conn in dead_connections:
            self.disconnect(conn, user_id)
    
    async def send_job_failed(self, user_id: str, job_id: str, error: str):
        """Send job failure notification to all connections for a user."""
        if user_id not in self.active_connections:
            return
        
        message = {"type": "job_failed", "job_id": job_id, "error": error}
        
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        for conn in dead_connections:
            self.disconnect(conn, user_id)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast a generic message to all connections for a user."""
        if user_id not in self.active_connections:
            return
        
        dead_connections = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        for conn in dead_connections:
            self.disconnect(conn, user_id)


# Global WebSocket manager instance
ws_manager = ConnectionManager()

