# ENBD Expense Chart App - Requirements

## Overview
Web app to visualize ENBD expenses with interactive charts and transaction details. Upload XLSX files directly in the UI. Runs locally in Docker. No more Excel!

## Data Source
- Upload XLSX files via web UI
- Auto-processes: import → clean → categorize → display
- Stores in `data/categorized.csv`
- Real-time updates

## Deployment
**Docker Compose** - One command to run everything:
```bash
docker-compose up
```
Access at: `http://localhost:3000`

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│ ENBD Expense Analyzer          [Categories⚙️] [Upload] │
├─────────────────────────────────────────────────────────┤
│ Filters:                                                │
│  Date Range: [From: ___] [To: ___]  Group by: [Week▼]  │
│  Categories: [☑ All] [☐ Food] [☐ Shopping] ...         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│     STACKED COLUMN CHART                                │
│     ┌───────────────────────────────────────┐          │
│  $$ │        ┌──┐     ┌──┐                  │          │
│     │   ┌──┐ │  │┌──┐ │  │                  │          │
│     │   │  │ │  ││  │ │  │                  │          │
│     │   └──┘ └──┘└──┘ └──┘                  │          │
│     │   ────────────────────                 │          │
│     │   Week1 Week2 Week3 Week4              │          │
│     └───────────────────────────────────────┘          │
│     Legend: █ Income (bottom) █ Expenses (stacked)     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Transactions (245 shown):                               │
│ ┌────────┬──────────┬───────────┬─────────┬──────────┐ │
│ │ Date   │ Merchant │ Category  │ Amount  │ Account  │ │
│ ├────────┼──────────┼───────────┼─────────┼──────────┤ │
│ │ Dec 26 │ CARREFOUR│ Groceries │ -245.00 │ Current  │ │
│ │ Dec 25 │ DTB      │ Salary    │ 45540.00│ Current  │ │
│ └────────┴──────────┴───────────┴─────────┴──────────┘ │
│ Pagination: « 1 2 3 4 5 »                              │
└─────────────────────────────────────────────────────────┘
```

## Category Management UI

### Categories Settings Page
Accessible via ⚙️ button in top navigation.

```
┌─────────────────────────────────────────────────────────┐
│ Category Management                          [🔙 Back]  │
├─────────────────────────────────────────────────────────┤
│ [🤖 Update All with AI] [➕ Add Category]               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─ Food & Dining ────────────────────────────────────┐ │
│ │ Keywords: CARREFOUR, LULU, PAUL, STARBUCKS         │ │
│ │ Transactions: 145 (28%)                            │ │
│ │ [✏️ Edit] [🤖 AI Update] [🗑️ Delete]               │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─ Shopping ─────────────────────────────────────────┐ │
│ │ Keywords: IKEA, H&M, LRIL, SEPHORA, OUNASS         │ │
│ │ Transactions: 89 (17%)                             │ │
│ │ [✏️ Edit] [🤖 AI Update] [🗑️ Delete]               │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─ Other ────────────────────────────────────────────┐ │
│ │ Uncategorized: 23 merchants                        │ │
│ │ [🤖 Categorize with AI] [📋 View List]             │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Category Edit Modal
```
┌─────────────────────────────────────┐
│ Edit Category: Food & Dining        │
├─────────────────────────────────────┤
│ Name: [Food & Dining          ]     │
│                                     │
│ Keywords (one per line):            │
│ ┌─────────────────────────────────┐ │
│ │ CARREFOUR                       │ │
│ │ LULU                            │ │
│ │ PAUL                            │ │
│ │ STARBUCKS                       │ │
│ │ [+ Add keyword]                 │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [🤖 AI Suggest Keywords]            │
│ [Cancel]  [Save Changes]            │
└─────────────────────────────────────┘
```

### AI Update Button Behavior

**At Category Level** (e.g., "Food & Dining" → 🤖 AI Update):
- Analyzes all "Other" transactions
- Suggests keywords to add to this category
- Shows preview: "AI suggests adding: SPINNEYS, WAITROSE (12 transactions)"
- User confirms → keywords added → transactions re-categorized

**At "Other" Category Level** (🤖 Categorize with AI):
- Sends all uncategorized merchants to LLM
- LLM suggests categories for each
- Shows confirmation dialog with changes
- Updates cache and re-categorizes

**Global Level** (🤖 Update All with AI):
- Re-runs LLM categorization for ALL "Other" merchants
- Updates `llm_categories.json` cache
- Re-categorizes transactions
- Shows summary: "✅ Categorized 45 merchants, 120 transactions updated"

## File Upload Feature

### Upload Flow
1. User clicks "Upload XLSX" button
2. Drag & drop or browse for ENBD Excel files
3. Backend runs pipeline: `import → clean → categorize`
4. Progress indicator shows: "Processing... (3/4 steps)"
5. Chart and table auto-refresh with new data
6. Show notification: "✅ Added 120 new transactions"

### Upload UI
- **Drag & drop zone**: "Drop ENBD XLSX files here"
- **Multi-file support**: Upload multiple files at once
- **Progress bar**: Show processing status
- **History**: List of uploaded files with timestamps

## Chart Specifications

### Stacked Column Chart
- **X-axis**: Time periods (weeks or months)
- **Y-axis**: Amount in AED
- **Stacks per column**: 2 groups
  1. **Income** (bottom, green): Salary + Incoming Transfer
  2. **Expenses** (top, stacked by category): All spending categories
- **Category order**: Largest → Smallest (bottom → top)
- **Colors**: 
  - Income: Green shades
  - Expenses: Distinct colors per category
- **Tooltip**: Show category name + amount on hover
- **Responsive**: Auto-resize, mobile-friendly

### Filters
1. **Date Range**: From/To date pickers
2. **Group By**: Dropdown (Week / Month)
3. **Categories**: Multi-select checkboxes with "Select All"

## Transaction List

### Display
- Table with sortable columns
- Pagination (50 rows per page)
- Same filters as chart
- **Total row**: Show sum of filtered transactions

### Columns
1. Date
2. Merchant
3. Category
4. Amount (color: red=expense, green=income)
5. Account

## Tech Stack (Modern & Dockerized)

**Backend**: FastAPI (Python 3.11+)
- Fast, async, auto-generated API docs
- Reuses existing ENBD analyzer pipeline
- File upload handling with streaming

**Frontend**: Next.js 14 + React + TypeScript
- Modern, fast, server-side rendering
- Recharts for visualizations
- TailwindCSS for styling
- shadcn/ui components

**Database**: SQLite (optional, for faster queries)
- Or direct CSV reading (simpler)

**Docker Stack**:
```yaml
services:
  backend:
    - FastAPI app
    - Python analyzer pipeline
    - Port 8000
  
  frontend:
    - Next.js app
    - Port 3000
  
  volumes:
    - ./data (shared between services)
    - ./config (categories + LLM cache)
```

## Features

### Must Have
✅ **File upload** via web UI (drag & drop)  
✅ **Stacked column chart** (income + expenses)  
✅ **Date range filter**  
✅ **Category multi-select filter**  
✅ **Week/Month grouping toggle**  
✅ **Transaction list** below chart  
✅ **Sync filters** between chart and list  
✅ **Category management UI**  
✅ **AI categorization button**  
✅ **Docker Compose** deployment  

### Nice to Have
- Export chart as PNG
- Export filtered data as CSV
- Dark mode
- Save filter presets
- Upload history with rollback
- Real-time progress for large files
- Email notifications (new uploads)

## API Endpoints

```
POST /api/upload
  - Upload XLSX files
  - Returns: { job_id, status: "processing" }

GET /api/upload/{job_id}
  - Check processing status
  - Returns: { status: "completed", transactions_added: 120 }

GET /api/data
  ?from=2025-01-01
  &to=2025-12-31
  &categories=Food,Shopping
  &groupby=week
  - Returns: { 
      chart_data: [...], 
      transactions: [...], 
      totals: { income: X, expenses: Y } 
    }

GET /api/categories
  - Returns: [ "Food & Dining", "Shopping", ... ]

GET /api/categories/rules
  - Returns: { 
      "Food & Dining": ["CARREFOUR", "LULU", ...],
      "Shopping": ["IKEA", "H&M", ...] 
    }

PUT /api/categories/rules
  - Update category rules
  - Body: { category: "Food", add_keywords: ["SPINNEYS"], remove_keywords: ["IKEA"] }
  - Returns: { success: true, updated_count: 2 }

POST /api/categories/recategorize
  - Re-run AI categorization
  - Body: { scope: "all" | category: "Other" | merchant: "UNKNOWN" }
  - Returns: { job_id, status: "processing" }

GET /api/stats
  - Returns: { 
      total_transactions: 542,
      date_range: { from: "...", to: "..." },
      accounts: [ "Current", "Savings", ... ]
    }
```

## File Structure
```
enbd-chart-app/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── upload.py            # File upload handler
│   │   ├── pipeline.py          # Run ENBD analyzer
│   │   └── data_api.py          # Data filtering + aggregation
│   ├── requirements.txt
│   └── enbd_analyzer/           # Copy of analyzer package
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Main dashboard
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── UploadZone.tsx   # Drag & drop upload
│   │   │   ├── Chart.tsx        # Stacked column chart
│   │   │   ├── Filters.tsx      # Filter controls
│   │   │   └── Table.tsx        # Transaction list
│   │   └── lib/
│   │       └── api.ts           # API client
│   ├── package.json
│   └── tailwind.config.js
├── data/                        # Shared volume
├── config/                      # Shared volume
└── README.md
```

## Docker Compose Setup

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
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL}
    restart: unless-stopped
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  data:
  config:
```

## Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd enbd-chart-app

# 2. Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# 3. Run with Docker
docker-compose up -d

# 4. Access app
open http://localhost:3000

# 5. Upload ENBD XLSX files via UI
# Done! 🎉
```

## Success Criteria
1. ✅ Chart displays in < 2 seconds
2. ✅ Filters apply instantly (< 500ms)
3. ✅ Works on mobile (responsive)
4. ✅ No Excel needed!

