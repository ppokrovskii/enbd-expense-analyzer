# Data Consistency Architecture

## Problem Statement

When displaying charts and transaction lists side-by-side, we need to guarantee that:
1. **Same filters produce same data** - Charts and lists must show the same transactions
2. **Consistent category handling** - NULL categories treated identically everywhere  
3. **Consistent transfer exclusion** - Transfer filtering applied uniformly
4. **Aggregations match details** - Chart totals = sum of transaction list

## Current Issues (Before Fix)

❌ **Transactions API:**
- Shows NULL categories as-is
- Includes all transactions (even transfers)
- Has all filter options (date, category, account, merchant)

❌ **Chart API:**
- Converts NULL → "Other"  
- Excludes 'Transfer Between My Accounts'
- Missing 'accounts' and 'merchant' filters

❌ **Result:** Charts and lists show different data!

## Solution: Service Layer Pattern

### Architecture

```
Frontend (React)
    ↓
API Endpoints (/api/transactions, /api/chart/weekly, /api/chart/monthly)
    ↓
TransactionQueryService (Single Source of Truth)
    ↓
Database (PostgreSQL)
```

### Key Design Decisions

#### 1. **Centralized Category Expression**
```python
category_expr = case(
    (Transaction.category.is_(None), 'Other'),
    else_=Transaction.category
)
```
- **Used everywhere**: Charts, lists, filters
- **Guarantees**: "Other" always means NULL category
- **Benefit**: Consistent user experience

#### 2. **Unified Filter Application**
```python
def apply_base_filters(
    query,
    start_date,
    end_date,
    categories,  # Supports "Other" for NULL
    accounts,
    merchant,
    exclude_transfers=True
)
```
- **Same function** for all queries
- **All filters** available in all contexts
- **Same logic** = same results

#### 3. **Transfer Exclusion Flag**
```python
exclude_transfers: bool = True
```
- **Default behavior**: Exclude internal transfers
- **Consistent**: Applied in charts and lists
- **Flexible**: Can be toggled if needed

## Implementation

### Service Layer (backend/app/services/transaction_query_service.py)

**Purpose:** Single source of truth for all transaction queries

**Methods:**
1. `get_category_expression()` - Standardized NULL → "Other" conversion
2. `apply_base_filters()` - Consistent filter application
3. `get_filtered_transactions()` - Paginated list with filters
4. `get_weekly_aggregation()` - Weekly chart data with filters
5. `get_monthly_aggregation()` - Monthly chart data with filters

### API Endpoints Update

**Before:**
```python
# Inconsistent logic duplicated across endpoints
@router.get("/transactions")
def get_transactions(...):
    query = db.query(Transaction)
    # Custom filter logic here
    
@router.get("/chart/weekly")
def get_weekly_chart_data(...):
    query = db.query(...)
    # Different filter logic here
```

**After:**
```python
# Delegated to service layer
@router.get("/transactions")
def get_transactions(...):
    transactions, total = TransactionQueryService.get_filtered_transactions(
        db, start_date, end_date, categories, accounts, merchant
    )
    
@router.get("/chart/weekly")  
def get_weekly_chart_data(...):
    results = TransactionQueryService.get_weekly_aggregation(
        db, start_date, end_date, categories, accounts, merchant
    )
```

## Guarantees

### 1. **Same Filters → Same Data**
```
Frontend applies filters: {
    startDate: "2025-01-01",
    endDate: "2025-01-31", 
    categories: ["Groceries", "Other"]
}

Transactions API uses: TransactionQueryService.get_filtered_transactions(...)
Chart API uses: TransactionQueryService.get_weekly_aggregation(...)

Both use: apply_base_filters() with same parameters
Result: ✅ Same underlying data
```

### 2. **Category Consistency**
```
Database has: category = NULL
Service layer converts: NULL → "Other"
User filters by: "Other"

Transactions shows: Rows with category="Other" (was NULL)
Chart shows: Bar segment for "Other" (was NULL)

Result: ✅ Consistent representation
```

### 3. **Transfer Exclusion**
```
Both APIs use: exclude_transfers=True (default)

Transaction list excludes: 'Transfer Between My Accounts'  
Chart excludes: 'Transfer Between My Accounts'

Result: ✅ Totals match
```

### 4. **All Filters Available**
```
Chart API now supports:
- start_date ✅
- end_date ✅
- categories ✅  
- accounts ✅ (NEW!)
- merchant ✅ (NEW!)

Result: ✅ Complete filter parity
```

## Testing Strategy

### Unit Tests
```python
def test_category_expression_consistency():
    """Ensure category expression is identical across use cases."""
    
def test_filter_application():
    """Verify same filters produce same record set."""
    
def test_aggregation_matches_details():
    """Sum of transaction list = chart totals."""
```

### Integration Tests  
```python
def test_chart_and_list_consistency():
    """Same filters → chart aggregations match transaction list sum."""
    # Get transactions
    transactions, _ = TransactionQueryService.get_filtered_transactions(
        db, categories=["Groceries"]
    )
    # Get chart data
    chart_data = TransactionQueryService.get_weekly_aggregation(
        db, categories=["Groceries"]
    )
    # Verify totals match
    assert sum(t.amount_signed for t in transactions) == sum(c.total for c in chart_data)
```

## Benefits

1. **Maintainability** - Filter logic in one place
2. **Testability** - Service layer can be unit tested
3. **Consistency** - Impossible to have divergent logic
4. **Flexibility** - Easy to add new filters/aggregations
5. **Clarity** - API endpoints are thin controllers
6. **Reusability** - Service methods used across endpoints

## Future Enhancements

1. **Caching Layer** - Cache aggregations for performance
2. **Query Builder** - Fluent interface for complex filters
3. **Audit Trail** - Log which filters were applied
4. **Performance Metrics** - Track query execution times
5. **Export Service** - Reuse filters for CSV/Excel export

## Migration Path

**Phase 1** (Current): Create service layer ✅  
**Phase 2**: Refactor existing endpoints to use service  
**Phase 3**: Add integration tests  
**Phase 4**: Remove duplicated filter logic  
**Phase 5**: Document API consistency guarantees

## Conclusion

By introducing `TransactionQueryService`, we architecturally guarantee that charts and transaction lists always show consistent data. The service layer acts as a single source of truth for all transaction queries, ensuring filters are applied uniformly and categories are handled consistently.

