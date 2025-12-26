# ENBD Chart App - Solution Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├──────────────────────┬──────────────────────────────────┤
│   Frontend           │         Backend                  │
│   (Next.js)          │         (FastAPI)                │
│   Port 3000          │         Port 8000                │
├──────────────────────┴──────────────────────────────────┤
│              Shared Volumes                              │
│          ./data/  ./config/  ./uploads/                 │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14 + TypeScript | SSR, fast, modern |
| Charts | Recharts | React-native, flexible |
| UI | TailwindCSS + shadcn/ui | Beautiful, accessible |
| Backend | FastAPI + Python 3.11 | Async, fast, reuses analyzer |
| Data | CSV (existing pipeline) | Simple, no DB setup |
| Deploy | Docker Compose | One-command local setup |

## Component Architecture

### Backend (`/backend`)

```python
app/
├── main.py              # FastAPI app + CORS
├── routers/
│   ├── upload.py        # POST /api/upload (file handling)
│   ├── data.py          # GET /api/data (filtered data)
│   ├── categories.py    # Category CRUD + AI operations
│   └── stats.py         # GET /api/stats (summary)
├── services/
│   ├── pipeline.py      # Run ENBD analyzer pipeline
│   ├── data_loader.py   # Read/filter categorized.csv
│   ├── aggregator.py    # Group by week/month, stack data
│   └── category_manager.py  # Category rule management
└── models/
    └── schemas.py       # Pydantic models
```

**Key Classes:**

```python
class DataService:
    def get_data(filters: FilterParams) -> ChartData:
        # 1. Load categorized.csv
        # 2. Apply filters (date, categories)
        # 3. Group by week/month
        # 4. Separate income vs expenses
        # 5. Sort categories by total (largest first)
        # 6. Return stacked data structure

class PipelineService:
    async def process_upload(files: List[UploadFile]) -> ProcessResult:
        # 1. Save XLSX to ./data/
        # 2. Run: enbd import
        # 3. Run: enbd clean
        # 4. Run: enbd categorize (with LLM if configured)
        # 5. Return stats: new_transactions, categories_added

class CategoryManager:
    def get_rules(self) -> Dict[str, List[str]]:
        # Load categories.json
        
    def update_rules(self, category: str, add: List[str], remove: List[str]):
        # Update categories.json
        # Re-run categorization pipeline
        
    def add_category(self, name: str, keywords: List[str]):
        # Add new category to categories.json
        
    def delete_category(self, name: str):
        # Remove category, reassign transactions to "Other"
        
    async def ai_recategorize(self, scope: str, target: Optional[str] = None):
        # scope: "all" | "category" | "merchant"
        # 1. Find uncategorized merchants
        # 2. Call LLM for suggestions
        # 3. Update llm_categories.json cache
        # 4. Re-run categorization
        # 5. Return: { updated_merchants: [...], transactions_affected: 45 }
```

### Frontend (`/frontend`)

```typescript
src/
├── app/
│   ├── page.tsx              # Main dashboard
│   ├── categories/
│   │   └── page.tsx          # Category management UI
│   └── layout.tsx            # App shell
├── components/
│   ├── UploadZone.tsx        # Drag & drop + progress
│   ├── Filters.tsx           # Date, categories, grouping
│   ├── StackedChart.tsx      # Recharts implementation
│   ├── TransactionTable.tsx  # Paginated table
│   ├── CategoryCard.tsx      # Category display card
│   ├── CategoryEditModal.tsx # Edit keywords modal
│   └── AIRecategorizeModal.tsx  # AI update confirmation
├── lib/
│   ├── api.ts                # Fetch wrapper
│   └── types.ts              # TypeScript interfaces
└── hooks/
    ├── useData.ts            # Data fetching + caching
    ├── useFilters.ts         # Filter state management
    └── useCategories.ts      # Category CRUD + AI ops
```

**Key Components:**

```typescript
// Stacked chart data structure
interface ChartData {
  periods: Period[]  // [{week: "2025-W01", income: 45540, expenses: {...}}]
  categories: string[]  // Sorted by total amount
  colors: Record<string, string>  // Category colors
}

// Category management
interface Category {
  name: string
  keywords: string[]
  transaction_count: number
  percentage: number
}

interface AIRecategorizeRequest {
  scope: "all" | "category" | "merchant"
  target?: string  // Category name or merchant name
}

// State management (React Query + Zustand)
const useFilters = () => {
  dateRange: [Date, Date]
  categories: string[]
  groupBy: 'week' | 'month'
}

const useData = (filters) => {
  // React Query for caching + auto-refresh
  data: ChartData | null
  transactions: Transaction[]
  isLoading: boolean
}

const useCategories = () => {
  categories: Category[]
  getRules: () => Promise<Record<string, string[]>>
  updateRules: (category: string, add: string[], remove: string[]) => Promise<void>
  addCategory: (name: string, keywords: string[]) => Promise<void>
  deleteCategory: (name: string) => Promise<void>
  aiRecategorize: (request: AIRecategorizeRequest) => Promise<RecategorizeResult>
}
```

## Data Flow

### Upload Flow
```
User drops XLSX
    ↓
Frontend uploads to /api/upload
    ↓
Backend saves to ./data/
    ↓
Run pipeline (import → clean → categorize)
    ↓
WebSocket sends progress updates
    ↓
Frontend polls /api/data
    ↓
Chart + Table refresh
```

### Category Management Flow
```
User clicks "Edit Category"
    ↓
Frontend shows modal with current keywords
    ↓
User adds/removes keywords
    ↓
PUT /api/categories/rules
    ↓
Backend:
  - Update categories.json
  - Re-run categorization on cleaned.csv
  - Generate new categorized.csv
    ↓
Frontend refetches data
    ↓
Chart updates with new categories
```

### AI Recategorization Flow
```
User clicks "🤖 Update with AI"
    ↓
POST /api/categories/recategorize { scope: "all" }
    ↓
Backend:
  - Load cleaned.csv
  - Find "Other" category merchants
  - Call OpenAI LLM for each merchant
  - Update llm_categories.json cache
  - Re-run categorization
  - Save new categorized.csv
    ↓
Return { updated_merchants: [...], transactions_affected: 45 }
    ↓
Frontend shows confirmation
    ↓
User confirms → refetch data → chart updates
```

### Chart Rendering Flow
```
User changes filters
    ↓
Frontend calls /api/data?filters=...
    ↓
Backend:
  - Load categorized.csv
  - Filter by date + categories
  - Group by week/month
  - Separate income (Salary, Incoming Transfer)
  - Separate expenses (all other categories)
  - Sort expense categories by total (desc)
  - Stack categories (largest at bottom)
    ↓
Return JSON:
{
  periods: [
    {
      date: "2025-W01",
      income: 45540,      // Single bar (green)
      expenses: {         // Stacked bars
        "Shopping": 2500,      // Bottom (largest)
        "Groceries": 1500,
        "Food & Dining": 800,
        "Transport": 500       // Top (smallest)
      }
    }
  ]
}
    ↓
Frontend renders with Recharts
```

## API Design

### Endpoints

```python
# Upload
POST /api/upload
  Content-Type: multipart/form-data
  Files: file1.xlsx, file2.xlsx
  Response: {
    job_id: "uuid",
    status: "processing",
    files_count: 2
  }

# Get upload status
GET /api/upload/{job_id}
  Response: {
    status: "completed" | "processing" | "failed",
    progress: 75,
    transactions_added: 120,
    error?: "..."
  }

# Get chart data
GET /api/data
  Query params:
    from: "2025-01-01"
    to: "2025-12-31"
    categories: "Food,Shopping"  (empty = all)
    groupby: "week" | "month"
  Response: {
    chart_data: {
      periods: [...],
      categories: [...],
      totals: { income: X, expenses: Y }
    },
    transactions: [...],  // For table
    pagination: { total: 542, page: 1, per_page: 50 }
  }

# Get metadata
GET /api/categories
  Response: ["Food & Dining", "Shopping", ...]

# Get category rules
GET /api/categories/rules
  Response: {
    "Food & Dining": ["CARREFOUR", "LULU", "PAUL"],
    "Shopping": ["IKEA", "H&M", "LRIL"],
    ...
  }

# Update category rules
PUT /api/categories/rules
  Body: {
    category: "Food & Dining",
    add_keywords: ["SPINNEYS", "WAITROSE"],
    remove_keywords: ["IKEA"]
  }
  Response: {
    success: true,
    updated_count: 2,
    recategorized_transactions: 12
  }

# Add new category
POST /api/categories
  Body: {
    name: "Pets",
    keywords: ["PETZONE", "VET", "GROOMING"]
  }
  Response: {
    success: true,
    category: "Pets"
  }

# Delete category
DELETE /api/categories/{name}
  Response: {
    success: true,
    transactions_moved_to_other: 34
  }

# AI recategorization
POST /api/categories/recategorize
  Body: {
    scope: "all" | "category" | "merchant",
    target?: "Other" | "UNKNOWN MERCHANT"
  }
  Response: {
    job_id: "uuid",
    status: "processing"
  }

# Get recategorization status
GET /api/categories/recategorize/{job_id}
  Response: {
    status: "completed" | "processing" | "failed",
    updated_merchants: ["SPINNEYS", "WAITROSE"],
    transactions_affected: 45,
    cost_estimate: "$0.02"
  }

# Get stats
GET /api/stats
  Response: {
    total_transactions: 542,
    date_range: { from: "...", to: "..." },
    total_income: 151312,
    total_expenses: 80339,
    uncategorized_count: 23
  }
```

## Docker Setup

### docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./uploads:/app/uploads
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy

volumes:
  data:
  config:
  uploads:
```

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## Chart Implementation

### Stacked Column with Recharts
```typescript
<ResponsiveContainer width="100%" height={400}>
  <ComposedChart data={chartData.periods}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="date" />
    <YAxis />
    <Tooltip />
    <Legend />
    
    {/* Income bar (green, at bottom) */}
    <Bar dataKey="income" fill="#10b981" name="Income" />
    
    {/* Expense bars (stacked, sorted large→small) */}
    {chartData.categories.map((cat, i) => (
      <Bar 
        key={cat}
        dataKey={`expenses.${cat}`}
        stackId="expenses"
        fill={colors[cat]}
        name={cat}
      />
    ))}
  </ComposedChart>
</ResponsiveContainer>
```

### Category Sorting Logic
```python
def sort_categories_by_total(df: pd.DataFrame) -> List[str]:
    """Sort expense categories by total amount (largest first)"""
    expense_categories = df[
        (df['Amount_Signed'] < 0) & 
        (~df['Category'].isin(['Salary', 'Incoming Transfer']))
    ]
    
    totals = expense_categories.groupby('Category')['Amount_Signed'].sum().abs()
    return totals.sort_values(ascending=False).index.tolist()
```

## Performance Optimization

1. **Caching**: React Query caches API responses (5 min TTL)
2. **Debouncing**: Filter changes debounced (300ms)
3. **Pagination**: Table loads 50 rows at a time
4. **CSV streaming**: Large files read in chunks
5. **Background jobs**: File processing in async tasks

## Security

- CORS: Only localhost:3000 allowed
- File validation: Only .xlsx with size < 50MB
- Path sanitization: Prevent directory traversal
- Environment vars: API keys in .env (not committed)

## Future Enhancements (Multi-user)

When adding multi-user support:
1. Add PostgreSQL service to docker-compose
2. User auth: JWT tokens + session management
3. Data isolation: Add `user_id` to all data operations
4. Separate data directories per user: `./data/{user_id}/`
5. Shared categories: Common + user-specific rules

Current design is **single-user** - all data shared, no auth required.

## Development Workflow

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart after code changes
docker-compose restart backend

# Stop all
docker-compose down

# Fresh start (remove volumes)
docker-compose down -v
```

## Testing Strategy

**Backend**:
- Unit tests: `pytest` for services
- Integration: Test full pipeline with sample XLSX
- API tests: `httpx` test client

**Frontend**:
- Component tests: Jest + React Testing Library
- E2E: Playwright (upload → view chart flow)

**Docker**:
- Health checks ensure services are ready
- Volume mounts work correctly

## File Structure
```
enbd-chart-app/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── upload.py
│   │   │   ├── data.py
│   │   │   ├── categories.py      # NEW: Category management
│   │   │   └── stats.py
│   │   ├── services/
│   │   │   ├── pipeline.py
│   │   │   ├── data_loader.py
│   │   │   ├── aggregator.py
│   │   │   └── category_manager.py  # NEW: CRUD + AI ops
│   │   └── models/
│   │       └── schemas.py
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   ├── categories/         # NEW: Category management page
│   │   │   │   └── page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   ├── Filters.tsx
│   │   │   ├── StackedChart.tsx
│   │   │   ├── TransactionTable.tsx
│   │   │   ├── CategoryCard.tsx         # NEW
│   │   │   ├── CategoryEditModal.tsx    # NEW
│   │   │   └── AIRecategorizeModal.tsx  # NEW
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── types.ts
│   │   └── hooks/
│   │       ├── useData.ts
│   │       ├── useFilters.ts
│   │       └── useCategories.ts    # NEW: Category ops
│   └── tests/
├── data/              # Shared volume
├── config/            # Shared volume
└── uploads/           # Temp upload storage
```

## Success Metrics

- ✅ Upload processes in < 30s for 500 transactions
- ✅ Chart renders in < 500ms
- ✅ Filter changes update instantly (< 300ms)
- ✅ Category edit applies in < 5s
- ✅ AI recategorization completes in < 10s for 50 merchants
- ✅ Works on mobile (responsive down to 375px)
- ✅ One command deployment: `docker-compose up`

## Category Management Implementation Notes

### Backend Service (`category_manager.py`)

```python
class CategoryManager:
    def __init__(self, config_dir: Path):
        self.rules_file = config_dir / "categories.json"
        self.cache_file = config_dir / "llm_categories.json"
        
    def get_rules(self) -> Dict[str, List[str]]:
        """Load categories.json"""
        with open(self.rules_file) as f:
            return json.load(f)
    
    def update_rules(self, category: str, add: List[str], remove: List[str]) -> int:
        """Update keywords, re-run categorization"""
        rules = self.get_rules()
        
        # Update rules
        rules[category] = list(set(rules[category]) - set(remove))
        rules[category].extend(add)
        
        # Save
        with open(self.rules_file, 'w') as f:
            json.dump(rules, f, indent=2)
        
        # Re-categorize
        from enbd_analyzer.categorizer import CategorizePipeline
        pipeline = CategorizePipeline(...)
        pipeline.run()
        
        return self._count_recategorized(category)
    
    async def ai_recategorize(self, scope: str, target: Optional[str]) -> Dict:
        """Run LLM categorization"""
        from enbd_analyzer.categorizer import CategorizePipeline
        
        # Load cleaned.csv
        df = pd.read_csv("data/cleaned.csv")
        
        # Find merchants to categorize
        if scope == "all":
            merchants = df[df['Category'] == 'Other']['Merchant'].unique()
        elif scope == "category":
            merchants = df[df['Category'] == target]['Merchant'].unique()
        else:  # merchant
            merchants = [target]
        
        # Run LLM (reuse existing LLM provider)
        pipeline = CategorizePipeline(..., use_llm=True)
        results = await pipeline.categorize_batch(merchants)
        
        # Update cache
        cache = CategoryCache(self.cache_file)
        for merchant, category in results.items():
            cache.set(merchant, category)
        
        # Re-run categorization
        pipeline.run()
        
        return {
            "updated_merchants": list(results.keys()),
            "transactions_affected": len(df[df['Merchant'].isin(results.keys())])
        }
```

### Frontend Hook (`useCategories.ts`)

```typescript
export function useCategories() {
  const queryClient = useQueryClient()
  
  // Fetch rules
  const { data: rules } = useQuery({
    queryKey: ['category-rules'],
    queryFn: () => api.get('/api/categories/rules'),
  })
  
  // Update mutation
  const updateRules = useMutation({
    mutationFn: (params: UpdateRulesParams) => 
      api.put('/api/categories/rules', params),
    onSuccess: () => {
      queryClient.invalidateQueries(['category-rules'])
      queryClient.invalidateQueries(['chart-data'])
      toast.success('Category updated!')
    },
  })
  
  // AI recategorization
  const aiRecategorize = useMutation({
    mutationFn: (params: RecategorizeParams) =>
      api.post('/api/categories/recategorize', params),
    onSuccess: async (response) => {
      // Poll for completion
      const jobId = response.job_id
      const result = await pollJobStatus(jobId)
      
      toast.success(
        `✅ ${result.updated_merchants.length} merchants categorized`
      )
      
      queryClient.invalidateQueries(['chart-data'])
    },
  })
  
  return { rules, updateRules, aiRecategorize }
}

async function pollJobStatus(jobId: string) {
  while (true) {
    const response = await api.get(`/api/categories/recategorize/${jobId}`)
    if (response.status === 'completed') return response
    if (response.status === 'failed') throw new Error(response.error)
    await sleep(1000)
  }
}
```

### UI Components

**CategoryCard.tsx**:
- Displays category name, keywords, transaction count
- Edit, AI Update, Delete buttons
- Expandable to show all keywords

**CategoryEditModal.tsx**:
- Text input for category name
- Tag input for keywords (add/remove)
- "AI Suggest Keywords" button (calls LLM to suggest)
- Save/Cancel buttons

**AIRecategorizeModal.tsx**:
- Shows preview of changes before applying
- "AI will categorize 23 merchants (estimated $0.05)"
- List of merchants to be categorized
- Confirm/Cancel buttons
- Progress bar during processing

