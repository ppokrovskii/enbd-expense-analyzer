# ENBD Expense Analyzer - Solution Design

## Architecture Philosophy
**Zero dependencies on external databases. CSV as the database. Immutable imports. Composable pipeline.**

## System Design

```
XLSX files → IMPORT → master.csv → CLEAN → cleaned.csv → CATEGORIZE → categorized.csv → REPORT
                ↓
            archive/
```

### Core Principles
1. **Idempotent Operations**: Re-running any command is safe
2. **Immutable Master**: Never delete from `master.csv`, only append
3. **Hash-based Deduplication**: O(1) lookups via set operations
4. **Fail-Fast**: Validate early, fail with clear errors
5. **Testable**: Each stage pure function (CSV in → CSV out)

## Component Architecture

### 1. CLI Layer (`cli.py`)
```python
# Click-based command tree
enbd
├── import      # ImportPipeline
├── clean       # CleanPipeline  
├── categorize  # CategorizePipeline
└── report      # ReportGenerator
```

**Why Click**: Nested commands, auto-help, parameter validation, testing support.

### 2. Core Modules

#### `importer.py` - Incremental Import Engine
```python
class ImportPipeline:
    def run(self):
        xlsx_files = self._discover_xlsx()
        raw_df = self._parse_xlsx_files(xlsx_files)
        master_df = self._load_master()
        new_df = self._deduplicate(raw_df, master_df)
        self._append_to_master(new_df)
        self._archive_files(xlsx_files)
```

**Key Algorithm**:
```python
def _deduplicate(raw: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    raw['hash'] = raw.apply(create_hash, axis=1)
    existing_hashes = set(master['hash']) if len(master) > 0 else set()
    new_mask = ~raw['hash'].isin(existing_hashes)
    return raw[new_mask]

def create_hash(row) -> str:
    # Composite key: date|account|amount|description|debit_credit
    key = f"{row['Date']}|{row['Account']}|{row['Amount']}|{row['Description']}|{row['Debit/Credit']}"
    return hashlib.md5(key.encode()).hexdigest()[:16]
```

**XLSX Parser Challenge**: ENBD exports have metadata rows (account number, currency) before headers.
```python
def _parse_xlsx(file_path: Path) -> pd.DataFrame:
    # Skip metadata rows, find "Date" header dynamically
    df = pd.read_excel(file_path, header=None)
    header_row = df[df[0] == 'Date'].index[0]
    df = pd.read_excel(file_path, skiprows=header_row)
    df['Account'] = extract_account_from_filename(file_path.stem)
    return df
```

#### `cleaner.py` - Data Normalization
```python
class CleanPipeline:
    TRANSFORMS = [
        remove_commas_from_amounts,
        extract_merchant_from_description,
        create_signed_amounts,
        flag_internal_transfers,
        add_date_dimensions,
        validate_no_nulls
    ]
```

**Merchant Extraction**:
```python
# "POKE AND CO RESTAURANT    DUBAI AE" → "POKE AND CO RESTAURANT"
def extract_merchant(description: str) -> str:
    return re.sub(r'\s{2,}.*', '', description).strip()
```

**Internal Transfer Detection**:
```python
TRANSFER_KEYWORDS = ['INTERNAL TRANSFER', 'BETWEEN OWN', 'STANDING ORDER']
def is_internal_transfer(row) -> bool:
    return any(kw in row['Description'].upper() for kw in TRANSFER_KEYWORDS)
```

#### `categorizer.py` - Rule Engine + LLM with Caching
```python
class CategorizePipeline:
    def __init__(self, use_llm: bool = False):
        self.rules = CategoryRules.load('config/categories.json')
        self.cache = CategoryCache('config/llm_categories.json')
        self.llm = LLMProvider.create() if use_llm else None
    
    def categorize(self, df: pd.DataFrame) -> pd.DataFrame:
        # Step 1: Apply rules
        df['Category'] = df['Merchant'].apply(self.rules.categorize)
        
        # Step 2: Apply cached LLM results
        cached_applied = self._apply_cache(df)
        
        # Step 3: Use LLM for remaining "Other" (if enabled)
        if self.llm:
            unknown = df[df['Category'] == 'Other']
            uncached = [m for m in unknown['Merchant'].unique() 
                       if not self.cache.has(m)]
            
            if uncached:
                # Only call API for uncached merchants
                results = self.llm.categorize_batch(uncached)
                self.cache.set_batch(results)
                self.cache.save()  # Persist to disk
            
            # Apply all cached results
            df = self._apply_cache(df)
        
        return df
```

**Caching Strategy**: 
- Results saved to `config/llm_categories.json`
- JSON format: `{"merchant_name": "Category"}`
- Version control friendly (commit to git)
- Only new merchants trigger API calls
- Cost: Pay once per unique merchant

#### `reporter.py` - Pivot Table Generator with Absolute Values
```python
class ReportGenerator:
    def weekly(self, df: pd.DataFrame) -> pd.DataFrame:
        # Filter out internal transfers
        df = df[~df['Is_Internal_Transfer']]
        
        # Group by week_start + category, sum amounts
        pivot = df.pivot_table(
            index='Week_Start',
            columns='Category',
            values='Amount_Signed',
            aggfunc='sum',
            fill_value=0
        )
        
        # Convert to absolute values for Excel visualization
        pivot = pivot.abs()
        
        return pivot
```

**Week Calculation**: Monday-Monday using `pd.Grouper`.
**Absolute Values**: Expenses shown as positive numbers for better chart visualization.

### 3. LLM Abstraction (`llm_provider.py`)
```python
class LLMProvider(ABC):
    @abstractmethod
    def categorize_batch(self, merchants: List[str], categories: List[str]) -> Dict[str, str]:
        """Categorize a batch of merchants."""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.model = model
    
    def categorize_batch(self, merchants: List[str], categories: List[str]) -> Dict[str, str]:
        # Batch 50 merchants per API call
        # Returns: {"merchant": "Category"}
        pass
```

**Prompt Engineering**:
```python
SYSTEM_PROMPT = """
Categorize merchant into ONE category:
{categories}

Merchant: {merchant}
Category:
"""
```

**Cost Optimization**:
- Uses GPT-4o-mini ($0.15 per 1M input tokens)
- Batches 50 merchants per call
- ~$0.0001 per merchant

### 4. Category Cache (`category_cache.py`)
```python
class CategoryCache:
    """Cache LLM results to avoid redundant API calls."""
    
    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache: Dict[str, str] = {}
        self.load()
    
    def load(self):
        """Load cache from JSON file."""
        if self.cache_path.exists():
            self.cache = json.load(self.cache_path.open())
    
    def save(self):
        """Save cache to JSON file."""
        json.dump(self.cache, self.cache_path.open('w'), indent=2, sort_keys=True)
    
    def has(self, merchant: str) -> bool:
        """Check if merchant is cached."""
        return merchant in self.cache
    
    def set_batch(self, results: Dict[str, str]):
        """Update cache with new results."""
        self.cache.update(results)
```

**Benefits**:
- Persistent storage in JSON format
- Version control friendly
- Pay once per unique merchant
- Team can share cache via git

## Data Model

### File Structure
```
data/
  master.csv              # Source of truth (append-only)
  cleaned.csv             # Intermediate (regenerated)
  categorized.csv         # Final (regenerated)
  archive/
    2025-12-26/
      *.xlsx
reports/
  weekly_expenses.csv     # Pivot format with absolute values
  monthly_expenses.csv    # Pivot format with absolute values
config/
  categories.json         # User-defined rules
  llm_categories.json     # LLM categorization cache
.env                      # API keys (gitignored)
.env.example              # Template for environment variables
```

### Schema: `master.csv`
| Column | Type | Source | Notes |
|--------|------|--------|-------|
| hash | str | computed | Deduplication key |
| Date | date | XLSX | Transaction date |
| Week_Start | date | computed | Monday of week |
| Month | str | computed | YYYY-MM |
| Year | int | computed | YYYY |
| Account | str | filename | Current/Savings/Millionaire/Smart Saver |
| Merchant | str | computed | Extracted from Description |
| Description | str | XLSX | Raw transaction text |
| Amount | float | XLSX | Unsigned |
| Amount_Signed | float | computed | Negative for debits |
| Currency | str | XLSX | AED |
| Balance | float | XLSX | Account balance after txn |
| Debit/Credit | str | XLSX | D or C |
| Status | str | XLSX | Completed/Pending |
| Is_Internal_Transfer | bool | computed | Exclude from reports |
| Category | str | categorizer | Initially null |
| Imported_At | datetime | computed | ISO timestamp |

## Performance Strategy

### Target: 1000 txns < 5s
- **Pandas vectorization**: No row iteration except hashing
- **Chunked LLM calls**: Batch 50 merchants (1 API call vs 50)
- **Smart caching**: Only uncached merchants sent to API
- **Lazy loading**: Only load CSVs when needed
- **Set-based dedup**: O(1) hash lookups

### LLM Cost Optimization
- **Caching**: Pay once per unique merchant
- **Batching**: 50 merchants per API call
- **Model**: GPT-4o-mini ($0.15/1M tokens)
- **First run**: ~$0.01-0.02 for 200 merchants
- **Subsequent runs**: $0 (uses cache)
- **New merchants**: ~$0.0001 each

### Memory Footprint
- 10K transactions ≈ 5MB in memory
- Safe to load entire dataset for analysis

## Error Handling

### Validation Gates
1. **Import**: Check XLSX has required columns
2. **Clean**: No nulls in critical fields (Date, Amount, Account)
3. **Categorize**: Warn if >10% uncategorized
4. **Report**: Fail if no data in date range

### User Feedback
```python
# Rich library for beautiful CLI output
✓ Imported 542 transactions (12 duplicates filtered)
✓ Master database: 1,034 total
✓ Archived 2 files → data/archive/2025-12-26/
```

## Testing Strategy

### Unit Tests (pytest)
```python
# tests/test_importer.py
def test_deduplication():
    raw = create_sample_df()
    master = create_sample_df()  # Same data
    result = ImportPipeline()._deduplicate(raw, master)
    assert len(result) == 0

# tests/test_cleaner.py
def test_merchant_extraction():
    assert extract_merchant("POKE AND CO    DUBAI") == "POKE AND CO"
```

### Integration Tests
```python
# tests/test_pipeline.py
def test_full_pipeline(tmp_path):
    # Use local emulators per user rules
    shutil.copy("fixtures/sample.xlsx", tmp_path / "data")
    cli.import_cmd()
    assert (tmp_path / "data" / "master.csv").exists()
```

### Test Data
- `fixtures/`: Sample XLSX files (3 accounts, 100 txns)
- Cover edge cases: same-day duplicates, special characters, large amounts

## Configuration

### `pyproject.toml` (uv)
```toml
[project]
name = "enbd-expense-analyzer"
version = "0.1.0"
dependencies = [
    "pandas>=2.0",
    "click>=8.1",
    "openpyxl>=3.1",  # XLSX support
    "rich>=13.0",      # Beautiful CLI
    "openai>=2.0",     # OpenAI API
    "python-dotenv>=1.0",  # .env file support
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=7.0",
]

[project.scripts]
enbd = "enbd_analyzer.cli:cli"
```

### `config/categories.json`
```json
{
  "Food & Dining": ["POKE AND CO", "DELIVEROO", "CAREEM HALA"],
  "Groceries": ["CARREFOUR", "CHOITHRAMS", "INSTASHOP"],
  "Shopping": ["AMAZON", "NOON.COM", "DEBENHAMS"],
  "Transport": ["DUBAI TAXI", "CAREEM", "SALIK", "ENOC"],
  "Utilities": ["VIRGIN MOBILE", "APPLE.COM/BILL", "DEWA"],
  "Healthcare": ["MEDICLINIC", "ASTER"],
  "Entertainment": ["VOX CINEMAS", "SPOTIFY"]
}
```

## Deployment

### Installation
```bash
# Using uv (fast, modern)
curl -LsSf https://astral.sh/uv/install.sh | sh
cd enbd-expense-analyzer
uv sync
uv run enbd --help
```

### First Run
```bash
uv run enbd import           # Process existing XLSX files
uv run enbd clean            # Parse & normalize
uv run enbd categorize       # Apply rules
uv run enbd report weekly    # Generate pivot table
```

## Future Enhancements (Out of Scope)

1. **Web Dashboard**: Streamlit/Dash visualization
2. **Budget Alerts**: Notify when category > threshold
3. **Forecasting**: Predict next month spending
4. **Multi-currency**: Support non-AED transactions
5. **Database Migration**: PostgreSQL for >100K transactions
6. **Additional LLM Providers**: Anthropic Claude, local models (Ollama)
7. **Interactive cache management**: CLI commands to review/edit cache

## Why This Design Wins

1. **Simplicity**: CSV-based, no DB setup, works everywhere
2. **Reliability**: Immutable master, hash-based dedup, idempotent
3. **Speed**: Pandas vectorization, batch LLM calls, smart caching
4. **Cost-effective**: Pay once per merchant with LLM caching
5. **Testability**: Pure functions, fixtures included
6. **Extensibility**: Plugin pattern for LLM providers
7. **User Experience**: Rich CLI, clear feedback, Excel-ready output
8. **Team-friendly**: Cache can be committed to git and shared

**Lines of Code Estimate**: 
- Core: ~900 lines (including LLM + caching)
- Tests: ~450 lines  
- **Total**: ~1,350 lines

