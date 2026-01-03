# Transaction Domain

**Module**: `app/domains/transactions/`  
**Routes**: `/transactions/*`

---

## Responsibility

Import XLSX files, deduplicate, query transactions, multi-bank support

---

## Key APIs

```
POST /transactions/import     → Upload XLSX, parse, dedupe, insert
GET  /transactions            → List (filter by date, category, merchant)
GET  /transactions/summary    → Total income/expenses/balance
```

---

## Database

```sql
transactions (
  id, person_id, hash, date, merchant, details, description,
  amount_debit, amount_credit, amount_signed, category, account, bank
)
INDEX: (person_id, date), (hash)
```

---

## Multi-Bank Parsers

```python
class ENBDParser(BankParser):
    def parse(file) -> DataFrame:
        # Map ENBD columns → standard format
        return DataFrame({date, merchant, details, amount_signed, ...})

class FABParser(BankParser):
    def parse(file) -> DataFrame:
        # FAB-specific column mapping
        ...

ParserFactory.get_parser(bank)  # Returns appropriate parser
```

---

## Deduplication

```python
hash = sha256(f"{date}|{merchant}|{amount}".encode()).hexdigest()
# Check existing hashes, insert only new transactions
```

---

## Freemium Enforcement

```python
if user.subscription_tier == "free" and count >= 1000:
    raise HTTPException(402, "Upgrade to premium")
```

---

**Dependencies**: PostgreSQL  
**Status**: Ready
