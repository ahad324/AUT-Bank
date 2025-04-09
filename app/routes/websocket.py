from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from app.core.websocket_manager import ConnectionManager
from app.core.auth import jwt, SECRET_KEY, ALGORITHM
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
manager = ConnectionManager()

async def get_token_payload(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        return None

@router.websocket("/ws/user")
async def user_websocket(
    websocket: WebSocket, 
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user_id = None
    try:
        # Verify token
        payload = await get_token_payload(token, db)
        if not payload:
            await websocket.close(code=4001)
            return

        user_id = int(payload.get("sub"))
        print(f"User {user_id} connecting to WebSocket")

        # Connect to WebSocket
        entity_id = await manager.connect(websocket, token, "user")
        if not entity_id:
            await websocket.close(code=4002)
            return

        print(f"User {user_id} connected successfully")

        try:
            while True:
                data = await websocket.receive_text()
                print(f"Received message from user {user_id}: {data}")
        except WebSocketDisconnect:
            print(f"User {user_id} disconnected")
            if user_id:
                await manager.disconnect(websocket, user_id, "user")
        except Exception as e:
            print(f"Error in user websocket: {str(e)}")
            if user_id:
                await manager.disconnect(websocket, user_id, "user")
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=4000)
    except Exception as e:
        print(f"WebSocket connection error: {str(e)}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=4000)

@router.websocket("/ws/admin")
async def admin_websocket(
    websocket: WebSocket, 
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        # Verify token
        payload = await get_token_payload(token, db)
        if not payload:
            print("Invalid admin token")
            await websocket.close(code=4001)
            return

        admin_id = int(payload.get("sub"))
        print(f"Admin {admin_id} connecting to WebSocket")

        # Connect to WebSocket
        entity_id = await manager.connect(websocket, token, "admin")
        if not entity_id:
            print(f"Failed to connect admin {admin_id}")
            await websocket.close(code=4002)
            return

        print(f"Admin {admin_id} connected successfully")

        try:
            while True:
                data = await websocket.receive_text()
                print(f"Received message from admin {admin_id}: {data}")
        except WebSocketDisconnect:
            print(f"Admin {admin_id} disconnected")
            await manager.disconnect(websocket, admin_id, "admin")
        except Exception as e:
            print(f"Error in admin websocket: {str(e)}")
            await manager.disconnect(websocket, admin_id, "admin")
            await websocket.close(code=4000)
    except Exception as e:
        print(f"Admin WebSocket connection error: {str(e)}")
        if not websocket.client_state.disconnected:
            await websocket.close(code=4000)