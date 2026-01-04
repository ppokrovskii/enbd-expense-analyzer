"use client";

import { useState, useEffect, useRef } from "react";
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
import { getApiHeaders } from "../utils/api";
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
  onCategoryExclude?: (category: string) => void;
  filterMode?: 'none' | 'whitelist' | 'blacklist';
  filteredCategories?: string[];
  allAvailableCategories?: string[]; // All categories from API (including transfers)
  onPeriodClick?: (period: string) => void;
  onClearFilters?: () => void;
}

// Stable default empty arrays (outside component to prevent recreation)
const EMPTY_ARRAY: string[] = [];

export default function SpendingChart({ 
  filters, 
  onGroupByChange, 
  onCategoryToggle,
  onCategoryExclude,
  filterMode = 'none',
  filteredCategories = EMPTY_ARRAY,
  allAvailableCategories = EMPTY_ARRAY,
  onPeriodClick,
  onClearFilters
}: SpendingChartProps) {
  const [chartData, setChartData] = useState<any>(null);
  const [categoryTotals, setCategoryTotals] = useState<any>(null); // Separate state for category totals
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false); // New state for subsequent loads
  const [error, setError] = useState<string | null>(null);
  const [categoryColors, setCategoryColors] = useState<Record<string, string>>({});
  const [personVersion, setPersonVersion] = useState(0); // Track person changes
  const fetchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Listen for person changes
  useEffect(() => {
    const handlePersonChange = () => {
      setPersonVersion(v => v + 1);
    };
    
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, []);

  // Fetch category colors on mount and when person changes
  useEffect(() => {
    const fetchCategoryColors = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/categories/', {
          headers: getApiHeaders(),
        });
        if (response.ok) {
          const categories = await response.json();
          const colorMap: Record<string, string> = {};
          categories.forEach((cat: { name: string; color?: string }) => {
            if (cat.color) {
              colorMap[cat.name] = cat.color;
            }
          });
          setCategoryColors(colorMap);
        }
      } catch (error) {
        console.error('Failed to fetch category colors:', error);
      }
    };
    fetchCategoryColors();
  }, [personVersion]);

  // Serialize array dependencies to avoid reference comparison issues
  const accountsKey = JSON.stringify(filters.accounts || []);
  const filteredCategoriesKey = JSON.stringify(filteredCategories);

  useEffect(() => {
    // Debounce rapid filter changes to prevent jumping
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
    }

    fetchTimeoutRef.current = setTimeout(() => {
      fetchChartData();
      fetchCategoryTotals(); // Fetch category totals separately
    }, 100); // 100ms debounce

    return () => {
      if (fetchTimeoutRef.current) {
        clearTimeout(fetchTimeoutRef.current);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.startDate, filters.endDate, accountsKey, filters.merchant, filters.groupBy, filterMode, filteredCategoriesKey, personVersion]);

  const fetchCategoryTotals = async () => {
    // Fetch totals for all categories without category filter
    try {
      const endpoint = filters.groupBy === "month" ? "/api/chart/monthly" : "/api/chart/weekly";
      const params = new URLSearchParams();

      if (filters.startDate) params.append("start_date", filters.startDate);
      if (filters.endDate) params.append("end_date", filters.endDate);
      
      // DO NOT send categories filter - we want totals for ALL categories
      
      filters.accounts?.forEach((acc) => params.append("accounts", acc));
      if (filters.merchant) params.append("merchant", filters.merchant);

      const response = await fetch(
        `http://localhost:8000${endpoint}${params.toString() ? `?${params.toString()}` : ""}`,
        { headers: getApiHeaders() }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch category totals: ${response.statusText}`);
      }

      const result = await response.json();
      setCategoryTotals(result);
    } catch (err) {
      console.error("Failed to fetch category totals:", err);
    }
  };

  const fetchChartData = async () => {
    // Only show full loading state on initial load
    if (chartData === null) {
      setLoading(true);
    } else {
      setIsRefreshing(true); // Subtle refresh state for updates
    }
    setError(null);

    try {
      const endpoint = filters.groupBy === "month" ? "/api/chart/monthly" : "/api/chart/weekly";
      const params = new URLSearchParams();

      if (filters.startDate) params.append("start_date", filters.startDate);
      if (filters.endDate) params.append("end_date", filters.endDate);
      
      // Smart filter: whitelist or blacklist mode
      if (filterMode === 'whitelist' && filteredCategories.length > 0) {
        // Whitelist mode: only show selected categories
        filteredCategories.forEach((cat) => params.append("categories", cat));
      } else if (filterMode === 'blacklist' && filteredCategories.length > 0 && allAvailableCategories.length > 0) {
        // Blacklist mode: show all except selected categories
        const includedCategories = allAvailableCategories.filter(cat => !filteredCategories.includes(cat));
        includedCategories.forEach((cat) => params.append("categories", cat));
      }
      // If filterMode is 'none', don't send categories filter at all (show everything)
      
      filters.accounts?.forEach((acc) => params.append("accounts", acc));
      if (filters.merchant) params.append("merchant", filters.merchant);

      const response = await fetch(
        `http://localhost:8000${endpoint}${params.toString() ? `?${params.toString()}` : ""}`,
        { headers: getApiHeaders() }
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
      setIsRefreshing(false);
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
  
  // Determine which categories to display in chart based on filter mode
  const displayCategories = (() => {
    if (filterMode === 'whitelist' && filteredCategories.length > 0) {
      // Whitelist mode: only show selected categories
      return legendCategories.filter((cat: string) => filteredCategories.includes(cat));
    } else if (filterMode === 'blacklist' && filteredCategories.length > 0) {
      // Blacklist mode: show all except selected categories
      return legendCategories.filter((cat: string) => !filteredCategories.includes(cat));
    } else {
      // No filter: show all categories
      return legendCategories;
    }
  })();
  
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

  // Calculate totals per category to sort them (for chart bar stacking, use filtered chartData)
  const categorySortingTotals: Record<string, number> = {};
  allExpenseCategories.forEach((cat: string) => {
    // For categories that might not be in chartData (e.g., excluded by default like transfers)
    // we need to handle them gracefully
    categorySortingTotals[cat] = chartData?.data
      ? chartData.data
          .filter((d: any) => d.category === cat)
          .reduce((sum: number, d: any) => sum + Number(d.total), 0)
      : 0;
  });

  // Sort expense categories by total (descending for display legend)
  const sortedExpenseCategories = [...allExpenseCategories].sort(
    (a, b) => categorySortingTotals[b] - categorySortingTotals[a]
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
    (a, b) => categorySortingTotals[b] - categorySortingTotals[a]
  );

  // Category colors - fetch from API or use defaults
  const getCategoryColor = (category: string, isIncome: boolean = false): string => {
    if (isIncome) return "#34C759"; // Green for income
    
    // Use color from API if available
    if (categoryColors[category]) {
      return categoryColors[category];
    }
    
    // Fallback color map for categories not yet in the system
    const colorMap: Record<string, string> = {
      "Other": "#64748B", // Gray for Other
      "Transfer Between My Accounts": "#64748B", // Gray
      "Outgoing Transfer": "#94A3B8", // Light gray
      "Incoming Transfer": "#34C759", // Green (same as income)
    };
    
    return colorMap[category] || "#94A3B8"; // Default gray
  };

  // Calculate total expenses and income from chart data
  const calculateTotals = () => {
    if (!chartData || !chartData.data) {
      return { totalExpenses: 0, totalIncome: 0 };
    }

    let totalExpenses = 0;
    let totalIncome = 0;

    chartData.data.forEach((item: any) => {
      const category = item.category;
      const amount = Number(item.total);

      if (incomeCategories.includes(category)) {
        totalIncome += amount;
      } else if (!transferCategories.includes(category)) {
        totalExpenses += amount;
      }
    });

    return { totalExpenses, totalIncome };
  };

  const { totalExpenses, totalIncome } = calculateTotals();

  // Custom tooltip that filters out zero values
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    // Filter out items with zero or undefined values
    const nonZeroItems = payload.filter((item: any) => item.value && item.value !== 0);

    if (nonZeroItems.length === 0) return null;

    return (
      <div
        style={{
          backgroundColor: "var(--color-bg-primary)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          boxShadow: "var(--shadow-lg)",
          padding: "12px",
        }}
      >
        <p
          style={{
            color: "var(--color-text-primary)",
            fontWeight: 600,
            fontSize: "14px",
            marginBottom: "8px",
          }}
        >
          {label}
        </p>
        {nonZeroItems.map((item: any, index: number) => {
          // Clean up the name by removing "expense_" or "income_" prefix
          let displayName = item.name;
          if (displayName.startsWith("expense_")) {
            displayName = displayName.replace("expense_", "");
          } else if (displayName.startsWith("income_")) {
            displayName = displayName.replace("income_", "");
          }

          return (
            <p
              key={index}
              style={{
                color: "var(--color-text-secondary)",
                fontSize: "13px",
                padding: "4px 0",
              }}
            >
              <span style={{ color: item.color }}>{displayName}</span> : {formatCurrency(item.value)}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="card p-6 space-y-6 relative">
      {/* Subtle loading indicator for refreshes */}
      {isRefreshing && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[var(--color-primary)] to-transparent animate-pulse" />
      )}
      
      {/* Chart Header with Segmented Control */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-caption text-[var(--color-text-secondary)]">
            Showing {chartData.periods.length} periods
          </p>
          <div className="flex items-center gap-4 mt-2">
            <div className="flex items-center gap-2">
              <span className="text-caption text-[var(--color-text-secondary)]">Expenses:</span>
              <span className="text-body font-semibold text-[var(--color-text-primary)]">
                {formatCurrency(totalExpenses)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-caption text-[var(--color-text-secondary)]">Income:</span>
              <span className="text-body font-semibold text-[var(--color-success)]">
                {formatCurrency(totalIncome)}
              </span>
            </div>
          </div>
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
      <div className={`transition-opacity duration-300 min-h-[400px] ${isRefreshing ? 'opacity-60' : 'opacity-100'}`}>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={transformedData}
            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
            onClick={(data) => {
              // Handle click on chart bar
              if (data && data.activeLabel && onPeriodClick) {
                onPeriodClick(String(data.activeLabel));
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
          <Tooltip content={<CustomTooltip />} />
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
              cursor="pointer"
              onMouseEnter={(data, index, e) => {
                // Make hover effect subtle with dark theme
                if (e && e.target) {
                  (e.target as any).style.opacity = '0.8';
                }
              }}
              onMouseLeave={(data, index, e) => {
                if (e && e.target) {
                  (e.target as any).style.opacity = '1';
                }
              }}
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
              cursor="pointer"
              onMouseEnter={(data, index, e) => {
                if (e && e.target) {
                  (e.target as any).style.opacity = '0.8';
                }
              }}
              onMouseLeave={(data, index, e) => {
                if (e && e.target) {
                  (e.target as any).style.opacity = '1';
                }
              }}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
      </div>

      {/* Category Summary - Unified List */}
      <div className="pt-4 border-t border-[var(--color-border-light)]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
            All Categories
          </h3>
          <button
            onClick={() => {
              // Clear all filters
              onClearFilters?.();
            }}
            disabled={filterMode === 'none'}
            className="text-label text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-apple"
          >
            Clear Selection
          </button>
        </div>
        
        {/* Unified category list with 2 columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
          {/* Show ALL available categories with totals from categoryTotals (without category filter) */}
          {(() => {
            // Calculate totals for all categories using categoryTotals (not filtered by selected categories)
            const allCategoryTotals: Array<{category: string, total: number, isIncome: boolean}> = [];
            
            // Process all available categories from legendCategories
            legendCategories.forEach((category: string) => {
              const isIncome = incomeCategories.includes(category);
              // Use categoryTotals instead of chartData to show unfiltered totals
              const total = categoryTotals?.data
                ? categoryTotals.data
                    .filter((d: any) => d.category === category)
                    .reduce((sum: number, d: any) => sum + Number(d.total), 0)
                : 0;
              
              allCategoryTotals.push({
                category,
                total,
                isIncome,
              });
            });
            
            // Sort by total descending (don't prioritize selected categories in sorting)
            allCategoryTotals.sort((a, b) => b.total - a.total);
            
            // Render all categories
            return allCategoryTotals.map(({ category, total, isIncome }) => {
              const color = getCategoryColor(category, isIncome);
              const isFiltered = filteredCategories.includes(category);
              const isInWhitelist = filterMode === 'whitelist' && isFiltered;
              const isInBlacklist = filterMode === 'blacklist' && isFiltered;
              const isVisible = filterMode === 'none' || 
                               (filterMode === 'whitelist' && isFiltered) || 
                               (filterMode === 'blacklist' && !isFiltered);
              const sign = isIncome ? '+' : '-';
              
              return (
                <div
                  key={category}
                  className={`
                    w-full flex items-center justify-between p-3 rounded-lg
                    transition-all duration-apple
                    ${!isVisible 
                      ? 'opacity-40 hover:opacity-100' 
                      : ''
                    }
                    hover:bg-white/5
                    group
                  `}
                >
                  <button
                    onClick={() => onCategoryToggle?.(category)}
                    className="flex items-center gap-3 min-w-0 flex-1 text-left"
                    disabled={!onCategoryToggle}
                  >
                    <div
                      className="w-3 h-3 rounded-full flex-shrink-0 ring-2 ring-offset-2 ring-offset-[var(--color-bg-primary)]"
                      style={{ backgroundColor: color, ['--tw-ring-color' as string]: isVisible ? `${color}40` : 'transparent' } as React.CSSProperties}
                    />
                    <p className="text-body text-[var(--color-text-primary)] truncate">
                      {category}
                    </p>
                  </button>
                  <div className="flex items-center gap-2">
                    <p className={`text-body font-semibold tabular-nums ${
                      isIncome ? 'text-[var(--color-success)]' : 'text-[var(--color-text-secondary)]'
                    }`}>
                      {sign} {formatCurrency(Math.abs(total))}
                    </p>
                    {/* X button for excluding/including categories - always visible */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onCategoryExclude?.(category);
                      }}
                      className={`
                        ml-2 p-1 rounded transition-all
                        ${isInBlacklist 
                          ? 'bg-gray-200 dark:bg-gray-700' 
                          : 'hover:bg-gray-200 dark:hover:bg-gray-700'
                        }
                      `}
                      title={isInBlacklist ? "Remove from blacklist" : "Exclude this category"}
                    >
                      <svg className={`w-4 h-4 ${isInBlacklist ? 'text-gray-600 dark:text-gray-400' : 'text-gray-500 dark:text-gray-300'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            });
          })()}
        </div>
      </div>
    </div>
  );
}
