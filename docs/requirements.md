# ENBD Expense Analyzer - Requirements

## Overview
CLI tool to analyze Emirates NBD transaction exports from multiple accounts. Download new XLSX files anytime, tool automatically deduplicates and maintains a master transaction database.

## Quick Commands
```bash
enbd import              # Process new XLSX files, dedupe, archive
enbd clean               # Parse, extract merchants, flag internal transfers
enbd categorize          # Rule-based categorization
enbd categorize --use-llm   # Use AI (OpenAI) with caching
enbd report weekly       # Monday-Monday breakdown (absolute values)
enbd report monthly      # Monthly breakdown (absolute values)
```

## Incremental Import Workflow

### Download & Import
1. Download new XLSX files from ENBD for any date range (overlapping periods OK)
2. Put files in `data/` folder
3. Run `enbd import`

### What Happens:
- Reads all `.xlsx` files in `data/`
- Combines with existing transactions from `data/master.csv`
- **Deduplicates** by unique key: `(Date, Account, Amount, Description)`
- Saves to `data/master.csv` (master transaction database)
- **Archives** processed XLSX files → `data/archive/YYYY-MM-DD/`

### Example:
```bash
# First import (Oct-Dec 2025)
$ ls data/
  Current Account Oct-Dec.xlsx
  Savings Account Oct-Dec.xlsx
$ enbd import
  ✓ Imported 542 transactions
  ✓ Master database: 542 total
  ✓ Archived 2 files → data/archive/2025-12-26/

# Second import (Nov-Jan 2026, overlapping)
$ ls data/
  Current Account Nov-Jan.xlsx
  Savings Account Nov-Jan.xlsx
$ enbd import
  ✓ Found 620 raw transactions
  ✓ Filtered 128 duplicates (already in master)
  ✓ Added 492 new transactions
  ✓ Master database: 1034 total
  ✓ Archived 2 files → data/archive/2026-01-15/
```

## Data Pipeline

**Import**: New XLSX → dedupe → append to `master.csv` → archive XLSX  
**Clean**: Parse `master.csv` → `cleaned.csv`  
**Categorize**: Apply rules + LLM → `categorized.csv`  
**Report**: Group by week/month → `weekly.csv` (pivot for Excel)

## Deduplication Strategy

**Unique Key**: `(Date, Account, Amount, Description, Debit/Credit)`

Why: ENBD doesn't provide transaction IDs, so we use composite key:
- Same date + account + amount + description + type = same transaction
- Edge case: Two identical transactions same day (rare, user can manually check)

**Hash**: `md5(date|account|amount|description|debit_credit)`

```python
def create_transaction_hash(row):
    key = f"{row['Date']}|{row['Account']}|{row['Amount']}|{row['Description']}|{row['Debit/Credit']}"
    return hashlib.md5(key.encode()).hexdigest()[:16]
```

## Key Features

### Data Cleanup
- Remove commas: `"7,600.00"` → `7600.00`
- Extract merchants: `"POKE AND CO RESTAURANT    DUBAI..."` → `POKE AND CO RESTAURANT`
- Signed amounts: Debit → negative, Credit → positive
- Flag internal transfers (avoid double-counting)
- Add date columns: `Week_Start`, `Month`, `Year`
- Add hash for deduplication

### Categorization
**Rule-based** (default):
```json
{
  "Food & Dining": ["POKE AND CO", "Deliveroo", "CAREEM HALA"],
  "Groceries": ["CARREFOUR", "CHOITHRAMS", "www.instashop.com"],
  "Shopping": ["Amazon", "DEBENHAMS"],
  "Transport": ["DUBAI TAXI", "CAREEM QUIK"],
  "Utilities": ["Virgin Mobile", "APPLE.COM/BILL"]
}
```

**LLM-powered** (optional):
- OpenAI GPT-4o-mini (~$0.01-0.02 first run, then FREE)
- **Smart caching**: Results saved to `config/llm_categories.json`
- **Pay once**: Subsequent runs use cache (no API calls)
- **New merchants only**: Only uncached merchants sent to API
- **Version control friendly**: Cache is human-readable JSON

### Reports
- **Weekly**: Monday-Monday, excludes internal transfers
- **Monthly**: Calendar month
- **Output**: Pivot format with **absolute values** for Excel Stacked Column Chart
- Expenses shown as positive numbers (better visualization)

## File Structure
```
data/
  *.xlsx                    # New exports (put here)
  master.csv                # Master transaction database (deduplicated)
  cleaned.csv               # After cleaning
  categorized.csv           # After categorization
  archive/
    2025-12-26/             # Processed files by date
      Current Account.xlsx
      Savings Account.xlsx
    2026-01-15/
      Current Account.xlsx
reports/
  weekly_expenses.csv       # Pivot format (absolute values)
  monthly_expenses.csv      # Pivot format (absolute values)
config/
  categories.json           # User-defined category rules
  llm_categories.json       # LLM categorization cache (auto-generated)
.env                        # API keys (gitignored)
.env.example                # Template for environment variables
```

## Master Database Schema

`data/master.csv`:
```
Hash, Date, Week_Start, Month, Year, Account, Transaction_Type, Merchant, 
Details, Description, Amount, Amount_Signed, Currency, Balance, 
Debit/Credit, Status, Is_Internal_Transfer, Category, Imported_At
```

- **Hash**: Unique transaction ID (for deduplication)
- **Imported_At**: When first imported (ISO timestamp)
- **Category**: Initially empty, filled by `categorize` command

## Excel Visualization
1. Open `reports/weekly_expenses.csv`
2. Insert → Stacked Column Chart
3. X-axis: weeks, Y-axis: amounts, colors: categories

## LLM Setup (Optional)

**OpenAI** (recommended):
```bash
# 1. Get API key from: https://platform.openai.com/api-keys
# 2. Create .env file:
echo "OPENAI_API_KEY=sk-proj-your-key-here" > .env

# 3. Run categorization with LLM:
enbd categorize --use-llm
```

**How LLM Categorization Works**:
1. Applies rule-based categorization first
2. Checks `config/llm_categories.json` cache
3. Sends only NEW uncategorized merchants to OpenAI API
4. Caches all results for future runs
5. Cost: ~$0.01-0.02 first time, then FREE (uses cache)

**Cache Benefits**:
- Pay only once per unique merchant
- Instant categorization on subsequent runs
- Share cache file via git (merchants stay categorized)
- Manually edit cache if needed

**Example**:
```bash
# First run: categorizes 191 merchants (~$0.02)
enbd categorize --use-llm

# Second run: uses cache (no API calls, $0)
enbd categorize --use-llm

# New merchants: only pays for uncached ones
enbd categorize --use-llm  # 5 new merchants = $0.0005
```

## Tech Stack
- Python 3.9+, Pandas, Click
- OpenAI Python SDK (optional, for LLM categorization)
- python-dotenv (for .env file support)
- No database, CSV-based master file

## Success Criteria
- Handle overlapping date ranges (auto-dedupe)
- Archive processed files automatically
- Process 1000+ transactions in < 5 seconds
- Zero manual CSV manipulation
- < 5% in "Others" category (with LLM)
- Excel-ready pivot output
