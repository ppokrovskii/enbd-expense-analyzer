# Notification Service - Solution Design

**Service**: Real-time Notifications & WebSocket Management  
**Port**: 8009  
**Repository**: `services/notification-service/`

---

## Responsibility

- WebSocket connection management
- Real-time notifications to frontend
- Subscribe/unsubscribe to person-specific channels
- Broadcast events (recategorization progress, reports ready)

---

## API Endpoints

### WebSocket
```
WS /ws?token={jwt_token}
  - Authenticate user via JWT
  - Subscribe to user's active person channel
  - Receive real-time notifications
  - Handle reconnections
```

### HTTP (for testing/manual triggers)
```
POST /notify
  Body: {
    person_id: string,
    type: string,
    data: object
  }
  Returns: { sent: true, connections: number }

GET /health
  Returns: { status: "healthy", connections: number }
```

---

## WebSocket Protocol

### Client → Server Messages
```json
// Authenticate (sent immediately after connection)
{
  "type": "auth",
  "token": "jwt_token_here"
}

// Switch person context
{
  "type": "subscribe",
  "person_id": "uuid"
}

// Heartbeat (keep-alive)
{
  "type": "ping"
}
```

### Server → Client Messages
```json
// Authentication success
{
  "type": "auth_success",
  "user_id": "uuid",
  "person_id": "uuid"
}

// Authentication failure
{
  "type": "auth_error",
  "message": "Invalid token"
}

// Notification
{
  "type": "notification",
  "event": "recategorization.started",
  "data": {
    "job_id": "uuid"
  }
}

// Heartbeat response
{
  "type": "pong"
}
```

---

## Notification Types

### Recategorization
```json
// Started
{
  "type": "notification",
  "event": "recategorization.started",
  "data": { "job_id": "uuid" }
}

// Progress (every 10%)
{
  "type": "notification",
  "event": "recategorization.progress",
  "data": {
    "job_id": "uuid",
    "processed": 450,
    "total": 1000,
    "percentage": 45
  }
}

// Completed
{
  "type": "notification",
  "event": "recategorization.completed",
  "data": {
    "job_id": "uuid",
    "processed": 1000,
    "total": 1000
  }
}
```

### Reports
```json
{
  "type": "notification",
  "event": "report.generated",
  "data": {
    "report_id": "uuid",
    "pdf_url": "https://...",
    "status": "completed"
  }
}
```

### Transactions
```json
{
  "type": "notification",
  "event": "transactions.imported",
  "data": {
    "imported": 123,
    "duplicates": 5
  }
}
```

---

## Implementation

### Connection Manager
```python
from fastapi import WebSocket
from typing import Dict, Set
import jwt

class ConnectionManager:
    def __init__(self):
        # person_id → set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, person_id: str):
        """Add connection to person's channel"""
        await websocket.accept()
        
        if person_id not in self.active_connections:
            self.active_connections[person_id] = set()
        
        self.active_connections[person_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, person_id: str):
        """Remove connection"""
        if person_id in self.active_connections:
            self.active_connections[person_id].discard(websocket)
            
            # Clean up empty channels
            if not self.active_connections[person_id]:
                del self.active_connections[person_id]
    
    async def send_to_person(self, person_id: str, message: dict):
        """Send message to all connections for a person"""
        if person_id not in self.active_connections:
            return
        
        # Broadcast to all connections
        disconnected = []
        for connection in self.active_connections[person_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn, person_id)
    
    def get_connection_count(self) -> int:
        """Total active connections"""
        return sum(len(conns) for conns in self.active_connections.values())

manager = ConnectionManager()
```

### WebSocket Endpoint
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """Handle WebSocket connections"""
    
    person_id = None
    
    try:
        # Wait for auth message
        await websocket.accept()
        
        # Receive auth message
        auth_msg = await websocket.receive_json()
        
        if auth_msg["type"] != "auth":
            await websocket.send_json({
                "type": "auth_error",
                "message": "Authentication required"
            })
            await websocket.close()
            return
        
        # Verify JWT
        try:
            payload = jwt.decode(
                auth_msg["token"],
                JWT_SECRET,
                algorithms=["HS256"]
            )
            user_id = payload["user_id"]
            person_id = payload["person_id"]
        except jwt.InvalidTokenError:
            await websocket.send_json({
                "type": "auth_error",
                "message": "Invalid token"
            })
            await websocket.close()
            return
        
        # Connect
        await manager.connect(websocket, person_id)
        
        await websocket.send_json({
            "type": "auth_success",
            "user_id": user_id,
            "person_id": person_id
        })
        
        # Listen for messages
        while True:
            message = await websocket.receive_json()
            
            if message["type"] == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif message["type"] == "subscribe":
                # Switch to different person
                new_person_id = message["person_id"]
                manager.disconnect(websocket, person_id)
                person_id = new_person_id
                await manager.connect(websocket, person_id)
    
    except WebSocketDisconnect:
        if person_id:
            manager.disconnect(websocket, person_id)
    
    except Exception as e:
        if person_id:
            manager.disconnect(websocket, person_id)
```

---

## Event Bus Integration

```python
import aio_pika

async def consume_events():
    """Consume events from RabbitMQ and broadcast to WebSockets"""
    
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    
    # Declare exchange
    exchange = await channel.declare_exchange(
        "notifications",
        aio_pika.ExchangeType.TOPIC
    )
    
    # Create queue
    queue = await channel.declare_queue("notification_service", durable=True)
    
    # Bind to relevant events
    await queue.bind(exchange, "recategorization.*")
    await queue.bind(exchange, "report.*")
    await queue.bind(exchange, "transactions.imported")
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                event = json.loads(message.body)
                
                # Extract person_id from event
                person_id = event.get("person_id")
                
                if person_id:
                    # Broadcast to all connections for this person
                    await manager.send_to_person(person_id, {
                        "type": "notification",
                        "event": event["event"],
                        "data": event
                    })

# Start consumer on app startup
@app.on_event("startup")
async def startup():
    asyncio.create_task(consume_events())
```

---

## Frontend Integration

### React Hook
```typescript
// useNotifications.ts
import { useEffect, useState } from 'react';
import useWebSocket from 'react-use-websocket';

export function useNotifications(token: string) {
  const [notifications, setNotifications] = useState<any[]>([]);
  
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    `ws://localhost:8009/ws`,
    {
      onOpen: () => {
        // Authenticate
        sendMessage(JSON.stringify({
          type: "auth",
          token: token
        }));
      },
      shouldReconnect: () => true,
      reconnectInterval: 3000
    }
  );
  
  useEffect(() => {
    if (lastMessage) {
      const message = JSON.parse(lastMessage.data);
      
      if (message.type === "notification") {
        setNotifications(prev => [...prev, message]);
        
        // Show toast
        toast.info(formatNotification(message));
      }
    }
  }, [lastMessage]);
  
  return { notifications, readyState };
}
```

### Usage in Component
```typescript
function Dashboard() {
  const { token } = useAuth();
  const { notifications } = useNotifications(token);
  
  useEffect(() => {
    notifications.forEach(notif => {
      if (notif.event === "recategorization.completed") {
        // Refresh transactions
        mutate('/api/transactions');
      }
    });
  }, [notifications]);
  
  return <div>...</div>;
}
```

---

## Dependencies

### Internal
- None (receives events from all services)

### External
- RabbitMQ (event bus)
- Redis (optional: connection state persistence)

---

## Technology

- **Framework**: FastAPI
- **WebSocket**: FastAPI WebSocket support
- **Event Bus**: aio-pika (RabbitMQ)
- **JWT**: PyJWT

---

## Testing

```python
from fastapi.testclient import TestClient

def test_websocket_auth():
    client = TestClient(app)
    
    with client.websocket_connect(f"/ws") as websocket:
        # Send auth
        websocket.send_json({
            "type": "auth",
            "token": "valid_jwt_token"
        })
        
        # Receive success
        response = websocket.receive_json()
        assert response["type"] == "auth_success"

def test_broadcast_notification():
    # Connect 2 clients for same person
    with client.websocket_connect("/ws") as ws1, \
         client.websocket_connect("/ws") as ws2:
        
        # Auth both
        ws1.send_json({"type": "auth", "token": token})
        ws2.send_json({"type": "auth", "token": token})
        
        # Send notification
        await manager.send_to_person(person_id, {
            "type": "notification",
            "event": "test.event"
        })
        
        # Both should receive
        msg1 = ws1.receive_json()
        msg2 = ws2.receive_json()
        
        assert msg1["event"] == "test.event"
        assert msg2["event"] == "test.event"
```

---

## Monitoring

- Active WebSocket connections
- Messages sent per second
- Connection duration average
- Reconnection rate

---

**Status**: Ready for implementation  
**Owner**: Backend Team  
**Dependencies**: RabbitMQ

