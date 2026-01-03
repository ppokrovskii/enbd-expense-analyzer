# Category Domain

**Module**: `app/domains/categories/`  
**Routes**: `/categories/*`, `/rules/*`

---

## Responsibility

Rules engine, **LLM generates rules** (not categories), batch recategorization

---

## Key APIs

```
GET  /categories             → List categories
POST /rules                  → Create rule
POST /rules/recategorize     → Background job
POST /ai-recategorize        → LLM generates rules for unmatched merchants
```

---

## Database

```sql
categories (id, person_id, name, color)
rules (id, person_id, category_id, field, operator, value, priority)
accounts (id, person_id, account_number, account_name)  -- For {variables}
```

---

## How It Works

**Phase 1: Rules (Fast)**
```python
# Apply rules by priority, support {variables}
if "starbucks" in merchant_details:
    return "Food & Dining"
```

**Phase 2: LLM Generates Rules for New Merchants**
```python
# LLM returns: {category, keywords[], exclude_keywords[], confidence}
rule = await llm.generate_rule(merchant, details)
# Save rule, apply to all transactions with that merchant
```

**Batch Processing**
```python
# Group by merchant → Apply rules → For unmatched: Generate rule → Save → Apply
```

---

## Variable Substitution

```python
"Transfer to {own_account_number}" → "Transfer to 1234567890"
```

---

## Recategorization

```python
# Background task with WebSocket progress
async def recategorize_all(person_id):
    for txn in transactions:
        txn.category = apply_rules(txn)
        if progress % 10 == 0:
            notify_progress()
```

---

**Dependencies**: PostgreSQL, Redis (cache), OpenAI (GPT-5.2)  
**Status**: Ready
