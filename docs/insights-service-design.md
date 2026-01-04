# AI Insights Service - Solution Design

**Service**: Trends & Anomalies Detection (Hybrid)  
**Port**: 8007  
**Repository**: `services/insights-service/`

---

## Responsibility

- Detect spending trends (increases, decreases)
- Identify anomalies (spikes, unusual transactions)
- Generate natural language insights (3-5 bullets)
- Hybrid approach: Algorithm + LLM validation

---

## API Endpoints

```
POST /insights/trends
  Body: {
    person_id: string,
    date_from: string,
    date_to: string,
    compare_to?: { date_from, date_to }  # Optional comparison period
  }
  Returns: {
    trends: [string],  # Max 5 bullets
    anomalies: [Anomaly],
    generated_at: string
  }

POST /insights/summary
  Body: { person_id, date_from, date_to }
  Returns: {
    summary: string,  # 2-3 sentence takeaway
    generated_at: string
  }

POST /insights/key-insights
  Body: { person_id, date_from, date_to, categories_data }
  Returns: {
    insights: [string],  # 3-5 bullets, no advice
    generated_at: string
  }
```

---

## Data Model

### Anomaly (response)
```typescript
interface Anomaly {
  type: "spike" | "unusual_merchant" | "large_transaction";
  transaction_id: string;
  description: string;
  amount: number;
  date: string;
  severity: "low" | "medium" | "high";
}
```

---

## Hybrid Algorithm + LLM

### Phase 1: Algorithmic Detection (Fast, Free)

```python
import numpy as np
from scipy import stats

async def detect_trends_algorithmic(
    person_id: str,
    date_from: str,
    date_to: str,
    compare_to: Optional[dict] = None
) -> dict:
    """
    Use statistical analysis:
    1. Compare spending by category (current vs previous period)
    2. Calculate z-scores for anomaly detection
    3. Identify spending spikes (>2 std dev)
    4. Find unusual merchants (never seen before)
    """
    
    # Get transactions
    current = await get_transactions(person_id, date_from, date_to)
    
    # Category spending comparison
    trends = []
    if compare_to:
        previous = await get_transactions(person_id, compare_to["date_from"], compare_to["date_to"])
        trends = compare_spending(current, previous)
    
    # Anomaly detection
    anomalies = detect_anomalies(current)
    
    return {
        "trends": trends,
        "anomalies": anomalies,
        "confidence": 0.85  # Algorithm confidence
    }

def compare_spending(current: pd.DataFrame, previous: pd.DataFrame) -> List[str]:
    """Compare spending between periods"""
    
    results = []
    
    # By category
    curr_cat = current.groupby('category')['amount_signed'].sum().abs()
    prev_cat = previous.groupby('category')['amount_signed'].sum().abs()
    
    for category in curr_cat.index:
        if category not in prev_cat.index:
            continue
        
        change_pct = ((curr_cat[category] - prev_cat[category]) / prev_cat[category]) * 100
        
        if abs(change_pct) > 20:  # Significant change
            direction = "increased" if change_pct > 0 else "decreased"
            results.append({
                "type": "category_change",
                "category": category,
                "change_pct": change_pct,
                "direction": direction
            })
    
    # Overall spending
    curr_total = curr_cat.sum()
    prev_total = prev_cat.sum()
    overall_change = ((curr_total - prev_total) / prev_total) * 100
    
    if abs(overall_change) > 10:
        results.append({
            "type": "overall_change",
            "change_pct": overall_change,
            "direction": "increased" if overall_change > 0 else "decreased"
        })
    
    return results

def detect_anomalies(transactions: pd.DataFrame) -> List[dict]:
    """Detect anomalies using statistical methods"""
    
    anomalies = []
    
    # Z-score for large transactions
    amounts = transactions['amount_signed'].abs()
    z_scores = np.abs(stats.zscore(amounts))
    
    # Transactions > 2 standard deviations
    outliers = transactions[z_scores > 2]
    
    for _, txn in outliers.iterrows():
        anomalies.append({
            "type": "large_transaction",
            "transaction_id": txn['id'],
            "amount": txn['amount_signed'],
            "merchant": txn['merchant'],
            "date": txn['date'].isoformat(),
            "severity": "high" if z_scores[txn.name] > 3 else "medium"
        })
    
    # Unusual merchants (appeared only once)
    merchant_counts = transactions['merchant'].value_counts()
    unique_merchants = merchant_counts[merchant_counts == 1].index
    
    for merchant in unique_merchants[:5]:  # Max 5
        txn = transactions[transactions['merchant'] == merchant].iloc[0]
        anomalies.append({
            "type": "unusual_merchant",
            "transaction_id": txn['id'],
            "merchant": merchant,
            "amount": txn['amount_signed'],
            "date": txn['date'].isoformat(),
            "severity": "low"
        })
    
    return anomalies
```

### Phase 2: LLM for Natural Language (Only for Generation)

```python
async def generate_trend_insights(
    algorithmic_results: dict,
    person_id: str,
    date_from: str,
    date_to: str
) -> List[str]:
    """
    Use LLM ONLY to convert algorithmic findings to natural language
    Input: Structured data from algorithm
    Output: 3-5 readable bullets
    """
    
    trends_data = json.dumps(algorithmic_results["trends"], indent=2)
    anomalies_data = json.dumps(algorithmic_results["anomalies"][:3], indent=2)  # Top 3
    
    prompt = f"""
Convert these spending analysis findings into 3-5 clear, concise bullet points.
Use natural language. Do NOT give advice, only state facts.

TRENDS:
{trends_data}

ANOMALIES:
{anomalies_data}

Example format:
• Spending spike in December (+45% vs November)
• Coffee spending increased by 30%
• Large one-off purchase: Furniture (3,500 AED)

Respond with JSON array:
["bullet 1", "bullet 2", ...]
"""
    
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=300
    )
    
    result = json.loads(response.choices[0].message.content)
    return result["insights"][:5]  # Max 5
```

### Generate Summary Takeaway

```python
async def generate_summary(
    person_id: str,
    date_from: str,
    date_to: str,
    total_income: float,
    total_expenses: float,
    net_balance: float
) -> str:
    """
    Generate 2-3 sentence summary for report Section 1
    """
    
    prompt = f"""
Write a 2-3 sentence summary for a financial report based on these facts:

Period: {date_from} to {date_to}
Income: {total_income} AED
Expenses: {total_expenses} AED
Net Balance: {net_balance} AED

Use natural, conversational language. Be concise. NO advice, just summary.

Example:
"You earned 45,540 AED and spent 23,456 AED during this period, resulting in a positive balance of 22,084 AED. Your spending was well-controlled, with most expenses going toward essentials like groceries and transportation."
"""
    
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )
    
    return response.choices[0].message.content
```

---

## Cost Optimization

### Strategy
- **100% detection via algorithm** (free, fast)
- **LLM only for language generation** (minimal tokens)
- No LLM for analysis/detection

### Cost Comparison
```
Pure LLM Approach:
- Analyze 500 transactions → 10,000 tokens
- Cost: ~$0.0015 per report

Hybrid Approach:
- Algorithm analyzes 500 transactions → 0 tokens
- LLM generates 5 bullets → 300 tokens
- Cost: ~$0.00005 per report

Savings: 97% reduction
```

---

## Dependencies

### Internal
- Transaction Service

### External
- OpenAI API (generation only)
- Redis (cache insights)

---

## Technology

- **Framework**: FastAPI
- **Stats**: NumPy, SciPy, Pandas
- **LLM**: OpenAI SDK
- **Cache**: Redis

---

## Testing

```python
def test_algorithmic_detection():
    transactions = pd.DataFrame([
        {"date": "2025-01-01", "merchant": "Coffee", "amount_signed": -25, "category": "Food"},
        {"date": "2025-01-05", "merchant": "Furniture", "amount_signed": -3500, "category": "Shopping"},  # Anomaly
        {"date": "2025-01-10", "merchant": "Coffee", "amount_signed": -30, "category": "Food"},
    ])
    
    anomalies = detect_anomalies(transactions)
    
    assert len(anomalies) > 0
    assert any(a["type"] == "large_transaction" for a in anomalies)
    assert any(a["merchant"] == "Furniture" for a in anomalies)

@pytest.mark.asyncio
async def test_trend_comparison():
    current = pd.DataFrame([...])  # Dec 2025
    previous = pd.DataFrame([...])  # Nov 2025
    
    trends = compare_spending(current, previous)
    
    assert any(t["type"] == "overall_change" for t in trends)
```

---

## Monitoring

- Processing time per 100 transactions
- LLM token usage (should be <500 per report)
- Cache hit rate
- Insight generation success rate

---

**Status**: Ready for implementation  
**Owner**: ML/Analytics Team  
**Dependencies**: Transaction Service, OpenAI

