from typing import Dict, Set
from fastapi import WebSocket
from app.core.auth import jwt, SECRET_KEY, ALGORITHM
import json
from app.core.rate_limiter import get_redis_client
from datetime import datetime, timezone


class ConnectionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_connections = {"user": {}, "admin": {}}
        return cls._instance

    async def connect(self, websocket: WebSocket, token: str, connection_type: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            entity_id = int(payload.get("sub"))

            await websocket.accept()

            if connection_type not in self.active_connections:
                self.active_connections[connection_type] = {}

            if entity_id not in self.active_connections[connection_type]:
                self.active_connections[connection_type][entity_id] = set()

            self.active_connections[connection_type][entity_id].add(websocket)

            await websocket.send_json(
                {
                    "type": "connection_status",
                    "data": {"status": "connected", "entity_id": entity_id},
                    "timestamp": str(datetime.now(timezone.utc)),
                }
            )

            return entity_id
        except Exception as e:
            print(f"Connection error: {str(e)}")
            if not websocket.client_state.disconnected:
                await websocket.close(code=4001)
            return None

    async def send_personal_message(
        self, message: dict, entity_id: int, connection_type: str
    ):

        try:
            if (
                connection_type in self.active_connections
                and entity_id in self.active_connections[connection_type]
            ):
                connections = self.active_connections[connection_type][entity_id]
                dead_connections = set()

                for connection in connections:
                    try:
                        await connection.send_json(message)

                    except Exception as e:
                        print(f"Error sending to connection: {str(e)}")
                        dead_connections.add(connection)

                # Remove dead connections
                for dead in dead_connections:
                    connections.remove(dead)
                    print(f"Removed dead connection for {connection_type} {entity_id}")
            else:
                print(f"No active connections found for {connection_type} {entity_id}")
        except Exception as e:
            print(f"Error in send_personal_message: {str(e)}")

    async def broadcast(self, message: dict):
        for connection_type in self.active_connections:
            for entity_id, connections in self.active_connections[
                connection_type
            ].items():
                for connection in connections.copy():
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        print(
                            f"Broadcast error to {connection_type} {entity_id}: {str(e)}"
                        )
                        connections.remove(connection)

    async def publish_event(self, event_type: str, data: dict):
        message = {
            "type": event_type,
            "data": data,
            "timestamp": str(datetime.now(timezone.utc)),
        }
        await self.redis.publish("banking_events", json.dumps(message))

    async def disconnect(
        self, websocket: WebSocket, entity_id: int, connection_type: str
    ):
        """Disconnect a WebSocket connection and remove it from active connections."""
        try:
            if (
                connection_type in self.active_connections
                and entity_id in self.active_connections[connection_type]
            ):
                self.active_connections[connection_type][entity_id].remove(websocket)

                # Clean up empty sets
                if not self.active_connections[connection_type][entity_id]:
                    del self.active_connections[connection_type][entity_id]
        except Exception as e:
            print(f"Error in disconnect: {str(e)}")
