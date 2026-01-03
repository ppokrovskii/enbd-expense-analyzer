# Auth Domain

**Module**: `app/domains/auth/`  
**Routes**: `/auth/*`, `/persons/*`

---

## Responsibility

Auth0 integration, person management, session handling

---

## Key APIs

```
GET  /auth/login              → Redirect to Auth0
GET  /auth/callback?code=...  → Exchange code for token
GET  /auth/me                 → Current user + active person
POST /persons                 → Create person
PUT  /persons/{id}/activate   → Switch context
```

---

## Database

```sql
users (id, auth0_user_id, email, name, subscription_tier, active_person_id)
persons (id, owner_user_id, name)
user_settings (user_id, preferred_llm_model DEFAULT 'gpt-5.2')
```

---

## Auth0 Setup

```typescript
// Verify token middleware
async function verify_token(token: str) -> dict:
    payload = jwt.decode(token, auth0_public_key, algorithms=["RS256"])
    return payload  # {sub: auth0_user_id, email, name}
```

---

## Person Switching

```python
# Update active_person_id
await db.execute("UPDATE users SET active_person_id = ? WHERE id = ?")

# All queries scoped by person_id
transactions = await db.query("SELECT * FROM transactions WHERE person_id = ?")
```

---

## Environment

```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_AUDIENCE=https://api.enbd-analyzer.com
```

---

**Dependencies**: Auth0, PostgreSQL  
**Status**: Ready
