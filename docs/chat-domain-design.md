# Chat Domain

**Module**: `app/domains/chat/`  
**Routes**: `/chat/*`

---

## Responsibility

AI assistant with tool calling, context injection (1000 transactions)

---

## Key APIs

```
GET  /chat/sessions                  → List sessions
POST /chat/sessions/{id}/messages    → Send message, get AI response
```

---

## Database

```sql
chat_sessions (id, person_id, title, total_tokens, total_cost_usd)
chat_messages (id, session_id, role, content, tool_calls, prompt_tokens)
```

---

## AI Agent with Tools

```python
TOOLS = [
    "get_transactions",      # Query transactions
    "get_spending_summary",  # By category
    "search_transactions"    # Text search
]

# Direct function calls (no HTTP)
result = await transaction_service.get_transactions(person_id, **args)
```

---

## Context Injection

```python
# First message: Inject 1000 recent transactions + categories
context = f"""
CATEGORIES: {', '.join(categories)}
TRANSACTIONS (last 1000):
{'\n'.join([f"{t.date}: {t.merchant} - {t.category} - {t.amount} AED" for t in txns])}
"""
```

---

## Token Display

```typescript
// Frontend
<div>Session: {session.total_tokens} tokens (${session.total_cost_usd})</div>
```

---

**Dependencies**: Transaction Domain, Category Domain, OpenAI (GPT-5.2)  
**Status**: Ready
