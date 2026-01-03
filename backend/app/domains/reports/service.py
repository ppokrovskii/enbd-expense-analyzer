"""Service for generating financial reports (PDF/Excel)."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from collections import defaultdict
from pathlib import Path
import uuid
import io
import os

from app.domains.transactions.models import Transaction
from app.domains.recurring.service import RecurringDetectionService
from app.domains.insights.service import InsightsService
from app.domains.reports.models import (
    Report,
    ReportFormat,
    ReportType,
    ReportStatus,
    ReportData,
    CategorySummary,
    PeriodSummary,
)


# Report output directory
REPORTS_DIR = Path(__file__).parent.parent.parent / "generated_reports"


class ReportService:
    """Service for generating financial reports."""
    
    @classmethod
    def generate_report(
        cls,
        db: Session,
        user_id: str,
        report_type: ReportType,
        report_format: ReportFormat,
        period_start: date,
        period_end: date,
        person_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Report:
        """
        Generate a financial report.
        
        Args:
            db: Database session
            user_id: User identifier
            report_type: Type of report
            report_format: Output format (PDF, Excel, JSON)
            period_start: Start date of report period
            period_end: End date of report period
            person_id: Optional person ID for filtering
            title: Optional custom title
            
        Returns:
            Report database record with file path
        """
        # Create report record
        report_title = title or cls._generate_title(report_type, period_start, period_end)
        
        report = Report(
            user_id=user_id,
            person_id=int(person_id) if person_id else None,
            report_type=report_type.value,
            report_format=report_format.value,
            title=report_title,
            status=ReportStatus.GENERATING.value,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        try:
            # Gather report data
            report_data = cls._gather_report_data(
                db, user_id, period_start, period_end, report_title, person_id
            )
            
            # Generate file based on format
            if report_format == ReportFormat.PDF:
                file_path, file_size = cls._generate_pdf(report_data, str(report.id))
            elif report_format == ReportFormat.EXCEL:
                file_path, file_size = cls._generate_excel(report_data, str(report.id))
            else:  # JSON
                file_path, file_size = cls._generate_json(report_data, str(report.id))
            
            # Update report record
            report.status = ReportStatus.COMPLETED.value
            report.file_path = file_path
            report.file_size = file_size
            report.completed_at = datetime.utcnow()
            report.metadata_json = report_data.to_dict()
            db.commit()
            
        except Exception as e:
            report.status = ReportStatus.FAILED.value
            report.error_message = str(e)
            db.commit()
            raise
        
        return report
    
    @classmethod
    def _generate_title(cls, report_type: ReportType, start: date, end: date) -> str:
        """Generate report title based on type and period."""
        if report_type == ReportType.MONTHLY_SUMMARY:
            return f"Monthly Financial Report - {start.strftime('%B %Y')}"
        elif report_type == ReportType.QUARTERLY_SUMMARY:
            quarter = (start.month - 1) // 3 + 1
            return f"Q{quarter} {start.year} Financial Report"
        elif report_type == ReportType.ANNUAL_SUMMARY:
            return f"Annual Financial Report - {start.year}"
        elif report_type == ReportType.CATEGORY_BREAKDOWN:
            return f"Category Analysis - {start.strftime('%b %d')} to {end.strftime('%b %d, %Y')}"
        else:
            return f"Financial Report - {start.strftime('%b %d')} to {end.strftime('%b %d, %Y')}"
    
    @classmethod
    def _gather_report_data(
        cls,
        db: Session,
        user_id: str,
        period_start: date,
        period_end: date,
        title: str,
        person_id: Optional[str] = None,
    ) -> ReportData:
        """Gather all data needed for report generation."""
        # Fetch transactions
        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= period_start,
            Transaction.date <= period_end,
        )
        if person_id:
            query = query.filter(Transaction.person_id == int(person_id))
        
        transactions = query.order_by(Transaction.date).all()
        
        # Calculate totals
        total_income = sum(
            float(t.amount_signed) for t in transactions 
            if t.amount_signed and t.amount_signed > 0
        )
        total_expenses = sum(
            abs(float(t.amount_signed)) for t in transactions 
            if t.amount_signed and t.amount_signed < 0
        )
        
        # Category breakdown
        category_data = cls._calculate_category_breakdown(transactions, total_expenses)
        
        # Monthly trends
        monthly_trends = cls._calculate_monthly_trends(transactions)
        
        # Weekly trends  
        weekly_trends = cls._calculate_weekly_trends(transactions)
        
        # Get accounts
        accounts = list(set(t.account for t in transactions if t.account))
        
        # Get insights
        insights_report = InsightsService.generate_insights(
            db, user_id, 
            period_days=(period_end - period_start).days,
            person_id=person_id
        )
        insights = [i.to_dict() for i in insights_report.insights[:10]]
        
        # Get recurring patterns
        recurring_result = RecurringDetectionService.detect_patterns(
            db, user_id, period_start, period_end, person_id
        )
        recurring = [g.to_dict() for g in recurring_result.recurring_groups[:10]]
        
        return ReportData(
            title=title,
            subtitle=f"{period_start.strftime('%B %d, %Y')} - {period_end.strftime('%B %d, %Y')}",
            period_start=period_start,
            period_end=period_end,
            generated_at=datetime.utcnow(),
            total_income=total_income,
            total_expenses=total_expenses,
            net_change=total_income - total_expenses,
            transaction_count=len(transactions),
            categories=category_data,
            monthly_trends=monthly_trends,
            weekly_trends=weekly_trends,
            insights=insights,
            recurring=recurring,
            account_names=accounts,
        )
    
    @classmethod
    def _calculate_category_breakdown(
        cls,
        transactions: List[Transaction],
        total_expenses: float,
    ) -> List[CategorySummary]:
        """Calculate category-wise spending breakdown."""
        category_txns = defaultdict(list)
        
        for txn in transactions:
            if txn.amount_signed and txn.amount_signed < 0:
                category = txn.category or "Other"
                category_txns[category].append(txn)
        
        summaries = []
        for category, txns in category_txns.items():
            total = sum(abs(float(t.amount_signed)) for t in txns)
            
            # Top merchants
            merchant_totals = defaultdict(float)
            for t in txns:
                merchant = t.merchant or t.description or "Unknown"
                merchant_totals[merchant] += abs(float(t.amount_signed))
            
            top_merchants = [
                {"name": m, "total": round(t, 2)}
                for m, t in sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            summaries.append(CategorySummary(
                name=category,
                total=total,
                transaction_count=len(txns),
                percentage=(total / total_expenses * 100) if total_expenses > 0 else 0,
                average_transaction=total / len(txns) if txns else 0,
                top_merchants=top_merchants,
            ))
        
        # Sort by total descending
        summaries.sort(key=lambda x: x.total, reverse=True)
        return summaries
    
    @classmethod
    def _calculate_monthly_trends(cls, transactions: List[Transaction]) -> List[PeriodSummary]:
        """Calculate monthly spending trends."""
        monthly_data = defaultdict(lambda: {"total": 0, "count": 0, "start": None, "end": None})
        
        for txn in transactions:
            if txn.amount_signed and txn.amount_signed < 0:
                key = txn.date.strftime("%Y-%m")
                monthly_data[key]["total"] += abs(float(txn.amount_signed))
                monthly_data[key]["count"] += 1
                
                if not monthly_data[key]["start"] or txn.date < monthly_data[key]["start"]:
                    monthly_data[key]["start"] = txn.date
                if not monthly_data[key]["end"] or txn.date > monthly_data[key]["end"]:
                    monthly_data[key]["end"] = txn.date
        
        trends = []
        for key in sorted(monthly_data.keys()):
            data = monthly_data[key]
            trends.append(PeriodSummary(
                label=datetime.strptime(key, "%Y-%m").strftime("%b %Y"),
                total=data["total"],
                transaction_count=data["count"],
                start_date=data["start"],
                end_date=data["end"],
            ))
        
        return trends
    
    @classmethod
    def _calculate_weekly_trends(cls, transactions: List[Transaction]) -> List[PeriodSummary]:
        """Calculate weekly spending trends."""
        weekly_data = defaultdict(lambda: {"total": 0, "count": 0, "start": None, "end": None})
        
        for txn in transactions:
            if txn.amount_signed and txn.amount_signed < 0:
                # Get week start (Monday)
                week_start = txn.date - timedelta(days=txn.date.weekday())
                key = week_start.isoformat()
                
                weekly_data[key]["total"] += abs(float(txn.amount_signed))
                weekly_data[key]["count"] += 1
                
                if not weekly_data[key]["start"] or txn.date < weekly_data[key]["start"]:
                    weekly_data[key]["start"] = txn.date
                if not weekly_data[key]["end"] or txn.date > weekly_data[key]["end"]:
                    weekly_data[key]["end"] = txn.date
        
        trends = []
        for key in sorted(weekly_data.keys()):
            data = weekly_data[key]
            week_start = date.fromisoformat(key)
            trends.append(PeriodSummary(
                label=f"Week of {week_start.strftime('%b %d')}",
                total=data["total"],
                transaction_count=data["count"],
                start_date=data["start"] or week_start,
                end_date=data["end"] or week_start,
            ))
        
        return trends[-12:]  # Last 12 weeks
    
    @classmethod
    def _generate_pdf(cls, data: ReportData, report_id: str) -> Tuple[str, int]:
        """Generate PDF report using reportlab."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except ImportError:
            # Fallback: generate a simple text-based PDF structure
            return cls._generate_simple_pdf(data, report_id)
        
        # Ensure output directory exists
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REPORTS_DIR / f"{report_id}.pdf"
        
        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
        )
        story.append(Paragraph(data.title, title_style))
        story.append(Paragraph(data.subtitle, styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        
        # Summary
        story.append(Paragraph("Summary", styles['Heading2']))
        summary_data = [
            ["Total Income", f"AED {data.total_income:,.2f}"],
            ["Total Expenses", f"AED {data.total_expenses:,.2f}"],
            ["Net Change", f"AED {data.net_change:,.2f}"],
            ["Transactions", str(data.transaction_count)],
        ]
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Category Breakdown
        story.append(Paragraph("Spending by Category", styles['Heading2']))
        cat_data = [["Category", "Amount", "% of Total", "Transactions"]]
        for cat in data.categories[:10]:
            cat_data.append([
                cat.name,
                f"AED {cat.total:,.2f}",
                f"{cat.percentage:.1f}%",
                str(cat.transaction_count),
            ])
        
        cat_table = Table(cat_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Monthly Trends
        if data.monthly_trends:
            story.append(Paragraph("Monthly Trends", styles['Heading2']))
            trend_data = [["Month", "Amount", "Transactions"]]
            for trend in data.monthly_trends:
                trend_data.append([
                    trend.label,
                    f"AED {trend.total:,.2f}",
                    str(trend.transaction_count),
                ])
            
            trend_table = Table(trend_data, colWidths=[2*inch, 2*inch, 1.5*inch])
            trend_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(trend_table)
        
        # Build PDF
        doc.build(story)
        
        file_size = file_path.stat().st_size
        return str(file_path), file_size
    
    @classmethod
    def _generate_simple_pdf(cls, data: ReportData, report_id: str) -> Tuple[str, int]:
        """Generate a simple PDF without reportlab (fallback)."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REPORTS_DIR / f"{report_id}.txt"  # Text file as fallback
        
        content = f"""
{data.title}
{data.subtitle}
Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M')}

═══════════════════════════════════════════════════════════════

SUMMARY
-------
Total Income:     AED {data.total_income:,.2f}
Total Expenses:   AED {data.total_expenses:,.2f}
Net Change:       AED {data.net_change:,.2f}
Transactions:     {data.transaction_count}

═══════════════════════════════════════════════════════════════

SPENDING BY CATEGORY
--------------------
"""
        for cat in data.categories[:10]:
            content += f"{cat.name:20s} AED {cat.total:>10,.2f} ({cat.percentage:>5.1f}%)\n"
        
        content += """
═══════════════════════════════════════════════════════════════

MONTHLY TRENDS
--------------
"""
        for trend in data.monthly_trends:
            content += f"{trend.label:15s} AED {trend.total:>10,.2f} ({trend.transaction_count} txns)\n"
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        file_size = file_path.stat().st_size
        return str(file_path), file_size
    
    @classmethod
    def _generate_excel(cls, data: ReportData, report_id: str) -> Tuple[str, int]:
        """Generate Excel report using openpyxl."""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            # Fallback to CSV
            return cls._generate_csv(data, report_id)
        
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REPORTS_DIR / f"{report_id}.xlsx"
        
        wb = Workbook()
        
        # Summary sheet
        ws = wb.active
        ws.title = "Summary"
        
        # Styles
        header_font = Font(bold=True, size=14)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font_white = Font(bold=True, color="FFFFFF")
        
        # Title
        ws['A1'] = data.title
        ws['A1'].font = Font(bold=True, size=18)
        ws['A2'] = data.subtitle
        ws['A3'] = f"Generated: {data.generated_at.strftime('%Y-%m-%d %H:%M')}"
        
        # Summary
        ws['A5'] = "Summary"
        ws['A5'].font = header_font
        
        summary_data = [
            ("Total Income", f"AED {data.total_income:,.2f}"),
            ("Total Expenses", f"AED {data.total_expenses:,.2f}"),
            ("Net Change", f"AED {data.net_change:,.2f}"),
            ("Transactions", data.transaction_count),
        ]
        for i, (label, value) in enumerate(summary_data, 6):
            ws[f'A{i}'] = label
            ws[f'B{i}'] = value
        
        # Categories sheet
        ws_cat = wb.create_sheet("Categories")
        ws_cat['A1'] = "Category"
        ws_cat['B1'] = "Amount"
        ws_cat['C1'] = "% of Total"
        ws_cat['D1'] = "Transactions"
        ws_cat['E1'] = "Avg Transaction"
        
        for cell in ws_cat[1]:
            cell.font = header_font_white
            cell.fill = header_fill
        
        for i, cat in enumerate(data.categories, 2):
            ws_cat[f'A{i}'] = cat.name
            ws_cat[f'B{i}'] = cat.total
            ws_cat[f'C{i}'] = cat.percentage / 100
            ws_cat[f'D{i}'] = cat.transaction_count
            ws_cat[f'E{i}'] = cat.average_transaction
        
        # Format columns
        ws_cat.column_dimensions['A'].width = 20
        ws_cat.column_dimensions['B'].width = 15
        ws_cat.column_dimensions['C'].width = 12
        ws_cat.column_dimensions['D'].width = 12
        ws_cat.column_dimensions['E'].width = 15
        
        # Monthly trends sheet
        ws_monthly = wb.create_sheet("Monthly Trends")
        ws_monthly['A1'] = "Month"
        ws_monthly['B1'] = "Amount"
        ws_monthly['C1'] = "Transactions"
        
        for cell in ws_monthly[1]:
            cell.font = header_font_white
            cell.fill = header_fill
        
        for i, trend in enumerate(data.monthly_trends, 2):
            ws_monthly[f'A{i}'] = trend.label
            ws_monthly[f'B{i}'] = trend.total
            ws_monthly[f'C{i}'] = trend.transaction_count
        
        # Save
        wb.save(file_path)
        file_size = file_path.stat().st_size
        return str(file_path), file_size
    
    @classmethod
    def _generate_csv(cls, data: ReportData, report_id: str) -> Tuple[str, int]:
        """Generate CSV report (fallback for Excel)."""
        import csv
        
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REPORTS_DIR / f"{report_id}.csv"
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Summary
            writer.writerow(["Summary"])
            writer.writerow(["Total Income", data.total_income])
            writer.writerow(["Total Expenses", data.total_expenses])
            writer.writerow(["Net Change", data.net_change])
            writer.writerow(["Transactions", data.transaction_count])
            writer.writerow([])
            
            # Categories
            writer.writerow(["Categories"])
            writer.writerow(["Category", "Amount", "Percentage", "Transactions"])
            for cat in data.categories:
                writer.writerow([cat.name, cat.total, cat.percentage, cat.transaction_count])
            writer.writerow([])
            
            # Monthly trends
            writer.writerow(["Monthly Trends"])
            writer.writerow(["Month", "Amount", "Transactions"])
            for trend in data.monthly_trends:
                writer.writerow([trend.label, trend.total, trend.transaction_count])
        
        file_size = file_path.stat().st_size
        return str(file_path), file_size
    
    @classmethod
    def _generate_json(cls, data: ReportData, report_id: str) -> Tuple[str, int]:
        """Generate JSON report."""
        import json
        
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REPORTS_DIR / f"{report_id}.json"
        
        with open(file_path, 'w') as f:
            json.dump(data.to_dict(), f, indent=2)
        
        file_size = file_path.stat().st_size
        return str(file_path), file_size
    
    @classmethod
    def get_report(cls, db: Session, report_id: str, user_id: str) -> Optional[Report]:
        """Get a report by ID."""
        return db.query(Report).filter(
            Report.id == uuid.UUID(report_id),
            Report.user_id == user_id
        ).first()
    
    @classmethod
    def get_user_reports(
        cls,
        db: Session,
        user_id: str,
        limit: int = 20,
        include_failed: bool = False,
    ) -> List[Report]:
        """Get reports for a user."""
        query = db.query(Report).filter(Report.user_id == user_id)
        
        if not include_failed:
            query = query.filter(Report.status != ReportStatus.FAILED.value)
        
        return query.order_by(Report.created_at.desc()).limit(limit).all()
    
    @classmethod
    def delete_report(cls, db: Session, report_id: str, user_id: str) -> bool:
        """Delete a report and its file."""
        report = cls.get_report(db, report_id, user_id)
        if not report:
            return False
        
        # Delete file if exists
        if report.file_path and Path(report.file_path).exists():
            Path(report.file_path).unlink()
        
        db.delete(report)
        db.commit()
        return True

