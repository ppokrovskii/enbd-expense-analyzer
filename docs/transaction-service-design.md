# Transaction Service - Solution Design

**Service**: Transaction Management  
**Port**: 8002  
**Repository**: `services/transaction-service/`

---

## Responsibility

- Import & parse bank files (XLSX → CSV)
- Hash-based deduplication
- Store transactions in PostgreSQL
- Query & filter transactions
- Support multi-bank parsers (ENBD, FAB, WIO)

---

## API Endpoints

```
POST /transactions/import
  Body: multipart/form-data
    file: Excel file
    person_id: string
    bank: "enbd" | "fab" | "wio"
  Returns: {
    imported: number,
    duplicates: number,
    errors: number,
    transaction_count: number  # Total for person
  }

GET /transactions
  Query: person_id, start_date?, end_date?, 
         category?, account?, merchant?, limit?
  Returns: [Transaction]

GET /transactions/{id}
  Returns: Transaction

PUT /transactions/{id}
  Body: { category?, notes?, merchant? }
  Returns: Transaction

DELETE /transactions/{id}
  Returns: { success: true }

GET /transactions/summary
  Query: person_id, start_date?, end_date?
  Returns: {
    total_income: number,
    total_expenses: number,
    net_balance: number,
    transaction_count: number,
    top_categories: [{name, total, count}]
  }

GET /transactions/merchants
  Query: person_id, search?
  Returns: [string]  # Unique merchant list
```

---

## Data Model

### transactions
```sql
CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL,
  hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 for dedup
  date DATE NOT NULL,
  merchant VARCHAR(255),
  details TEXT,
  description TEXT,
  amount_debit DECIMAL(12,2),
  amount_credit DECIMAL(12,2),
  amount_signed DECIMAL(12,2),  -- Negative for debit
  balance DECIMAL(12,2),
  account VARCHAR(50),
  bank VARCHAR(20) DEFAULT 'enbd',
  category VARCHAR(100),
  category_confidence DECIMAL(3,2),
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_person_date (person_id, date),
  INDEX idx_hash (hash),
  INDEX idx_category (category),
  INDEX idx_merchant (merchant)
);
```

---

## Multi-Bank Support (Pluggable Parsers)

### Parser Interface
```python
from abc import ABC, abstractmethod
import pandas as pd

class BankParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> pd.DataFrame:
        """Parse bank file → standardized DataFrame"""
        pass
    
    @abstractmethod
    def get_bank_name(self) -> str:
        """Return bank identifier"""
        pass
```

### ENBD Parser
```python
class ENBDParser(BankParser):
    def parse(self, file_path: str) -> pd.DataFrame:
        df = pd.read_excel(file_path)
        
        # Map ENBD columns → standard format
        return pd.DataFrame({
            "date": pd.to_datetime(df["Date"], format="%d/%m/%Y"),
            "merchant": df["Merchant"],
            "details": df["Details"],
            "description": df["Description"],
            "amount_debit": df["Debit"],
            "amount_credit": df["Credit"],
            "balance": df["Balance"],
            "account": df["Account"]
        })
    
    def get_bank_name(self) -> str:
        return "enbd"
```

### FAB Parser (Future)
```python
class FABParser(BankParser):
    def parse(self, file_path: str) -> pd.DataFrame:
        df = pd.read_excel(file_path)
        
        # Map FAB columns → standard format
        return pd.DataFrame({
            "date": pd.to_datetime(df["Transaction Date"]),
            "merchant": df["Description"],  # Different column name
            "details": df["Remarks"],
            ...
        })
    
    def get_bank_name(self) -> str:
        return "fab"
```

### Parser Factory
```python
class ParserFactory:
    _parsers = {
        "enbd": ENBDParser(),
        "fab": FABParser(),
        "wio": WIOParser()
    }
    
    @classmethod
    def get_parser(cls, bank: str) -> BankParser:
        if bank not in cls._parsers:
            raise ValueError(f"Unsupported bank: {bank}")
        return cls._parsers[bank]
```

---

## Import Flow

```python
from hashlib import sha256

async def import_transactions(
    file: UploadFile,
    person_id: str,
    bank: str
) -> dict:
    """
    1. Parse file with bank-specific parser
    2. Calculate hash for each transaction
    3. Check for duplicates
    4. Insert new transactions
    5. Publish event for categorization
    """
    
    # Parse file
    parser = ParserFactory.get_parser(bank)
    df = parser.parse(file.filename)
    
    # Calculate hashes
    df["hash"] = df.apply(calculate_hash, axis=1)
    df["person_id"] = person_id
    df["bank"] = bank
    
    # Get existing hashes
    existing_hashes = await get_existing_hashes(person_id)
    
    # Filter new transactions
    new_txns = df[~df["hash"].isin(existing_hashes)]
    
    # Insert to database
    await insert_transactions(new_txns)
    
    # Publish event
    await publish_event({
        "event": "transactions.imported",
        "person_id": person_id,
        "count": len(new_txns),
        "transaction_ids": new_txns["id"].tolist()
    })
    
    return {
        "imported": len(new_txns),
        "duplicates": len(df) - len(new_txns)
    }

def calculate_hash(row: pd.Series) -> str:
    """Hash based on date + merchant + amount"""
    key = f"{row['date']}|{row['merchant']}|{row['amount_signed']}"
    return sha256(key.encode()).hexdigest()
```

---

## Events Published

```python
{
  "event": "transactions.imported",
  "person_id": "uuid",
  "count": 123,
  "transaction_ids": ["uuid1", "uuid2", ...]
}

{
  "event": "transaction.updated",
  "transaction_id": "uuid",
  "person_id": "uuid",
  "field": "category",
  "old_value": "Uncategorized",
  "new_value": "Food & Dining"
}
```

---

## Events Consumed

```python
# From Category Service
{
  "event": "transactions.categorized",
  "transaction_ids": ["uuid1", "uuid2"],
  "category": "Food & Dining",
  "confidence": 0.95
}
```

---

## Freemium Enforcement

```python
async def check_transaction_limit(person_id: str):
    """Check if user exceeds free tier limit"""
    user = await get_user_by_person(person_id)
    
    if user.subscription_tier == "free":
        count = await count_transactions(person_id)
        if count >= user.transaction_limit:  # 1000
            raise HTTPException(
                status_code=402,
                detail="Transaction limit reached. Upgrade to premium."
            )
```

---

## Technology

- **Framework**: FastAPI
- **Data Processing**: Pandas
- **Database**: PostgreSQL (transaction schema)
- **Event Bus**: aio-pika

---

## Testing

```python
def test_enbd_parser():
    parser = ENBDParser()
    df = parser.parse("test_data/enbd_sample.xlsx")
    
    assert "date" in df.columns
    assert "merchant" in df.columns
    assert len(df) > 0

def test_deduplication():
    # Import same file twice
    result1 = await import_transactions(file, person_id, "enbd")
    result2 = await import_transactions(file, person_id, "enbd")
    
    assert result1["imported"] > 0
    assert result2["imported"] == 0
    assert result2["duplicates"] == result1["imported"]

def test_transaction_limit():
    # Create 1000 transactions
    for i in range(1000):
        await create_transaction(person_id)
    
    # Should fail on 1001st
    with pytest.raises(HTTPException) as exc:
        await import_transactions(file, person_id, "enbd")
    
    assert exc.value.status_code == 402
```

---

## Monitoring

- Import success/failure rate
- Deduplication rate
- Transaction count per person
- Query performance (p50, p95)

---

**Status**: Ready for implementation  
**Owner**: Backend Team  
**Dependencies**: PostgreSQL, RabbitMQ

