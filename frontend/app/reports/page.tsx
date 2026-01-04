"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { getApiHeaders } from "../utils/api";
import MetricCard from "../components/ui/MetricCard";
import SpendingChart from "../components/SpendingChart";
import SkeletonLoader from "../components/ui/SkeletonLoader";

interface FilterValues {
  startDate: string;
  endDate: string;
}

interface ReportStats {
  total_income: number;
  total_expenses: number;
  net: number;
  transaction_count: number;
}

interface CategoryBreakdown {
  category: string;
  total: number;
  percentage: number;
  transaction_count: number;
}

interface TopTransaction {
  description: string;
  amount: number;
  date: string;
}

interface CategoryDetail {
  category: string;
  total: number;
  count: number;
  top_transactions: TopTransaction[];
}

export default function ReportsPage() {
  const [filters, setFilters] = useState<FilterValues>(() => {
    // Default to current month
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    return {
      startDate: firstDay.toISOString().split('T')[0],
      endDate: lastDay.toISOString().split('T')[0]
    };
  });

  const [stats, setStats] = useState<ReportStats | null>(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState<CategoryBreakdown[]>([]);
  const [categoryDetails, setCategoryDetails] = useState<CategoryDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Memoize chart filters to prevent unnecessary re-renders
  const chartFilters = useMemo(() => ({
    startDate: filters.startDate,
    endDate: filters.endDate,
    categories: [] as string[],
    accounts: [] as string[],
    merchant: '',
    groupBy: 'month' as const
  }), [filters.startDate, filters.endDate]);

  // Stable empty array for filteredCategories prop
  const emptyCategories = useMemo(() => [] as string[], []);

  // Stable no-op callback for SpendingChart
  const noopGroupByChange = useCallback(() => {}, []);

  // Listen for person changes
  useEffect(() => {
    const handlePersonChange = () => {
      fetchReportData();
    };
    
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, [filters]);

  useEffect(() => {
    fetchReportData();
  }, [filters]);

  const fetchReportData = async () => {
    if (!filters.startDate || !filters.endDate) return;
    
    setLoading(true);
    setError(null);

    try {
      // Calculate period days
      const start = new Date(filters.startDate);
      const end = new Date(filters.endDate);
      const periodDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

      // Fetch summary stats
      const statsParams = new URLSearchParams();
      if (filters.startDate) statsParams.set('start_date', filters.startDate);
      if (filters.endDate) statsParams.set('end_date', filters.endDate);

      const statsResponse = await fetch(
        `http://localhost:8000/api/stats/summary?${statsParams.toString()}`,
        { headers: getApiHeaders() }
      );

      if (!statsResponse.ok) throw new Error('Failed to fetch stats');
      const statsData = await statsResponse.json();
      setStats(statsData);

      // Fetch insights to get category breakdown
      const insightsResponse = await fetch(
        `http://localhost:8000/api/insights/generate?period_days=${periodDays}`,
        { headers: getApiHeaders() }
      );

      if (insightsResponse.ok) {
        const insightsData = await insightsResponse.json();
        
        // Extract category data from insights
        const categoryInsight = insightsData.insights?.find(
          (i: any) => i.type === 'category_analysis'
        );
        
        if (categoryInsight?.data?.categories) {
          // Transform to our format
          const breakdown = categoryInsight.data.categories.map((cat: any) => ({
            category: cat.category,
            total: Math.abs(cat.amount),
            percentage: cat.percentage,
            transaction_count: cat.count || 0
          }));
          setCategoryBreakdown(breakdown.slice(0, 7));
          
          // Create detailed view
          const details = breakdown.map((cat: any) => ({
            category: cat.category,
            total: cat.total,
            count: cat.transaction_count,
            top_transactions: []
          }));
          setCategoryDetails(details);
        }
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report data');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFilter = (filterType: string) => {
    const now = new Date();
    let startYear: number, startMonth: number, startDay: number;
    let endYear: number, endMonth: number, endDay: number;

    switch (filterType) {
      case 'this-month':
        startYear = now.getFullYear();
        startMonth = now.getMonth() + 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        break;
      
      case 'last-month':
        const lastMonth = now.getMonth() === 0 ? 11 : now.getMonth() - 1;
        const lastMonthYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = lastMonthYear;
        startMonth = lastMonth + 1;
        startDay = 1;
        endYear = lastMonthYear;
        endMonth = lastMonth + 1;
        endDay = new Date(lastMonthYear, lastMonth + 1, 0).getDate();
        break;
      
      case 'two-months-ago':
        const twoMonthsAgo = (now.getMonth() - 2 + 12) % 12;
        const twoMonthsAgoYear = now.getMonth() < 2 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = twoMonthsAgoYear;
        startMonth = twoMonthsAgo + 1;
        startDay = 1;
        endYear = twoMonthsAgoYear;
        endMonth = twoMonthsAgo + 1;
        endDay = new Date(twoMonthsAgoYear, twoMonthsAgo + 1, 0).getDate();
        break;
      
      case 'last-3-months':
        const threeMonthsAgo = (now.getMonth() - 3 + 12) % 12;
        const threeMonthsAgoYear = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = threeMonthsAgoYear;
        startMonth = threeMonthsAgo + 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        break;
      
      case 'this-year':
        startYear = now.getFullYear();
        startMonth = 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = 12;
        endDay = 31;
        break;
      
      case 'last-year':
        startYear = now.getFullYear() - 1;
        startMonth = 1;
        startDay = 1;
        endYear = now.getFullYear() - 1;
        endMonth = 12;
        endDay = 31;
        break;
      
      case 'last-7-days': {
        const sevenDaysAgo = new Date(now);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        startYear = sevenDaysAgo.getFullYear();
        startMonth = sevenDaysAgo.getMonth() + 1;
        startDay = sevenDaysAgo.getDate();
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = now.getDate();
        break;
      }
      
      case 'last-30-days': {
        const thirtyDaysAgo = new Date(now);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        startYear = thirtyDaysAgo.getFullYear();
        startMonth = thirtyDaysAgo.getMonth() + 1;
        startDay = thirtyDaysAgo.getDate();
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = now.getDate();
        break;
      }
      
      default:
        return;
    }

    setFilters({
      startDate: `${startYear}-${String(startMonth).padStart(2, '0')}-${String(startDay).padStart(2, '0')}`,
      endDate: `${endYear}-${String(endMonth).padStart(2, '0')}-${String(endDay).padStart(2, '0')}`
    });
  };

  const getQuickFilterLabel = (filterType: string): string => {
    const now = new Date();
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'];
    
    switch (filterType) {
      case 'this-month':
        return monthNames[now.getMonth()];
      case 'last-month':
        return monthNames[(now.getMonth() - 1 + 12) % 12];
      case 'two-months-ago':
        return monthNames[(now.getMonth() - 2 + 12) % 12];
      default:
        return filterType;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'AED',
      minimumFractionDigits: 2,
    }).format(Math.abs(amount));
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const exportPDF = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/reports/generate', {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({
          report_type: 'monthly_summary',
          report_format: 'pdf',
          period_start: filters.startDate,
          period_end: filters.endDate,
        }),
      });

      if (!response.ok) throw new Error('Failed to generate PDF');

      const report = await response.json();
      
      // Download the generated report
      const downloadResponse = await fetch(
        `http://localhost:8000/api/reports/${report.id}/download`,
        { headers: getApiHeaders() }
      );

      if (!downloadResponse.ok) throw new Error('Failed to download PDF');

      const blob = await downloadResponse.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export PDF');
    }
  };

  const exportExcel = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/reports/generate', {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({
          report_type: 'monthly_summary',
          report_format: 'excel',
          period_start: filters.startDate,
          period_end: filters.endDate,
        }),
      });

      if (!response.ok) throw new Error('Failed to generate Excel');

      const report = await response.json();
      
      // Download the generated report
      const downloadResponse = await fetch(
        `http://localhost:8000/api/reports/${report.id}/download`,
        { headers: getApiHeaders() }
      );

      if (!downloadResponse.ok) throw new Error('Failed to download Excel');

      const blob = await downloadResponse.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export Excel');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-title text-[var(--color-text-primary)]">Financial Reports</h1>
        <p className="text-body text-[var(--color-text-secondary)] mt-1">
          Generate comprehensive reports for your financial analysis
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="card p-4 bg-red-50 border border-red-200">
          <p className="text-body text-red-800">{error}</p>
        </div>
      )}

      {/* Date Filters */}
      <div className="card p-6 space-y-4">
        {/* Quick Date Filters */}
        <div>
          <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
            Quick Filters
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleQuickFilter('this-month')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              {getQuickFilterLabel('this-month')}
            </button>
            <button
              onClick={() => handleQuickFilter('last-month')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              {getQuickFilterLabel('last-month')}
            </button>
            <button
              onClick={() => handleQuickFilter('two-months-ago')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              {getQuickFilterLabel('two-months-ago')}
            </button>
            <span className="border-l border-[var(--color-border-light)] mx-1"></span>
            <button
              onClick={() => handleQuickFilter('last-7-days')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              Last 7 Days
            </button>
            <button
              onClick={() => handleQuickFilter('last-30-days')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              Last 30 Days
            </button>
            <button
              onClick={() => handleQuickFilter('last-3-months')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              Last 3 Months
            </button>
            <button
              onClick={() => handleQuickFilter('this-year')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              This Year
            </button>
            <button
              onClick={() => handleQuickFilter('last-year')}
              className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
            >
              Last Year
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Date Range */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              From Date
            </label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              To Date
            </label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
              className="input"
            />
          </div>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-3 pt-4 border-t border-[var(--color-border-light)]">
          <button
            onClick={exportPDF}
            disabled={loading}
            className="btn btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            Export PDF
          </button>
          <button
            onClick={exportExcel}
            disabled={loading}
            className="btn btn-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Export Excel
          </button>
        </div>
      </div>

      {/* Report Preview - Section 1: Summary */}
      <div>
        <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Report Preview</h2>
        
        {/* Summary Totals */}
        {loading ? (
          <SkeletonLoader variant="metric" />
        ) : stats ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <MetricCard
              title="Total Spending"
              value={stats.total_expenses}
              format="currency"
              gradient
              gradientType="expense"
              icon={
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              }
            />
            <MetricCard
              title="Total Income"
              value={stats.total_income}
              format="currency"
              gradient
              gradientType="income"
              icon={
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              }
            />
            <MetricCard
              title="Net Balance"
              value={stats.net}
              format="currency"
              gradient
              gradientType={stats.net >= 0 ? "success" : "expense"}
              changeType={stats.net >= 0 ? "increase" : "decrease"}
              icon={
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              }
            />
          </div>
        ) : null}
      </div>

      {/* Section 2: Expense Overview Chart */}
      <div>
        <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Expense Overview</h2>
        <SpendingChart
          filters={chartFilters}
          onGroupByChange={noopGroupByChange}
          filterMode="none"
          filteredCategories={emptyCategories}
          allAvailableCategories={emptyCategories}
        />
      </div>

      {/* Section 3: Top Categories */}
      {!loading && categoryBreakdown.length > 0 && (
        <div>
          <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Top Spending Categories</h2>
          <div className="card p-6">
            <div className="space-y-4">
              {categoryBreakdown.map((cat, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-body font-medium text-[var(--color-text-primary)]">
                      {cat.category || 'Uncategorized'}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-caption text-[var(--color-text-secondary)]">
                        {cat.percentage.toFixed(1)}%
                      </span>
                      <span className="text-body font-semibold text-[var(--color-text-primary)]">
                        {formatCurrency(cat.total)}
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-[var(--color-bg-tertiary)] rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] h-2 rounded-full transition-all duration-500"
                      style={{ width: `${cat.percentage}%` }}
                    />
                  </div>
                  <p className="text-caption text-[var(--color-text-secondary)]">
                    {cat.transaction_count} transactions
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Section 4: Category Details */}
      {!loading && categoryDetails.length > 0 && (
        <div>
          <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Category Details</h2>
          <div className="space-y-4">
            {categoryDetails.map((detail, index) => (
              <div key={index} className="card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-subheading text-[var(--color-text-primary)]">
                    {detail.category || 'Uncategorized'}
                  </h3>
                  <div className="text-right">
                    <div className="text-heading text-[var(--color-text-primary)]">
                      {formatCurrency(detail.total)}
                    </div>
                    <div className="text-caption text-[var(--color-text-secondary)]">
                      {detail.count} transactions
                    </div>
                  </div>
                </div>
                
                {detail.top_transactions.length > 0 && (
                  <div>
                    <p className="text-caption text-[var(--color-text-secondary)] mb-2">
                      Top transactions:
                    </p>
                    <div className="space-y-2">
                      {detail.top_transactions.slice(0, 5).map((txn, txnIndex) => (
                        <div
                          key={txnIndex}
                          className="flex items-center justify-between py-2 border-b border-[var(--color-border-light)] last:border-b-0"
                        >
                          <div className="flex-1">
                            <p className="text-body text-[var(--color-text-primary)]">
                              {txn.description}
                            </p>
                            <p className="text-caption text-[var(--color-text-secondary)]">
                              {formatDate(txn.date)}
                            </p>
                          </div>
                          <div className="text-body font-medium text-[var(--color-text-primary)]">
                            {formatCurrency(txn.amount)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 5: AI-Generated Insights Placeholder */}
      <div>
        <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Key Insights</h2>
        <div className="card p-6">
          <div className="flex items-start gap-4 mb-4">
            <div className="p-3 rounded-lg bg-[var(--color-primary)]/10">
              <svg className="w-6 h-6 text-[var(--color-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-body text-[var(--color-text-secondary)] italic">
                AI-generated insights will appear here when you export the report. These insights will analyze spending patterns, identify trends, and highlight important observations from your financial data.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Section 6: Next Steps */}
      <div>
        <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Next Steps</h2>
        <div className="card p-6">
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <svg className="w-5 h-5 text-[var(--color-primary)] mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <p className="text-body text-[var(--color-text-secondary)]">
                Review your top 2-3 spending categories to identify potential savings opportunities
              </p>
            </li>
            <li className="flex items-start gap-3">
              <svg className="w-5 h-5 text-[var(--color-primary)] mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <p className="text-body text-[var(--color-text-secondary)]">
                Check recurring charges for subscriptions you may no longer need
              </p>
            </li>
            <li className="flex items-start gap-3">
              <svg className="w-5 h-5 text-[var(--color-primary)] mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <p className="text-body text-[var(--color-text-secondary)]">
                Re-run this report after a few months to track your progress and spending trends
              </p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
