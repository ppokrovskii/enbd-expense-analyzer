"""WebSocket router for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query(..., description="User ID for authentication")
):
    """
    WebSocket endpoint for real-time updates.
    
    Clients connect with: ws://localhost:8000/ws?user_id=<user_id>
    
    Message types received:
    - job_progress: { type, job_id, progress, processed, total }
    - job_complete: { type, job_id, result }
    - job_failed: { type, job_id, error }
    
    Args:
        websocket: WebSocket connection
        user_id: User ID from query parameter
    """
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Echo back for testing (can be removed in production)
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)

