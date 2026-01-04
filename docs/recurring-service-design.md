# Recurring Detection Service - Solution Design

**Service**: Recurring Transaction Detection  
**Port**: 8006  
**Repository**: `services/recurring-service/`

---

## Responsibility

- Detect recurring patterns in transactions (hybrid algorithm + LLM)
- Group recurring transactions
- Calculate estimated amounts & frequencies
- Flag "forgotten" subscriptions (>60 days inactive)

---

## API Endpoints

```
POST /recurring/detect
  Body: {
    person_id: string,
    date_from: string,
    date_to: string,
    min_occurrences?: number  # Default: 2
  }
  Returns: [RecurringGroup]

GET /recurring/groups?person_id=...
  Returns: [RecurringGroup]

GET /recurring/groups/{id}
  Returns: RecurringGroup with transaction list
```

---

## Data Model

### RecurringGroup (response)
```typescript
interface RecurringGroup {
  id: string;
  person_id: string;
  pattern_name: string;  // "Netflix", "Gym Membership"
  merchant: string;
  estimated_amount: number;
  frequency: "weekly" | "monthly" | "quarterly" | "yearly";
  occurrences: number;
  last_seen_date: string;
  forgotten: boolean;  // true if >60 days since last_seen
  transactions: Transaction[];  // IDs only in list, full in detail view
}
```

---

## Hybrid Algorithm + LLM Approach

### Phase 1: Deterministic Pattern Detection (Fast, Cheap)

```python
import pandas as pd
from fuzzywuzzy import fuzz
from datetime import datetime, timedelta

def detect_recurring_patterns(transactions: pd.DataFrame) -> List[RecurringGroup]:
    """
    Algorithmic detection:
    1. Group by merchant (fuzzy matching)
    2. Calculate date intervals
    3. Detect consistent patterns (±3 days tolerance)
    4. Filter: 2+ occurrences, similar amounts (±10%)
    """
    
    # Fuzzy merchant grouping
    merchant_groups = fuzzy_group_by_merchant(transactions, threshold=85)
    
    recurring_groups = []
    for merchant, txns in merchant_groups.items():
        if len(txns) < 2:
            continue
        
        # Sort by date
        txns = txns.sort_values('date')
        
        # Calculate intervals
        intervals = []
        for i in range(len(txns) - 1):
            days = (txns.iloc[i+1]['date'] - txns.iloc[i]['date']).days
            intervals.append(days)
        
        # Detect pattern
        if is_consistent_interval(intervals, tolerance=3):
            frequency = infer_frequency(intervals)
            
            # Check amount consistency
            amounts = txns['amount'].abs()
            if is_consistent_amount(amounts, tolerance=0.10):
                recurring_groups.append({
                    "merchant": merchant,
                    "frequency": frequency,
                    "occurrences": len(txns),
                    "estimated_amount": amounts.median(),
                    "transaction_ids": txns['id'].tolist(),
                    "last_seen_date": txns['date'].max(),
                    "confidence": calculate_confidence(intervals, amounts)
                })
    
    return recurring_groups

def is_consistent_interval(intervals: List[int], tolerance: int) -> bool:
    """Check if intervals are consistent (±tolerance days)"""
    if not intervals:
        return False
    median_interval = statistics.median(intervals)
    return all(abs(i - median_interval) <= tolerance for i in intervals)

def infer_frequency(intervals: List[int]) -> str:
    """Infer frequency from intervals"""
    median = statistics.median(intervals)
    if 5 <= median <= 9:
        return "weekly"
    elif 28 <= median <= 33:
        return "monthly"
    elif 85 <= median <= 95:
        return "quarterly"
    elif 360 <= median <= 370:
        return "yearly"
    return "irregular"
```

### Phase 2: LLM Validation & Naming (Only for Edge Cases)

```python
async def validate_with_llm(group: dict, transactions: List[Transaction]) -> dict:
    """
    Use LLM only when:
    - Low confidence (<70%)
    - Irregular frequency
    - Need better pattern_name
    """
    
    if group["confidence"] > 0.70 and group["frequency"] != "irregular":
        # High confidence → Skip LLM
        group["pattern_name"] = group["merchant"]
        return group
    
    # Prepare context
    txn_sample = [
        f"{t['date']}: {t['merchant']} - {t['details']} - {t['amount']} AED"
        for t in transactions[:5]  # Max 5 samples
    ]
    
    prompt = f"""
Analyze these transactions to determine if they are recurring:

{chr(10).join(txn_sample)}

Respond in JSON:
{{
  "is_recurring": true/false,
  "pattern_name": "Netflix Subscription",
  "frequency": "monthly",
  "confidence": 0.95,
  "reasoning": "Short explanation"
}}
"""
    
    response = await llm_client.chat(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    
    if result["is_recurring"]:
        group["pattern_name"] = result["pattern_name"]
        group["llm_confidence"] = result["confidence"]
    
    return group
```

---

## Forgotten Subscriptions Detection

```python
def flag_forgotten_subscriptions(groups: List[RecurringGroup]) -> List[RecurringGroup]:
    """
    Flag recurring groups where last_seen_date > 60 days ago
    """
    threshold_date = datetime.now() - timedelta(days=60)
    
    for group in groups:
        if group["last_seen_date"] < threshold_date:
            group["forgotten"] = True
        else:
            group["forgotten"] = False
    
    return groups
```

---

## Dependencies

### External
- PostgreSQL (caching detected groups)
- Redis (LLM response cache)
- OpenAI API (validation only)

### Internal
- Transaction Service (get data)

---

## Cost Optimization

### Strategy
- **90% detection via algorithm** (0 API calls)
- **10% validation via LLM** (only low-confidence cases)
- **Cache LLM responses** (by merchant pattern)

### Example Cost
```
1000 transactions → ~20 recurring groups
Algorithm detects: 18 groups (90%)
LLM validates: 2 groups (10%)

Cost:
- Algorithm: $0
- LLM: 2 calls × $0.001 = $0.002
- Total: $0.002 vs $0.20 (pure LLM)
```

---

## Performance Targets

- Processing time: < 5 seconds for 1000 transactions
- Accuracy: >95% precision, >90% recall
- LLM usage: <10% of groups

---

## Technology

- **Framework**: FastAPI
- **Data**: Pandas, NumPy
- **Fuzzy Matching**: fuzzywuzzy
- **LLM**: OpenAI SDK
- **Cache**: Redis

---

## Testing

```python
def test_detect_monthly_subscription():
    transactions = [
        {"date": "2025-01-01", "merchant": "Netflix", "amount": -49},
        {"date": "2025-02-01", "merchant": "Netflix", "amount": -49},
        {"date": "2025-03-01", "merchant": "Netflix", "amount": -49},
    ]
    
    groups = detect_recurring_patterns(pd.DataFrame(transactions))
    
    assert len(groups) == 1
    assert groups[0]["frequency"] == "monthly"
    assert groups[0]["estimated_amount"] == 49
    assert groups[0]["occurrences"] == 3

def test_forgotten_subscription():
    group = {
        "last_seen_date": datetime.now() - timedelta(days=70)
    }
    
    flagged = flag_forgotten_subscriptions([group])
    assert flagged[0]["forgotten"] is True
```

---

## Monitoring

- Algorithm detection rate (%)
- LLM fallback rate (%)
- Processing time per 100 transactions
- Accuracy metrics (precision/recall)

---

**Status**: Ready for implementation  
**Owner**: ML/Analytics Team  
**Dependencies**: Transaction Service, OpenAI, Redis

