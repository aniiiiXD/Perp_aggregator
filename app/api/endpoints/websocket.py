"""
WebSocket endpoint for real-time communication
"""
import uuid
from fastapi import APIRouter, WebSocket, Request

router = APIRouter()


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, request: Request):
    """WebSocket endpoint for real-time price updates"""
    connection_id = str(uuid.uuid4())
    ws_manager = request.app.state.ws_manager
    
    await ws_manager.handle_connection(websocket, connection_id)