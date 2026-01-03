# ENBD Expense Analyzer - Solution Design

**Architecture**: Modular Monolith  
**Stack**: FastAPI + PostgreSQL + Redis + Next.js  
**LLM**: GPT-5.2 (user-configurable)

---

## Domains (9 Modules)

| Domain | Routes | Responsibility |
|--------|--------|---------------|
| **Auth** | `/auth/*` | Auth0, persons, context switching |
| **Transactions** | `/transactions/*` | Import XLSX, dedupe, multi-bank |
| **Categories** | `/categories/*`, `/rules/*` | Rules + **LLM generates rules** |
| **Chat** | `/chat/*` | AI assistant, tool calling |
| **Reports** | `/reports/*` | PDF (7 sections), Excel |
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

**Generate Report**
```
POST /reports/generate → Background job
→ Get transactions + recurring + insights (parallel)
→ Render PDF → Upload S3 → WebSocket: "report.generated"
```

**Person Switch**
```
PUT /persons/{id}/activate → Update active_person_id
→ Frontend refreshes all data
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
reports (id, person_id, date_from, date_to, pdf_url, status)
```

---

## Technology

**Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic  
**AI**: OpenAI GPT-5.2, Pandas, NumPy, SciPy  
**Auth**: Auth0  
**DB**: PostgreSQL 15, Redis 7  
**Payments**: Stripe  
**Frontend**: Next.js 14, TailwindCSS, shadcn/ui

---

## Key Features

✅ Auth0 (enterprise auth)  
✅ Multi-person (isolated data, context switching)  
✅ Freemium (1000 free, unlimited premium)  
✅ Multi-bank (ENBD, FAB, WIO)  
✅ Rule-based categorization (**LLM generates rules**)  
✅ Hybrid AI (95% cost savings)  
✅ AI Chat (tool calling, 1000 txn context)  
✅ PDF Reports (7 sections, AI content)  
✅ Real-time (WebSocket)  
✅ User-configurable LLM

---

## Detailed Designs

See: [auth](./auth-domain-design.md), [transaction](./transaction-domain-design.md), [category](./category-domain-design.md), [chat](./chat-domain-design.md), [report](./report-domain-design.md), [recurring](./recurring-domain-design.md), [insights](./insights-domain-design.md), [payment](./payment-domain-design.md), [notification](./notification-domain-design.md), [frontend](./frontend-design.md)

---

**Status**: Ready for implementation  
**Version**: 4.0 (Ultra-Lean)  
**Date**: 2025-01-03
