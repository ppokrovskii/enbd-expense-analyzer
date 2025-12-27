"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import FilterPanel from "../components/FilterPanel";
import SpendingChart from "../components/SpendingChart";
import TransactionList from "../components/TransactionList";
import MetricCard from "../components/ui/MetricCard";
import SkeletonLoader from "../components/ui/SkeletonLoader";
import { useStats } from "../hooks/useStats";

interface FilterValues {
  startDate: string;
  endDate: string;
  categories: string[];
  accounts: string[];
  merchant: string;
}

export default function TransactionsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // Initialize state from URL params
  const [filters, setFilters] = useState<FilterValues>(() => {
    const startDate = searchParams.get('startDate') || '';
    const endDate = searchParams.get('endDate') || '';
    const merchant = searchParams.get('merchant') || '';
    const categories = searchParams.getAll('category');
    const accounts = searchParams.getAll('account');
    
    return {
      startDate,
      endDate,
      categories,
      accounts,
      merchant
    };
  });
  
  const [groupBy, setGroupBy] = useState<"week" | "month">(() => {
    return (searchParams.get('groupBy') as "week" | "month") || "week";
  });
  
  // Selected categories - empty by default (show all)
  // Smart filter state: can be whitelist or blacklist mode
  const [filterMode, setFilterMode] = useState<'none' | 'whitelist' | 'blacklist'>(() => {
    const mode = searchParams.get('filterMode');
    // Default to blacklist mode if no URL params
    if (!mode && searchParams.toString() === '') {
      return 'blacklist';
    }
    return (mode === 'whitelist' || mode === 'blacklist') ? mode : 'none';
  });
  const [filteredCategories, setFilteredCategories] = useState<string[]>(() => {
    const urlCategories = searchParams.getAll('filteredCategory');
    // Default to excluding "Transfer Between My Accounts" if no URL params
    if (urlCategories.length === 0 && searchParams.toString() === '') {
      return ['Transfer Between My Accounts'];
    }
    return urlCategories;
  });
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  
  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    
    if (filters.startDate) params.set('startDate', filters.startDate);
    if (filters.endDate) params.set('endDate', filters.endDate);
    if (filters.merchant) params.set('merchant', filters.merchant);
    filters.categories.forEach(cat => params.append('category', cat));
    filters.accounts.forEach(acc => params.append('account', acc));
    
    // Add smart filter params
    if (filterMode !== 'none') {
      params.set('filterMode', filterMode);
      filteredCategories.forEach(cat => params.append('filteredCategory', cat));
    }
    
    params.set('groupBy', groupBy);
    
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    router.replace(newUrl, { scroll: false });
  }, [filters, filterMode, filteredCategories, groupBy, router]);
  
  // Fetch available categories (including transfer categories)
  useEffect(() => {
    fetch("http://localhost:8000/api/filters/options")
      .then(res => res.json())
      .then(data => {
        const cats = data.categories || [];
        setAvailableCategories(cats);
      })
      .catch(err => console.error("Failed to fetch categories:", err));
  }, []);
  
  // Fetch summary statistics with filters
  const { stats, loading: statsLoading, error: statsError } = useStats({
    startDate: filters.startDate,
    endDate: filters.endDate,
  });

  const handleFilterChange = (newFilters: FilterValues) => {
    setFilters(newFilters);
  };

  const handleFilterReset = () => {
    setFilters({
      startDate: "",
      endDate: "",
      categories: [],
      accounts: [],
      merchant: ""
    });
    setSelectedCategories([]);
  };

  const handleCategoryToggle = (category: string) => {
    handleCategoryClick(category);
  };

  // Handle category name click (whitelist mode)
  const handleCategoryClick = (category: string) => {
    setFilteredCategories((prev) => {
      if (filterMode === 'whitelist' && prev.includes(category)) {
        // Remove from whitelist
        const newList = prev.filter((c) => c !== category);
        if (newList.length === 0) {
          setFilterMode('none');
        }
        return newList;
      } else if (filterMode === 'whitelist') {
        // Add to existing whitelist
        return [...prev, category];
      } else {
        // Switch to whitelist mode
        setFilterMode('whitelist');
        return [category];
      }
    });
  };

  // Handle X button click (blacklist mode)
  const handleCategoryExclude = (category: string) => {
    setFilteredCategories((prev) => {
      if (filterMode === 'blacklist' && prev.includes(category)) {
        // Remove from blacklist
        const newList = prev.filter((c) => c !== category);
        if (newList.length === 0) {
          setFilterMode('none');
        }
        return newList;
      } else if (filterMode === 'blacklist') {
        // Add to existing blacklist
        return [...prev, category];
      } else {
        // Switch to blacklist mode
        setFilterMode('blacklist');
        return [category];
      }
    });
  };

  // Clear all filters
  const handleClearFilters = () => {
    setFilterMode('none');
    setFilteredCategories([]);
  };
  
  const handlePeriodClick = (period: string) => {
    // Calculate date range based on the period format and groupBy type
    if (groupBy === "week") {
      // Period format: "2025-12-08" (week start date)
      const weekStart = new Date(period);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6); // Add 6 days to get week end
      
      const newFilters = {
        ...filters,
        startDate: weekStart.toISOString().split('T')[0],
        endDate: weekEnd.toISOString().split('T')[0]
      };
      setFilters(newFilters);
      handleFilterChange(newFilters);
    } else {
      // Period format: "2025-12" (month)
      const [year, month] = period.split('-');
      const monthStart = new Date(parseInt(year), parseInt(month) - 1, 1);
      const monthEnd = new Date(parseInt(year), parseInt(month), 0); // Last day of month
      
      const newFilters = {
        ...filters,
        startDate: monthStart.toISOString().split('T')[0],
        endDate: monthEnd.toISOString().split('T')[0]
      };
      setFilters(newFilters);
      handleFilterChange(newFilters);
    }
  };

  const handleQuickFilter = (filterType: string) => {
    const now = new Date();
    let startYear: number, startMonth: number, startDay: number;
    let endYear: number, endMonth: number, endDay: number;

    switch (filterType) {
      case 'this-month':
        startYear = now.getFullYear();
        startMonth = now.getMonth() + 1; // JavaScript months are 0-indexed
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(); // Last day of current month
        break;
      
      case 'last-month':
        const lastMonth = now.getMonth() === 0 ? 11 : now.getMonth() - 1;
        const lastMonthYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = lastMonthYear;
        startMonth = lastMonth + 1;
        startDay = 1;
        endYear = lastMonthYear;
        endMonth = lastMonth + 1;
        endDay = new Date(lastMonthYear, lastMonth + 1, 0).getDate(); // Last day of last month
        break;
      
      case 'two-months-ago':
        const twoMonthsAgo = (now.getMonth() - 2 + 12) % 12;
        const twoMonthsAgoYear = now.getMonth() < 2 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = twoMonthsAgoYear;
        startMonth = twoMonthsAgo + 1;
        startDay = 1;
        endYear = twoMonthsAgoYear;
        endMonth = twoMonthsAgo + 1;
        endDay = new Date(twoMonthsAgoYear, twoMonthsAgo + 1, 0).getDate(); // Last day of that month
        break;
      
      case 'last-3-months':
        const threeMonthsAgo = (now.getMonth() - 3 + 12) % 12;
        const threeMonthsAgoYear = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = threeMonthsAgoYear;
        startMonth = threeMonthsAgo + 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(); // Last day of current month
        break;
      
      case 'this-year':
        startYear = now.getFullYear();
        startMonth = 1;
        startDay = 1;
        endYear = now.getFullYear();
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

    const newFilters = {
      ...filters,
      startDate: `${startYear}-${String(startMonth).padStart(2, '0')}-${String(startDay).padStart(2, '0')}`,
      endDate: `${endYear}-${String(endMonth).padStart(2, '0')}-${String(endDay).padStart(2, '0')}`
    };
    setFilters(newFilters);
    handleFilterChange(newFilters);
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

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-title text-[var(--color-text-primary)]">Transactions</h1>
        <p className="text-body text-[var(--color-text-secondary)] mt-1">
          Track your spending and analyze your financial patterns
        </p>
      </div>

      {/* Summary Metric Cards */}
      {statsLoading ? (
        <SkeletonLoader variant="metric" />
      ) : statsError ? (
        <div className="card p-4 bg-red-50 border border-red-200">
          <p className="text-body text-red-800">{statsError}</p>
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

      {/* Date and Merchant Filters */}
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
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Date Range */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              From Date
            </label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => {
                const newFilters = {...filters, startDate: e.target.value};
                setFilters(newFilters);
                handleFilterChange(newFilters);
              }}
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
              onChange={(e) => {
                const newFilters = {...filters, endDate: e.target.value};
                setFilters(newFilters);
                handleFilterChange(newFilters);
              }}
              className="input"
            />
          </div>
          {/* Merchant Search */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              Merchant
            </label>
            <input
              type="text"
              value={filters.merchant}
              onChange={(e) => {
                const newFilters = {...filters, merchant: e.target.value};
                setFilters(newFilters);
                handleFilterChange(newFilters);
              }}
              placeholder="Search merchant..."
              className="input"
            />
          </div>
        </div>
        
        {/* Account Filter + Clear Button */}
        <div className="flex items-center gap-3 mt-4 pt-4 border-t border-[var(--color-border-light)]">
          <FilterPanel 
            onFilterChange={handleFilterChange} 
            onReset={handleFilterReset}
            currentFilters={filters}
          />
          
          {/* Clear All Button */}
          {(filters.startDate || filters.endDate || filters.merchant || filters.accounts.length > 0) && (
            <button
              onClick={handleFilterReset}
              className="text-caption font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-apple"
            >
              Clear all filters
            </button>
          )}
        </div>
      </div>

      {/* Spending Chart */}
      <div>
        <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Spending Overview</h2>
        <SpendingChart
          filters={{
            startDate: filters.startDate,
            endDate: filters.endDate,
            categories: filters.categories,
            accounts: filters.accounts,
            merchant: filters.merchant,
            groupBy: groupBy
          }}
          onGroupByChange={setGroupBy}
          onCategoryToggle={handleCategoryClick}
          onCategoryExclude={handleCategoryExclude}
          filterMode={filterMode}
          filteredCategories={filteredCategories}
          allAvailableCategories={availableCategories}
          onPeriodClick={handlePeriodClick}
          onClearFilters={handleClearFilters}
        />
      </div>


      {/* Transactions List */}
      <div>
        <h2 className="text-heading text-[var(--color-text-primary)] mb-4">Transaction Details</h2>
        <TransactionList 
          filters={filters}
          filterMode={filterMode}
          filteredCategories={filteredCategories}
          availableCategories={availableCategories}
        />
      </div>
    </div>
  );
}
