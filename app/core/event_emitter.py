from app.core.websocket_manager import ConnectionManager
from typing import Optional
from datetime import datetime, timezone
from app.core.websocket_manager import ConnectionManager
from fastapi import BackgroundTasks

manager = ConnectionManager()


async def emit_event(
    event_type: str,
    data: dict,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    broadcast: bool = False,
    background_tasks: Optional[BackgroundTasks] = None,
):
    message = {
        "type": event_type,
        "data": data,
        "timestamp": str(datetime.now(timezone.utc)),
    }

    async def send_notification():
        try:
            if broadcast:
                await manager.broadcast(message)
            elif user_id:
                await manager.send_personal_message(message, user_id, "user")
            elif admin_id:
                await manager.send_personal_message(message, admin_id, "admin")
        except Exception as e:
            print(f"Failed to emit event {event_type}: {str(e)}")  # Error log

    if background_tasks:
        background_tasks.add_task(send_notification)
    else:
        await send_notification()
