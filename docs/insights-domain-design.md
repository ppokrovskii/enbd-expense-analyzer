# AI Insights Domain

**Module**: `app/domains/insights/`  
**Routes**: Internal (called by Report domain)

---

## Responsibility

Trends, anomalies (hybrid: algo calculates, LLM generates language)

---

## API

```python
async def generate_insights(person_id, date_from, date_to) -> dict:
    return {
        "trends": ["Spending increased 45%", ...],  # Max 5
        "anomalies": [Anomaly(...), ...],
        "summary": "2-3 sentence takeaway"
    }
```

---

## Hybrid Approach

**Phase 1: Statistical Analysis (Free)**
```python
# Calculate z-scores for anomalies
outliers = transactions[z_scores > 2]  # >2 std dev

# Compare periods
change_pct = (current - previous) / previous * 100

# Result: Structured data (category changes, outliers, etc.)
```

**Phase 2: LLM for Language (Cheap)**
```python
# Convert structured data → natural language
prompt = f"Convert these findings to 5 bullets: {json.dumps(algo_results)}"
insights = await llm.generate(prompt)  # Max 300 tokens
# Returns: ["Spending spike in December (+45%)", ...]
```

---

## Anomaly Types

```typescript
interface Anomaly {
  type: "spike" | "unusual_merchant" | "large_transaction";
  transaction_id: string;
  description: string;
  severity: "low" | "medium" | "high";
}
```

---

## Cost

Algorithm does 100% analysis, LLM only generates text → 95%+ cheaper

---

**Dependencies**: Transaction Domain, OpenAI (GPT-5.2), NumPy, SciPy, Pandas  
**Status**: Ready
