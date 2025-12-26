"use client";

import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import SegmentedControl from "./ui/SegmentedControl";
import SkeletonLoader from "./ui/SkeletonLoader";
import EmptyState from "./ui/EmptyState";

interface ChartFilters {
  startDate: string;
  endDate: string;
  categories: string[];
  accounts: string[];
  merchant: string;
  groupBy: "week" | "month";
}

interface SpendingChartProps {
  filters: ChartFilters;
  onGroupByChange?: (value: "week" | "month") => void;
  onCategoryToggle?: (category: string) => void;
  excludedCategories?: string[];
  allAvailableCategories?: string[]; // All categories from API (including transfers)
  onPeriodClick?: (period: string) => void;
}

export default function SpendingChart({ 
  filters, 
  onGroupByChange, 
  onCategoryToggle, 
  excludedCategories = [], 
  allAvailableCategories = [],
  onPeriodClick
}: SpendingChartProps) {
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchChartData();
  }, [filters]);

  const fetchChartData = async () => {
    setLoading(true);
    setError(null);

    try {
      const endpoint = filters.groupBy === "month" ? "/api/chart/monthly" : "/api/chart/weekly";
      const params = new URLSearchParams();

      if (filters.startDate) params.append("start_date", filters.startDate);
      if (filters.endDate) params.append("end_date", filters.endDate);
      filters.categories?.forEach((cat) => params.append("categories", cat));
      filters.accounts?.forEach((acc) => params.append("accounts", acc));
      if (filters.merchant) params.append("merchant", filters.merchant);

      const response = await fetch(
        `http://localhost:8000${endpoint}${params.toString() ? `?${params.toString()}` : ""}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch chart data: ${response.statusText}`);
      }

      const result = await response.json();
      setChartData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chart data");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  if (loading) {
    return <SkeletonLoader variant="chart" />;
  }

  if (error) {
    return (
      <div className="card p-4 bg-red-50 border border-red-200">
        <p className="text-body text-red-800">{error}</p>
      </div>
    );
  }

  if (!chartData || chartData.data.length === 0) {
    return (
      <div className="card">
        <EmptyState
          title="No data available"
          description="Try adjusting your filters or uploading more transactions"
          icon={
            <svg className="w-16 h-16 text-[var(--color-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
      </div>
    );
  }

  // Separate income and expense categories
  const incomeCategories = ["Salary", "Incoming Transfer"];
  const transferCategories = ["Transfer Between My Accounts", "Outgoing Transfer"];
  
  // Get all available categories for the legend
  // Use allAvailableCategories if provided (includes all categories from API)
  // Otherwise fallback to chartData categories (which are already filtered by backend)
  const legendCategories = allAvailableCategories.length > 0 
    ? allAvailableCategories 
    : (chartData?.categories || []);
  
  // Filter out excluded categories for chart display only
  const displayCategories = legendCategories.filter(
    (cat: string) => !excludedCategories.includes(cat)
  );
  
  // For each category, determine if it's income or expense
  const categoryTypes: Record<string, "income" | "expense"> = {};
  legendCategories.forEach((cat: string) => {
    if (incomeCategories.includes(cat)) {
      categoryTypes[cat] = "income";
    } else {
      categoryTypes[cat] = "expense";
    }
  });
  
  // All expense categories (for legend) - sorted by total
  const allExpenseCategories = legendCategories.filter(
    (cat: string) => categoryTypes[cat] === "expense"
  );
  
  // All income categories (for legend)
  const allIncomeCategories = legendCategories.filter(
    (cat: string) => categoryTypes[cat] === "income"
  );
  
  // Display-only expense categories (for chart)
  const expenseCategories = displayCategories.filter(
    (cat: string) => categoryTypes[cat] === "expense"
  );
  
  // Display-only income categories (for chart)
  const actualIncomeCategories = displayCategories.filter(
    (cat: string) => categoryTypes[cat] === "income"
  );

  // Calculate totals per category to sort them (use all categories for legend)
  const categoryTotals: Record<string, number> = {};
  allExpenseCategories.forEach((cat: string) => {
    // For categories that might not be in chartData (e.g., excluded by default like transfers)
    // we need to handle them gracefully
    categoryTotals[cat] = chartData?.data
      ? chartData.data
          .filter((d: any) => d.category === cat)
          .reduce((sum: number, d: any) => sum + Number(d.total), 0)
      : 0;
  });

  // Sort expense categories by total (descending for display legend)
  const sortedExpenseCategories = [...allExpenseCategories].sort(
    (a, b) => categoryTotals[b] - categoryTotals[a]
  );

  // Transform data: each period has income and expense bars
  // For stacked bars in Recharts, the Bar component order determines stack order
  // We need ALL categories in the data, even if zero, in consistent order
  const transformedData = chartData.periods.map((period: string) => {
    const periodData: Record<string, any> = { period };
    
    // Add ALL expense categories in the same order as stackedExpenseCategories
    // This ensures consistent stacking across all bars
    expenseCategories.forEach((category: string) => {
      const item = chartData.data.find((d: any) => d.period === period && d.category === category);
      periodData[`expense_${category}`] = item ? Number(item.total) : 0;
    });
    
    // Add income categories (stacked in separate bar)
    actualIncomeCategories.forEach((category: string) => {
      const item = chartData.data.find((d: any) => d.period === period && d.category === category);
      periodData[`income_${category}`] = item ? Number(item.total) : 0;
    });
    
    return periodData;
  });
  
  // For rendering bars, we need the largest categories FIRST (they appear at bottom in stack)
  // Sort by total descending (largest first = bottom of stack in Recharts)
  const stackedExpenseCategories = [...expenseCategories].sort(
    (a, b) => categoryTotals[b] - categoryTotals[a]
  );

  // Category colors - assign unique colors to each category
  const getCategoryColor = (category: string, isIncome: boolean = false): string => {
    if (isIncome) return "#34C759"; // Green for income
    
    // Map each category to a unique color
    const colorMap: Record<string, string> = {
      "Other": "#64748B", // Gray for Other
      "Groceries": "#8B5CF6", // Purple
      "Shopping": "#F59E0B", // Amber/Yellow
      "Transport": "#06B6D4", // Cyan/Teal
      "Food & Dining": "#EC4899", // Pink
      "Technology Subscriptions": "#EF4444", // Red
      "Telecommunications": "#3B82F6", // Blue
      "Healthcare": "#10B981", // Emerald
      "Entertainment": "#F97316", // Orange
      "Utilities": "#6366F1", // Indigo
    };
    
    return colorMap[category] || "#94A3B8"; // Default gray
  };

  return (
    <div className="card p-6 space-y-6">
      {/* Chart Header with Segmented Control */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-caption text-[var(--color-text-secondary)]">
            Showing {chartData.periods.length} periods
          </p>
        </div>
        {onGroupByChange && (
          <SegmentedControl
            options={[
              { value: "week", label: "Weekly" },
              { value: "month", label: "Monthly" },
            ]}
            value={filters.groupBy}
            onChange={(value) => onGroupByChange(value as "week" | "month")}
          />
        )}
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={transformedData}
          margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
          onClick={(data) => {
            // Handle click on chart bar
            if (data && data.activeLabel && onPeriodClick) {
              onPeriodClick(data.activeLabel);
            }
          }}
        >
          <defs>
            {/* Gradients for expense categories */}
            {stackedExpenseCategories.map((category: string) => {
              const color = getCategoryColor(category, false);
              return (
                <linearGradient key={`expense-${category}`} id={`gradient-${category.replace(/\s+/g, '-')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.7} />
                </linearGradient>
              );
            })}
            {/* Gradient for income */}
            {actualIncomeCategories.map((category: string) => {
              const color = getCategoryColor(category, true);
              return (
                <linearGradient key={`income-${category}`} id={`gradient-${category.replace(/\s+/g, '-')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.9} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.7} />
                </linearGradient>
              );
            })}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-light)" />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 12, fill: "var(--color-text-secondary)" }}
            tickLine={{ stroke: "var(--color-border-light)" }}
            style={{ cursor: 'pointer' }}
          />
          <YAxis
            tickFormatter={formatCurrency}
            tick={{ fontSize: 12, fill: "var(--color-text-secondary)" }}
            tickLine={{ stroke: "var(--color-border-light)" }}
          />
          <Tooltip
            formatter={(value: number | undefined) => value !== undefined ? formatCurrency(value) : ""}
            contentStyle={{
              backgroundColor: "var(--color-bg-primary)",
              border: "1px solid var(--color-border)",
              borderRadius: "12px",
              boxShadow: "var(--shadow-lg)",
              padding: "12px",
            }}
            labelStyle={{ 
              color: "var(--color-text-primary)", 
              fontWeight: 600,
              fontSize: "14px",
              marginBottom: "8px",
            }}
            itemStyle={{
              color: "var(--color-text-secondary)",
              fontSize: "13px",
              padding: "4px 0",
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: "20px" }}
            iconType="circle"
            formatter={(value) => {
              // Clean up legend labels
              if (value.startsWith("expense_")) return value.replace("expense_", "");
              if (value.startsWith("income_")) return value.replace("income_", "");
              return value;
            }}
          />
          
          {/* Expense bars (stacked) */}
          {stackedExpenseCategories.map((category: string, idx: number) => (
            <Bar
              key={`expense-${category}`}
              dataKey={`expense_${category}`}
              stackId="expenses"
              fill={`url(#gradient-${category.replace(/\s+/g, '-')})`}
              name={category}
              radius={idx === stackedExpenseCategories.length - 1 ? [8, 8, 0, 0] : undefined}
              cursor="pointer"
            />
          ))}
          
          {/* Income bars (stacked separately) - only if income categories exist */}
          {actualIncomeCategories.length > 0 && actualIncomeCategories.map((category: string) => (
            <Bar
              key={`income-${category}`}
              dataKey={`income_${category}`}
              stackId="income"
              fill={`url(#gradient-${category.replace(/\s+/g, '-')})`}
              name={category}
              radius={[8, 8, 0, 0]}
              cursor="pointer"
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Category Summary - Unified List */}
      <div className="pt-4 border-t border-[var(--color-border-light)]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
            All Categories
          </h3>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  // Select all (exclude none)
                  if (onCategoryToggle) {
                    excludedCategories.forEach(cat => onCategoryToggle(cat));
                  }
                }}
                disabled={excludedCategories.length === 0}
                className="text-label text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-apple"
              >
                Select All
              </button>
              <span className="text-[var(--color-text-tertiary)]">|</span>
              <button
                onClick={() => {
                  // Deselect all (exclude all categories)
                  if (onCategoryToggle) {
                    legendCategories
                      .filter((cat: string) => !excludedCategories.includes(cat))
                      .forEach((cat: string) => onCategoryToggle(cat));
                  }
                }}
                disabled={excludedCategories.length === legendCategories.length}
                className="text-label text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-apple"
              >
                Deselect All
              </button>
            </div>
        </div>
        
        {/* Unified category list with 2 columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
          {/* First pass: calculate all totals and create unified list */}
          {(() => {
            // Calculate totals for all categories
            const allCategoryTotals: Array<{category: string, total: number, isIncome: boolean}> = [];
            
            // Add expense categories
            sortedExpenseCategories.forEach((category: string) => {
              allCategoryTotals.push({
                category,
                total: categoryTotals[category],
                isIncome: false,
              });
            });
            
            // Add income categories
            allIncomeCategories.forEach((category: string) => {
              const total = chartData?.data
                ? chartData.data
                    .filter((d: any) => d.category === category)
                    .reduce((sum: number, d: any) => sum + Number(d.total), 0)
                : 0;
              if (total > 0) {
                allCategoryTotals.push({
                  category,
                  total,
                  isIncome: true,
                });
              }
            });
            
            // Sort by absolute total (largest first)
            allCategoryTotals.sort((a, b) => b.total - a.total);
            
            // Render all categories
            return allCategoryTotals.map(({ category, total, isIncome }) => {
              const color = getCategoryColor(category, isIncome);
              const isExcluded = excludedCategories.includes(category);
              const sign = isIncome ? '+' : '-';
              
              return (
                <button
                  key={category}
                  onClick={() => onCategoryToggle?.(category)}
                  className={`
                    w-full flex items-center justify-between p-3 rounded-lg
                    transition-all duration-apple text-left
                    ${isExcluded 
                      ? 'opacity-40 hover:opacity-100' 
                      : ''
                    }
                    hover:bg-white/5 active:bg-white/10
                    ${onCategoryToggle ? 'cursor-pointer' : 'cursor-default'}
                  `}
                  disabled={!onCategoryToggle}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0 ring-2 ring-offset-2 ring-offset-[var(--color-bg-primary)]"
                      style={{ backgroundColor: color, ringColor: isExcluded ? 'transparent' : `${color}40` }}
                    />
                    <p className={`text-body ${isExcluded ? 'line-through' : ''} text-[var(--color-text-primary)] truncate`}>
                      {category}
                    </p>
                  </div>
                  <p className={`text-body font-semibold ml-4 tabular-nums ${
                    isIncome ? 'text-[var(--color-success)]' : 'text-[var(--color-text-secondary)]'
                  }`}>
                    {sign} {formatCurrency(Math.abs(total))}
                  </p>
                </button>
              );
            });
          })()}
        </div>
      </div>
    </div>
  );
}
