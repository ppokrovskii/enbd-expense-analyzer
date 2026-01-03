"""WebSocket router for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .manager import ws_manager

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
    """
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)

