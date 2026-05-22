from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket.manager import ConnectionManager
from app.api.v1.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: AsyncSession = Depends(get_db)):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Optionally handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)