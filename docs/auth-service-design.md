# Auth Service - Solution Design

**Service**: Authentication & User Management  
**Port**: 8001  
**Repository**: `services/auth-service/`

---

## Responsibility

- User registration & authentication (Google OAuth + email/password)
- Person management (multi-person data isolation)
- JWT token generation & validation
- Session management
- Context switching (active person)

---

## API Endpoints

### Authentication
```
POST /auth/register
  Body: { email, password, name }
  Returns: { access_token, user }

POST /auth/login
  Body: { email, password }
  Returns: { access_token, user }

POST /auth/google
  Body: { google_token }
  Returns: { access_token, user }

GET /auth/me
  Headers: Authorization: Bearer {token}
  Returns: { user, active_person }

POST /auth/logout
  Headers: Authorization: Bearer {token}
  Returns: { success: true }

GET /auth/validate-token
  Headers: Authorization: Bearer {token}
  Returns: { valid: true, user_id, person_id }
```

### Person Management
```
GET /persons
  Returns: [{ id, name, created_at }]

POST /persons
  Body: { name }
  Returns: { id, name, created_at }

PUT /persons/{id}/activate
  Returns: { success: true, active_person_id }

DELETE /persons/{id}
  Returns: { success: true, deleted_data_count }
```

---

## Data Model

### users
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255),  -- NULL for OAuth
  picture_url TEXT,
  auth_provider VARCHAR(20),  -- 'google' | 'email'
  subscription_tier VARCHAR(20) DEFAULT 'free',  -- 'free' | 'premium'
  transaction_count INTEGER DEFAULT 0,
  transaction_limit INTEGER DEFAULT 1000,  -- NULL for premium
  stripe_customer_id VARCHAR(255),
  stripe_subscription_id VARCHAR(255),
  active_person_id UUID,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP,
  
  INDEX idx_email (email),
  INDEX idx_active_person (active_person_id)
);
```

### persons
```sql
CREATE TABLE persons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_owner (owner_user_id)
);
```

### sessions (optional - for server-side session management)
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_token (token_hash),
  INDEX idx_user (user_id)
);
```

---

## Dependencies

### External
- Google OAuth API
- PostgreSQL (auth schema)
- Redis (token blacklist, rate limiting)

### Internal
- Event Bus (publishes events)

---

## Events Published

```python
# User registered
{
  "event": "user.created",
  "user_id": "uuid",
  "email": "user@example.com",
  "subscription_tier": "free"
}

# User logged in
{
  "event": "user.logged_in",
  "user_id": "uuid",
  "person_id": "uuid"
}

# Person created
{
  "event": "person.created",
  "person_id": "uuid",
  "owner_user_id": "uuid",
  "name": "Sarah"
}

# Person switched
{
  "event": "person.switched",
  "user_id": "uuid",
  "old_person_id": "uuid",
  "new_person_id": "uuid"
}

# Person deleted
{
  "event": "person.deleted",
  "person_id": "uuid",
  "owner_user_id": "uuid"
}
```

---

## Key Flows

### User Registration
```
1. POST /auth/register
2. Validate email uniqueness
3. Hash password (bcrypt)
4. Create user record
5. Create default person (user's name)
6. Set active_person_id
7. Publish: user.created
8. Publish: person.created
9. Generate JWT token
10. Return token + user info
```

### Google OAuth
```
1. POST /auth/google with token
2. Verify token with Google API
3. Check if user exists (by email)
4. If new: Create user + default person
5. If existing: Update last_login
6. Generate JWT token
7. Return token + user info
```

### Person Context Switching
```
1. PUT /persons/{id}/activate
2. Verify person belongs to user
3. Update user.active_person_id
4. Publish: person.switched
5. Return success
```

---

## Implementation Details

### JWT Token Structure
```python
{
  "user_id": "uuid",
  "person_id": "uuid",  # Active person
  "email": "user@example.com",
  "sub_tier": "free",  # Subscription tier
  "exp": 1234567890,  # Expiration
  "iat": 1234567890   # Issued at
}
```

### Password Hashing
```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), hash.encode())
```

### Google OAuth Verification
```python
from google.oauth2 import id_token
from google.auth.transport import requests

def verify_google_token(token: str) -> dict:
    idinfo = id_token.verify_oauth2_token(
        token, 
        requests.Request(), 
        GOOGLE_CLIENT_ID
    )
    return {
        "email": idinfo["email"],
        "name": idinfo["name"],
        "picture": idinfo["picture"]
    }
```

---

## Technology

- **Framework**: FastAPI
- **Database**: PostgreSQL (auth schema)
- **Cache**: Redis (token blacklist)
- **Auth Library**: PyJWT, bcrypt, google-auth
- **Event Bus**: aio-pika (RabbitMQ)

---

## Testing

### Unit Tests
```python
def test_register_user():
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "secure123",
        "name": "Test User"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_create_person():
    response = client.post("/persons", json={"name": "Sarah"})
    assert response.status_code == 200
    assert response.json()["name"] == "Sarah"
```

### Integration Tests
```python
def test_full_auth_flow():
    # Register
    register = client.post("/auth/register", json=...)
    token = register.json()["access_token"]
    
    # Create person
    person = client.post("/persons", 
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Sarah"}
    )
    
    # Switch context
    switch = client.put(f"/persons/{person.json()['id']}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert switch.status_code == 200
```

---

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
RUN uv sync

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Environment Variables
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
RABBITMQ_URL=amqp://...
```

---

## Monitoring

### Health Check
```
GET /health
Returns: { 
  status: "healthy",
  database: "connected",
  redis: "connected",
  uptime_seconds: 12345
}
```

### Metrics
- Request latency (p50, p95, p99)
- Auth success/failure rate
- Active sessions count
- Token validation rate

---

**Status**: Ready for implementation  
**Owner**: Auth Team  
**Dependencies**: PostgreSQL, Redis, RabbitMQ



