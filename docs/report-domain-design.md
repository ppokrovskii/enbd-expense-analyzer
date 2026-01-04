# Report Domain

**Module**: `app/domains/reports/`  
**Routes**: `/reports/*`

---

## Responsibility

PDF/Excel generation orchestrator (7 sections), calls Recurring & Insights domains

---

## Key APIs

```
POST /reports/generate           → Background job, returns report_id
GET  /reports/{id}               → Report metadata
POST /reports/{id}/export/pdf    → Generate PDF, upload to S3
```

---

## Database

```sql
reports (
  id, person_id, date_from, date_to,
  total_income, total_expenses, net_balance,
  summary_takeaway, trends_content, insights_content,
  pdf_url, excel_url, status
)
```

---

## Generation Flow

```python
async def generate_report(person_id, date_from, date_to):
    # Parallel processing (direct calls)
    transactions = await transaction_service.get_transactions(...)
    recurring = await recurring_service.detect_patterns(...)
    insights = await insights_service.generate_insights(...)
    
    # Render PDF (7 sections)
    pdf = render_template(report_template, data)
    pdf_url = await s3.upload(pdf)
    
    # Notify user
    await notification_service.send(person_id, "report.generated")
```

---

## PDF Structure (7 Sections)

1. Summary (income, expenses, balance, takeaway)
2. Expense Overview (top categories, chart)
3. Category Details (per category breakdown)
4. Subscriptions & Recurring
5. Trends & Anomalies (5 bullets, AI-generated)
6. Key Insights (3-5 bullets, plain language, NO advice)
7. Next Steps (static guidance)

---

**Dependencies**: Transaction, Recurring, Insights, S3, Notification  
**Status**: Ready
