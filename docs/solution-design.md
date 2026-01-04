# ENBD Expense Analyzer - Solution Design

**Architecture**: Modular Monolith  
**Stack**: FastAPI + PostgreSQL + Redis + Next.js  
**LLM**: GPT-5.2 (user-configurable)

---

## Domains (9 Modules)

| Domain | Routes | Responsibility |
|--------|--------|---------------|
| **Auth** | `/auth/*` | Auth0, persons, context switching |
| **Transactions** | `/transactions/*` | Import XLSX, dedupe, multi-bank, **Excel export** |
| **Categories** | `/categories/*`, `/rules/*` | Rules + **LLM generates rules** + **Rule Manager** |
| **Chat** | `/chat/*` | AI assistant, tool calling |
| **Reports** | `/reports/*` | Customizable PDF reports (WYSIWYG), section-based |
| **Recurring** | Internal | Pattern detection (hybrid) |
| **Insights** | Internal | Trends, anomalies (hybrid) |
| **Payments** | `/subscriptions/*` | Stripe, freemium |
| **Notifications** | `/ws` | WebSocket |
| **Admin** | `/admin/*` | LLM model config |

---

## Key Flows

**Import → Categorize**
```
POST /transactions/import → Parse → Dedupe → Insert
→ Apply rules → For unmatched: LLM generates rule → Save → Apply
```

**Report Building**
```
POST /reports/ → Create empty report with auto-name
→ User adds sections (+ Add Section button)
→ Each section: set filters, generate AI content, rename title
→ Reorder sections (up/down buttons)
→ Export PDF (WYSIWYG rendering)
```

**Person Switch**
```
PUT /persons/{id}/activate → Update active_person_id
→ Frontend refreshes all data
```

**Rule Manager**
```
/categories/rules?merchants=X,Y&category=Z&search=ABC&status=uncategorized
→ GET /api/rules/merchants (aggregated with rule match)
→ Inline edit → PUT /api/rules/{id}
→ Bulk assign → POST /api/rules/bulk-assign
→ AI suggest → POST /api/categories/ai-bulk-suggest
```

---

## Database

```sql
users (id, auth0_user_id, email, subscription_tier, active_person_id)
persons (id, owner_user_id, name)
user_settings (user_id, preferred_llm_model DEFAULT 'gpt-5.2')
transactions (id, person_id, hash, date, merchant, category, amount_signed)
categories (id, person_id, name, color)
rules (id, person_id, category_id, field, operator, value, priority)
chat_sessions (id, person_id, total_tokens, total_cost_usd)

-- Reports (new structure)
reports (id, person_id, name, created_at, updated_at)
report_sections (
  id, report_id, section_type, position, 
  custom_title,      -- nullable, overrides auto-generated
  filters_json,      -- {start_date, end_date, group_by?}
  content_json,      -- {takeaway?, bullets?, ...}
  created_at, updated_at
)
```

---

## Technology

**Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic  
**AI**: OpenAI GPT-5.2, Pandas, NumPy, SciPy  
**Auth**: Auth0  
**DB**: PostgreSQL 15, Redis 7  
**Payments**: Stripe  
**Frontend**: Next.js 14, TailwindCSS, shadcn/ui  
**PDF Export**: WeasyPrint or Puppeteer (WYSIWYG rendering)

---

## Key Features

✅ Auth0 (enterprise auth)  
✅ Multi-person (isolated data, context switching)  
✅ Freemium (1000 free, unlimited premium)  
✅ Multi-bank (ENBD, FAB, WIO)  
✅ Rule-based categorization (**LLM generates rules**)  
✅ Hybrid AI (95% cost savings)  
✅ AI Chat (tool calling, 1000 txn context)  
✅ **Customizable PDF Reports** (section-based, WYSIWYG)  
✅ Real-time (WebSocket)  
✅ User-configurable LLM

---

## Report System Design

### Report Structure
- Report = container with name + ordered list of sections
- Each section is independent: own type, filters, title, content
- Summary section is always first (not removable)

### Section Types
1. **Summary** — metrics + takeaway (always present)
2. **Expense Overview** — chart (weekly/monthly grouping)
3. **Top Spending Categories** — bar breakdown
4. **Category Details** — per-category transaction lists
5. **Subscriptions & Recurring** — detected patterns
6. **Trends & Anomalies** — AI-generated bullets
7. **Key Insights** — AI-generated bullets

### Section Features
- Independent date filters per section
- Renamable titles (custom or auto-generated)
- Move up/down for reordering
- AI generation for applicable sections

### Export
- PDF only (WYSIWYG — renders exactly as web)
- Excel export is in Transactions domain, not Reports

### Reports List
- Shows all reports across all persons for user
- Filter by person
- Actions: Open, Rename, Delete, Duplicate

---

## Detailed Designs

See: [auth](./auth-domain-design.md), [transaction](./transaction-domain-design.md), [category](./category-domain-design.md), [chat](./chat-domain-design.md), [report](./report-domain-design.md), [recurring](./recurring-domain-design.md), [insights](./insights-domain-design.md), [payment](./payment-domain-design.md), [notification](./notification-domain-design.md), [frontend](./frontend-design.md)

---

**Status**: Ready for implementation  
**Version**: 5.0 (Reports Refactored)  
**Date**: 2026-01-04
