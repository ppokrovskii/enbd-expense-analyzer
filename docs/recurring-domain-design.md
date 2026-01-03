# Recurring Detection Domain

**Module**: `app/domains/recurring/`  
**Routes**: Internal (called by Report domain)

---

## Responsibility

Detect recurring transactions (hybrid: algo + LLM), flag "forgotten" (>60 days)

---

## API

```python
async def detect_patterns(person_id, date_from, date_to) -> List[RecurringGroup]
```

---

## Hybrid Approach

**Phase 1: Algorithm (Fast, Free)**
```python
# Group by merchant (fuzzy matching 85%)
# Calculate date intervals
# Check consistency (±3 days tolerance)
# Check amount consistency (±10%)
# Infer frequency: weekly, monthly, quarterly, yearly

if consistent_intervals and consistent_amounts:
    return RecurringGroup(merchant, frequency, estimated_amount, ...)
```

**Phase 2: LLM Validation (Edge Cases Only)**
```python
# Only if confidence < 70% or irregular frequency
llm_result = await llm.validate_pattern(transactions)
# Returns: {is_recurring, pattern_name, frequency, confidence}
```

---

## "Forgotten" Flag

```python
if last_seen_date < (now - 60 days):
    group.forgotten = True  # Yellow/orange highlight
```

---

## Response

```typescript
interface RecurringGroup {
  id: string;
  pattern_name: string;  // "Netflix"
  merchant: string;
  estimated_amount: number;
  frequency: "weekly" | "monthly" | "quarterly" | "yearly";
  occurrences: number;
  last_seen_date: string;
  forgotten: boolean;
}
```

---

## Cost

90% detection via algorithm (free), 10% LLM validation → 97% cheaper than pure LLM

---

**Dependencies**: Transaction Domain, OpenAI (GPT-5.2), Redis  
**Status**: Ready
