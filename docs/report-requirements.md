# Personal Finance Report — Requirements

## Overview
Create customizable, shareable PDF reports for sub-accounts (customer, wife, friend). Reports are built incrementally by adding sections with independent filters. PDF export renders exactly as the web page (WYSIWYG).

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

## Output Format
- **PDF only**: Multi-page, WYSIWYG — looks exactly like web page (without buttons and interactive elements)
- **Excel export**: Available via Transactions page (not part of Reports)

---

## Report Creation Workflow

### 1. Create New Report
- Click "New Report" button
- Report is created empty with auto-generated name:
  - First report: `"{Person Name} Report"`
  - Subsequent reports: `"{Person Name} Report 2"`, `"{Person Name} Report 3"`, etc.
- Report name is **editable** (click to rename)

### 2. Initial Report View
New report opens with:
- **Quick Filters** (same as Transactions page): month buttons, day ranges, custom date picker
- **Summary Section** (always present, not removable):
  - Period display (from quick filters)
  - Total Income, Total Expenses, Net Balance metric cards
  - Editable Summary Takeaway + "Generate with AI" button
- Default filters: same as Transactions page defaults

### 3. Add Sections
- **"+ Add Section"** button at bottom of report
- Opens section type selector (list/dropdown)
- Same section type can be added **multiple times**
- Each section instance has **independent filters**

### 4. Section Types

| Section Type | Has Filters | Has AI Generate | Notes |
|--------------|-------------|-----------------|-------|
| Expense Overview | Yes (dates + Weekly/Monthly) | No | Chart visualization |
| Top Spending Categories | Yes (dates) | No | Category breakdown bars |
| Category Details | Yes (dates) | No | Per-category transaction lists |
| Subscriptions & Recurring | Yes (dates) | Yes (Detect) | List with monthly/annualized costs |
| Trends & Anomalies | Yes (dates) | Yes (Generate) | Editable bullet list (max 5) |
| Key Insights | Yes (dates) | Yes (Generate) | Editable bullet list (3-5) |

### 5. Section Filters
- Each section has a **"Filters"** button (icon)
- Clicking opens a **popup/modal** with:
  - Quick date presets (same as main page)
  - Custom date range (from/to)
  - Weekly/Monthly toggle (Expense Overview only)
- Filters are **not shown inline** on the report page

### 6. Section Title

**Auto-generated title** based on filters:
- Format: `"{Grouping} {Section Name} for {date range}"`
- Examples:
  - `"Monthly Expense Overview for Jan 1, 2025 – Dec 31, 2025"`
  - `"Weekly Expense Overview for Oct 1, 2025 – Dec 31, 2025"`
  - `"Top Spending Categories for Nov 1, 2025 – Nov 30, 2025"`

**Note**: Weekly/Monthly prefix only applies to Expense Overview section.

**Custom title**: User can **rename any section title** by clicking on it. Custom title overrides the auto-generated one.

### 7. Section Actions
Each section has:
- **Title** (click to edit/rename)
- **Filters** button (opens filter popup)
- **Move Up / Move Down** buttons (reorder sections)
- **Delete** button (removes section from report)

### 8. Export to PDF
- **Export PDF** button at top of report
- PDF renders **exactly as web page** (WYSIWYG)
- Excludes: buttons, filter popups, interactive elements
- Includes: all sections in order with their content and visualizations

---

## Reports List View

- Shows reports from **all persons** for current user
- Grouped by person or flat list with person indicator
- Each report shows: Name, Person, Created date, Last modified
- Actions: Open, Rename, Delete, Duplicate
- Sort by: Name, Person, Created, Modified
- Filter by: Person

---

## Recurring Transactions

**Data**: `Transaction.is_recurring`, `recurrence_group_id`, `recurrence_confidence`

**Detection** (AI):
- Similar description (80%+ fuzzy), amount (±5%), frequency (weekly/monthly/quarterly)
- Min 3 occurrences

**UI Integration**:
- "Detect Recurring" button in Subscriptions & Recurring section
- Filter: "Show recurring only" on Transactions page
- AI chat command: "Find recurring transactions"

---

## Data Model

**Person**: id, owner_user_id, name, created_at

**Report**: id, person_id, name, created_at, updated_at

**ReportSection**: id, report_id, section_type, position, custom_title, filters_json, content_json, created_at, updated_at
- `section_type`: enum (summary, expense_overview, top_categories, category_details, recurring, trends, insights)
- `position`: integer for ordering
- `custom_title`: string, nullable — if set, overrides auto-generated title
- `filters_json`: {start_date, end_date, group_by?}
- `content_json`: {takeaway?, bullets?, ...} — editable AI content

**Transaction** (extended): person_id, is_recurring, recurrence_group_id, recurrence_confidence

**Category**: person_id

**UserAccount**: person_id

**ChatSession**: person_id

---

## API Endpoints

**Reports**:
- `GET /api/reports/` — list all reports for current user (all persons)
- `GET /api/reports/?person_id={id}` — list reports for specific person
- `POST /api/reports/` — create new report (returns with auto-generated name)
- `GET /api/reports/{id}` — get report with all sections
- `PUT /api/reports/{id}` — update report (rename)
- `DELETE /api/reports/{id}` — delete report

**Report Sections**:
- `POST /api/reports/{id}/sections` — add section to report
- `PUT /api/reports/{id}/sections/{section_id}` — update section (title, filters, content)
- `DELETE /api/reports/{id}/sections/{section_id}` — remove section
- `PUT /api/reports/{id}/sections/{section_id}/move` — move section up or down (body: {direction: "up" | "down"})

**AI Generation**:
- `POST /api/reports/sections/{section_id}/generate` — generate AI content for section

**Export**:
- `POST /api/reports/{id}/export/pdf` — export as PDF (WYSIWYG)

**Persons**: GET/POST/DELETE `/api/persons`, PUT `/api/persons/{id}/activate`

**Recurring**: POST `/api/transactions/detect-recurring`, GET `/api/transactions/recurring`

---

## Quality Bar

- Report creation: < 30 seconds to first useful report
- Section add: < 1 second
- AI generation: < 10s/section
- PDF export: < 10s (WYSIWYG rendering)
- Recurring detection: > 90% accuracy
- Zero financial advice in AI content

---

## UI/UX Notes

1. **Report feels like a canvas** — user builds it up section by section
2. **Sections are self-contained** — each has its own data scope and title
3. **Titles are editable** — click to rename any section
4. **Filters are hidden by default** — clean report view, filter popup on demand
5. **Simple reordering** — up/down buttons, not drag-and-drop
6. **Multiple instances allowed** — compare different time periods side-by-side
7. **Summary is always first** — provides context for the rest of the report
8. **WYSIWYG PDF** — what you see is what you export
9. **Cross-person view** — reports list shows all persons for quick access
