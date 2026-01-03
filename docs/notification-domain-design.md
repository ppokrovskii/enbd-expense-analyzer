# Notification Domain

**Module**: `app/domains/notifications/`  
**Routes**: `/ws` (WebSocket)

---

## Responsibility

WebSocket management, real-time notifications to frontend

---

## WebSocket Protocol

```
Client → Server: {type: "auth", token: "jwt"}
Server → Client: {type: "auth_success", user_id, person_id}

Server → Client: {
  type: "notification",
  event: "recategorization.progress",
  data: {job_id, processed, total}
}
```

---

## Notification Events

```python
# Recategorization
"recategorization.started"
"recategorization.progress"     # Every 10%
"recategorization.completed"

# Reports
"report.generated"              # {report_id, pdf_url}

# Transactions
"transactions.imported"         # {count}
```

---

## Implementation

```python
class ConnectionManager:
    connections: Dict[person_id, Set[WebSocket]]
    
    async def send_to_person(person_id, message):
        for ws in connections[person_id]:
            await ws.send_json(message)

# Direct calls from other domains
from app.domains.notifications import manager
await manager.send_to_person(person_id, {"event": "...", "data": {...}})
```

---

## Frontend Integration

```typescript
wsManager.on('recategorization.completed', (data) => {
  toast.success('Done!');
  mutate('/api/transactions');  // Refresh data
});
```

---

**Dependencies**: Redis (connection state), FastAPI WebSocket  
**Status**: Ready
