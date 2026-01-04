# Category Service - Solution Design

**Service**: Transaction Categorization  
**Port**: 8003  
**Repository**: `services/category-service/`

---

## Responsibility

- Manage categories & rules
- Auto-categorize transactions (rules + LLM fallback)
- Batch recategorization
- Default categories/rules for new users

---

## API Endpoints

### Categories
```
GET /categories?person_id=...
  Returns: [Category]

POST /categories
  Body: { person_id, name, color, parent_id? }
  Returns: Category

PUT /categories/{id}
  Body: { name?, color?, parent_id? }
  Returns: Category

DELETE /categories/{id}
  Returns: { success: true }
```

### Rules
```
GET /rules?person_id=...
  Returns: [Rule]

POST /rules
  Body: {
    person_id, category_id, field, operator, value, priority
  }
  Returns: Rule

PUT /rules/{id}
  Body: { category_id?, value?, priority? }
  Returns: Rule

DELETE /rules/{id}
  Returns: { success: true }

POST /rules/recategorize
  Body: { person_id }
  Returns: { job_id, status: "started" }

GET /rules/recategorize/{job_id}
  Returns: { status, processed, total, completed_at? }
```

### Categorization
```
POST /categorize
  Body: {
    transaction_id: string,
    merchant: string,
    details: string,
    description: string,
    amount: number
  }
  Returns: {
    category: string,
    confidence: number,
    method: "rule" | "llm" | "manual"
  }
```

---

## Data Model

### categories
```sql
CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL,
  name VARCHAR(100) NOT NULL,
  color VARCHAR(7),  -- Hex color
  parent_id UUID REFERENCES categories(id),
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(person_id, name),
  INDEX idx_person (person_id)
);
```

### rules
```sql
CREATE TABLE rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL,
  category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
  field VARCHAR(50) NOT NULL,  -- 'merchant_details', 'amount', 'account'
  operator VARCHAR(20) NOT NULL,  -- 'contains', 'equals', 'starts_with', 'regex'
  value TEXT NOT NULL,  -- Can include variables like {own_account_number}
  priority INTEGER DEFAULT 100,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_person (person_id),
  INDEX idx_priority (priority)
);
```

### accounts (for variable substitution)
```sql
CREATE TABLE accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL,
  account_number VARCHAR(50) NOT NULL,
  account_name VARCHAR(100) NOT NULL,  -- 'own_account_number', 'smart_saver_account'
  bank VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(person_id, account_name),
  INDEX idx_person (person_id)
);
```

### recategorization_jobs
```sql
CREATE TABLE recategorization_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL,
  status VARCHAR(20) DEFAULT 'started',  -- started, processing, completed, failed
  total_transactions INTEGER,
  processed_transactions INTEGER DEFAULT 0,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  
  INDEX idx_person (person_id)
);
```

---

## Categorization Logic

### Phase 1: Rule-Based (Fast, Free)
```python
async def categorize_by_rules(
    person_id: str,
    merchant: str,
    details: str,
    description: str,
    amount: float
) -> Optional[str]:
    """
    Apply rules in priority order (highest first)
    Concatenate merchant + details for matching
    Support variable substitution
    """
    
    # Get person's rules (ordered by priority DESC)
    rules = await get_rules(person_id)
    
    # Get account variables
    accounts = await get_accounts(person_id)
    account_vars = {acc.account_name: acc.account_number for acc in accounts}
    
    # Concatenate fields for matching
    merchant_details = f"{merchant} {details}".lower()
    
    for rule in rules:
        # Substitute variables
        pattern = substitute_variables(rule.value, account_vars)
        
        # Match based on field
        if rule.field == "merchant_details":
            if apply_operator(merchant_details, rule.operator, pattern):
                return rule.category_id
        
        elif rule.field == "amount":
            if apply_operator(str(amount), rule.operator, pattern):
                return rule.category_id
        
        elif rule.field == "account":
            # Check if transaction mentions this account
            if apply_operator(details.lower(), rule.operator, pattern):
                return rule.category_id
    
    return None

def substitute_variables(value: str, vars: dict) -> str:
    """Replace {var_name} with actual values"""
    for var_name, var_value in vars.items():
        value = value.replace(f"{{{var_name}}}", var_value)
    return value

def apply_operator(text: str, operator: str, pattern: str) -> bool:
    if operator == "contains":
        return pattern.lower() in text.lower()
    elif operator == "equals":
        return text.lower() == pattern.lower()
    elif operator == "starts_with":
        return text.lower().startswith(pattern.lower())
    elif operator == "regex":
        return bool(re.search(pattern, text, re.IGNORECASE))
    return False
```

### Phase 2: LLM Fallback (Only if no rule matches)
```python
async def categorize_by_llm(
    merchant: str,
    details: str,
    description: str,
    categories: List[str]
) -> dict:
    """
    Use LLM only when rules don't match
    Cache results by merchant pattern
    """
    
    # Check cache first
    cache_key = f"llm_cat:{merchant.lower()}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Concatenate for context
    full_context = f"{merchant} | {details} | {description}"
    
    prompt = f"""
Categorize this transaction:
{full_context}

Available categories:
{', '.join(categories)}

Respond in JSON:
{{
  "category": "Food & Dining",
  "confidence": 0.95,
  "reasoning": "Coffee shop"
}}
"""
    
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    
    # Cache for 30 days
    await redis.setex(cache_key, 2592000, json.dumps(result))
    
    return result
```

---

## Batch Recategorization

```python
async def recategorize_all(person_id: str) -> str:
    """
    Triggered when rules are updated
    Process in background, send WebSocket notifications
    """
    
    # Create job
    job = await create_job(person_id)
    
    # Run in background
    asyncio.create_task(process_recategorization(job.id, person_id))
    
    return job.id

async def process_recategorization(job_id: str, person_id: str):
    """Background task"""
    
    # Get all transactions
    transactions = await get_all_transactions(person_id)
    total = len(transactions)
    
    await update_job(job_id, status="processing", total=total)
    await send_notification(person_id, "recategorization.started", {"job_id": job_id})
    
    processed = 0
    for txn in transactions:
        # Recategorize
        category = await categorize_by_rules(
            person_id, txn.merchant, txn.details, txn.description, txn.amount
        )
        
        if not category:
            categories = await get_categories(person_id)
            llm_result = await categorize_by_llm(
                txn.merchant, txn.details, txn.description,
                [c.name for c in categories]
            )
            category = llm_result["category"]
        
        await update_transaction_category(txn.id, category)
        
        processed += 1
        
        # Send progress every 10%
        if processed % max(1, total // 10) == 0:
            await send_notification(person_id, "recategorization.progress", {
                "job_id": job_id,
                "processed": processed,
                "total": total
            })
    
    await update_job(job_id, status="completed", processed=total, completed_at=datetime.now())
    await send_notification(person_id, "recategorization.completed", {"job_id": job_id})
```

---

## Default Categories for New Users

```python
DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "color": "#ef4444"},  # Red
    {"name": "Groceries", "color": "#10b981"},  # Green
    {"name": "Transportation", "color": "#3b82f6"},  # Blue
    {"name": "Entertainment", "color": "#a855f7"},  # Purple
    {"name": "Shopping", "color": "#f59e0b"},  # Orange
    {"name": "Bills & Utilities", "color": "#6b7280"},  # Grey
    {"name": "Healthcare", "color": "#ec4899"},  # Pink
    {"name": "Income", "color": "#14b8a6"},  # Teal
    {"name": "Transfers", "color": "#8b5cf6"},  # Violet
    {"name": "Uncategorized", "color": "#9ca3af"}  # Light grey
]

DEFAULT_RULES = [
    {"category": "Food & Dining", "field": "merchant_details", "operator": "contains", "value": "starbucks"},
    {"category": "Food & Dining", "field": "merchant_details", "operator": "contains", "value": "costa"},
    {"category": "Groceries", "field": "merchant_details", "operator": "contains", "value": "carrefour"},
    {"category": "Transportation", "field": "merchant_details", "operator": "contains", "value": "uber"},
    {"category": "Transfers", "field": "merchant_details", "operator": "contains", "value": "transfer to {own_account_number}"},
]

async def initialize_default_data(person_id: str):
    """Called when new person is created"""
    # Create categories
    category_map = {}
    for cat_data in DEFAULT_CATEGORIES:
        cat = await create_category(person_id, cat_data["name"], cat_data["color"])
        category_map[cat_data["name"]] = cat.id
    
    # Create rules
    for rule_data in DEFAULT_RULES:
        await create_rule(
            person_id=person_id,
            category_id=category_map[rule_data["category"]],
            field=rule_data["field"],
            operator=rule_data["operator"],
            value=rule_data["value"]
        )
```

---

## Events Consumed

```python
# From Transaction Service
{
  "event": "transactions.imported",
  "person_id": "uuid",
  "transaction_ids": ["uuid1", "uuid2"]
}
# → Trigger auto-categorization
```

---

## Events Published

```python
{
  "event": "transactions.categorized",
  "transaction_ids": ["uuid1", "uuid2"],
  "category": "Food & Dining"
}

{
  "event": "rules.updated",
  "person_id": "uuid",
  "rule_id": "uuid"
}
# → Potentially trigger recategorization
```

---

## Technology

- **Framework**: FastAPI
- **Database**: PostgreSQL (category schema)
- **Cache**: Redis (LLM responses)
- **LLM**: OpenAI SDK
- **Event Bus**: aio-pika

---

## Testing

```python
def test_rule_matching():
    result = categorize_by_rules(
        person_id="test",
        merchant="Starbucks",
        details="Coffee",
        description="",
        amount=-25.0
    )
    assert result == "food_dining_category_id"

def test_variable_substitution():
    accounts = {"own_account_number": "1234567890"}
    value = "Transfer to {own_account_number}"
    result = substitute_variables(value, accounts)
    assert result == "Transfer to 1234567890"

@pytest.mark.asyncio
async def test_recategorization():
    job_id = await recategorize_all(person_id)
    
    # Wait for completion
    await asyncio.sleep(2)
    
    job = await get_job(job_id)
    assert job.status == "completed"
    assert job.processed == job.total
```

---

## Monitoring

- Rule match rate (%)
- LLM fallback rate (%)
- Recategorization job duration
- Cache hit rate

---

**Status**: Ready for implementation  
**Owner**: Backend Team  
**Dependencies**: Transaction Service, OpenAI, Redis

