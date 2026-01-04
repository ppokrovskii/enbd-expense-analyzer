# Personal Finance Report — Requirements

## Overview
Generate shareable PDF/Excel reports for sub-accounts (customer, wife, friend). User uploads their transactions and creates reports with AI insights.

## Multi-Person Management

**Concept**: User manages multiple "persons" (wife, friend, customer) under single login

**Context Switching**:
- Header dropdown: "John Doe ▼" → Select person or "Add New Person"
- Add person: Enter name only (no separate login/account)
- **Full context switch**: Selected person becomes active across entire app
- Each person has **isolated**:
  - Transactions (own XLSX uploads)
  - Accounts (own bank account numbers)
  - Categories (own rules & colors)
  - AI chat history (own sessions)
  - Reports (own generated reports)

**UI Behavior**:
- All pages (Transactions, Categories, Chat, Settings, Reports) show active person's data
- Upload files → goes to active person
- Create categories → for active person
- Active person indicator always visible in header
- User can delete person (cascades all their data)

## Output Formats
- **PDF**: 5–7 pages, all details below
- **Excel**: Single sheet, same columns as Transactions page

---

## PDF Structure (7 sections)

**1. Summary**
- Period, total income, total expenses, net balance
- Editable takeaway (1 paragraph) + AI generation button (not in PDF)

**2. Expense Overview**
- Top 5–7 categories: Amount + % of total
- Simple bar chart

**3. Category Details**
- Per category: Total, transaction count, top 3–5 descriptions

**4. Subscriptions & Recurring**
- List recurring transactions: Monthly + annualized cost
- AI detection button (not in PDF)

**5. Trends & Anomalies** (AI-generated, editable)
- Max 5 bullets: Spikes, growth, large one-offs

**6. Key Insights** (AI-generated, editable)
- 3–5 insights, plain language
- No advice, no benchmarking

**7. Next Steps** (Static text)
- "Review top 2–3 categories..."
- "Check recurring charges..."
- "Re-run after a few months..."

---

## Recurring Transactions

**Data**: `Transaction.is_recurring`, `recurrence_group_id`, `recurrence_confidence`

**Detection** (AI):
- Similar description (80%+ fuzzy), amount (±5%), frequency (weekly/monthly/quarterly)
- Min 3 occurrences

**UI Integration**:
- Button on Reports page, Transactions page
- Filter: "Show recurring only"
- AI chat command: "Find recurring transactions"

---

## Report Generation Flow

1. Switch to target person (if not already active)
2. Navigate to Reports page
3. Date range (presets: 30/60/90 days, quarter, year, custom)
4. Optional: Include/exclude categories, filter accounts
5. Generate AI content (Summary, Recurring, Trends, Insights) — all editable
6. Export PDF or Excel

---

## Data Model

**Person**: id, owner_user_id, name, created_at

**Report**: id, person_id, date_from, date_to, summary_takeaway, trends_content, insights_content, recurring_detected_at, timestamps

**Transaction** (extended): person_id, is_recurring, recurrence_group_id, recurrence_confidence

**Category**: person_id (all existing tables get person_id foreign key)

**UserAccount**: person_id

**ChatSession**: person_id

---

## API Endpoints

**Persons**: GET/POST/DELETE `/api/persons`, PUT `/api/persons/{id}/activate` (set active context)

**Reports**: POST `/api/reports/generate`, GET/PUT `/api/reports/{id}`, POST `/api/reports/{id}/export/pdf|excel`

**Recurring**: POST `/api/transactions/detect-recurring`, PUT `/api/transactions/{id}/recurring`, GET `/api/transactions/recurring`

**AI**: POST `/api/ai/generate-summary|trends|insights|detect-recurring`

---

## Quality Bar

- Readable in < 10 minutes
- PDF: 11pt+ font, clean design, 2–3 colors, printer-friendly
- Report creation: < 2 min
- Performance: Report < 5s, AI < 10s/section, PDF < 3s, Excel < 2s
- Recurring detection: > 90% accuracy
- Zero financial advice

