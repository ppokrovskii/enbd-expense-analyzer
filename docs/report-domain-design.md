# Report Domain

**Module**: `app/domains/reports/`  
**Routes**: `/reports/*`

---

## Responsibility

Customizable PDF report builder with section-based architecture. User creates reports, adds sections with independent filters, and exports to PDF (WYSIWYG).

---

## Key APIs

### Reports
```
GET  /reports/                              → List all reports (all persons for user)
GET  /reports/?person_id={id}               → List reports for specific person
POST /reports/                              → Create empty report with auto-name
GET  /reports/{id}                          → Get report with all sections
PUT  /reports/{id}                          → Update report (rename)
DELETE /reports/{id}                        → Delete report
```

### Report Sections
```
POST /reports/{id}/sections                 → Add section to report
PUT  /reports/{id}/sections/{section_id}    → Update section (title, filters, content)
DELETE /reports/{id}/sections/{section_id}  → Remove section
PUT  /reports/{id}/sections/{section_id}/move → Move section up/down
```

### AI Generation
```
POST /reports/sections/{section_id}/generate → Generate AI content for section
```

### Export
```
POST /reports/{id}/export/pdf               → Export as PDF (WYSIWYG)
```

---

## Database

```sql
reports (
  id SERIAL PRIMARY KEY,
  person_id INTEGER REFERENCES persons(id),
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)

report_sections (
  id SERIAL PRIMARY KEY,
  report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
  section_type VARCHAR(50) NOT NULL,  -- enum
  position INTEGER NOT NULL DEFAULT 0,
  custom_title VARCHAR(255),          -- nullable, overrides auto-generated
  filters_json JSONB,                 -- {start_date, end_date, group_by?}
  content_json JSONB,                 -- {takeaway?, bullets?, chart_data?}
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)
```

### Section Types Enum
- `summary` — always first, not removable
- `expense_overview` — chart with weekly/monthly toggle
- `top_categories` — category breakdown bars
- `category_details` — per-category transaction lists
- `recurring` — subscriptions & recurring patterns
- `trends` — trends & anomalies bullets
- `insights` — key insights bullets

---

## Report Creation Flow

```python
async def create_report(person_id: int):
    # Auto-generate name
    existing_count = await count_reports(person_id)
    person = await get_person(person_id)
    
    if existing_count == 0:
        name = f"{person.name} Report"
    else:
        name = f"{person.name} Report {existing_count + 1}"
    
    # Create report
    report = await create_report(person_id=person_id, name=name)
    
    # Add default Summary section
    await add_section(
        report_id=report.id,
        section_type="summary",
        position=0,
        filters_json=default_filters()  # same as Transactions page
    )
    
    return report
```

---

## Section Management

### Add Section
```python
async def add_section(report_id: int, section_type: str):
    # Get max position
    max_pos = await get_max_position(report_id)
    
    # Default filters (inherit from report/summary)
    filters = default_section_filters()
    
    section = ReportSection(
        report_id=report_id,
        section_type=section_type,
        position=max_pos + 1,
        filters_json=filters
    )
    return await save(section)
```

### Move Section
```python
async def move_section(section_id: int, direction: str):
    section = await get_section(section_id)
    sections = await get_all_sections(section.report_id)
    
    # Summary (position 0) cannot be moved
    if section.section_type == "summary":
        raise ValueError("Summary section cannot be moved")
    
    current_idx = sections.index(section)
    
    if direction == "up" and current_idx > 1:  # Can't go above Summary
        swap_positions(sections[current_idx], sections[current_idx - 1])
    elif direction == "down" and current_idx < len(sections) - 1:
        swap_positions(sections[current_idx], sections[current_idx + 1])
```

### Update Section Title
```python
async def update_section(section_id: int, custom_title: str = None, ...):
    section = await get_section(section_id)
    
    if custom_title is not None:
        section.custom_title = custom_title  # None clears custom title
    
    # ... update other fields
    return await save(section)
```

---

## Section Title Generation

```python
def generate_section_title(section: ReportSection) -> str:
    # Custom title takes precedence
    if section.custom_title:
        return section.custom_title
    
    # Auto-generate based on type and filters
    filters = section.filters_json
    date_range = format_date_range(filters.start_date, filters.end_date)
    
    type_names = {
        "summary": "Summary",
        "expense_overview": "Expense Overview",
        "top_categories": "Top Spending Categories",
        "category_details": "Category Details",
        "recurring": "Subscriptions & Recurring",
        "trends": "Trends & Anomalies",
        "insights": "Key Insights"
    }
    
    base_name = type_names[section.section_type]
    
    # Add grouping prefix for expense_overview
    if section.section_type == "expense_overview":
        grouping = filters.get("group_by", "monthly").capitalize()
        return f"{grouping} {base_name} for {date_range}"
    
    return f"{base_name} for {date_range}"
```

---

## PDF Export (WYSIWYG)

```python
async def export_pdf(report_id: int) -> bytes:
    report = await get_report_with_sections(report_id)
    
    # Render HTML exactly as web page
    html = render_report_html(report)
    
    # Convert to PDF using headless browser
    pdf = await html_to_pdf(html)
    
    return pdf
```

### PDF Rendering Notes
- Uses headless browser (Puppeteer/Playwright) for WYSIWYG
- Excludes: buttons, filter popups, interactive elements
- Includes: all charts, tables, content as displayed
- Page breaks between sections (optional)

---

## Reports List (All Persons)

```python
async def list_reports(user_id: int, person_id: int = None):
    # Get all persons for user
    persons = await get_persons(user_id)
    person_ids = [p.id for p in persons]
    
    query = select(Report).where(Report.person_id.in_(person_ids))
    
    if person_id:
        query = query.where(Report.person_id == person_id)
    
    return await db.execute(query.order_by(Report.updated_at.desc()))
```

---

## Dependencies

- **Transaction Domain**: Get transactions for sections
- **Recurring Domain**: Detect patterns for recurring section
- **Insights Domain**: Generate trends/insights content
- **Person Domain**: Get person info for naming

---

**Status**: Ready for implementation
