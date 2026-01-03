"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import CategoryFilters from "../components/categories/CategoryFilters";
import RulesFilter from "../components/categories/RulesFilter";
import MerchantsGrid from "../components/categories/MerchantsGrid";
import SparkleIcon from "../components/ui/SparkleIcon";
import { API_BASE_URL } from "../constants/api";

export interface Category {
  id: number;
  name: string;
  keywords: string[];
}

export interface CategoryDetailedStats {
  id: number;
  name: string;
  total_amount: number;
  transaction_count: number;
  rule_count: number;
  merchant_count: number;
  days: number;
}

interface DateFilters {
  startDate: string;
  endDate: string;
}

export default function CategoriesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedRuleIndex, setSelectedRuleIndex] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedMerchants, setSelectedMerchants] = useState<Set<string>>(new Set());
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isRecategorizing, setIsRecategorizing] = useState(false);
  
  // Date filter state
  const [dateFilters, setDateFilters] = useState<DateFilters>(() => {
    // Default to last 30 days
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    };
  });

  useEffect(() => {
    fetchCategories();
  }, []);

  // Clear merchant selection when returning from AI suggestions page
  useEffect(() => {
    setSelectedMerchants(new Set());
    setRefreshTrigger(prev => prev + 1);
  }, [searchParams]);

  const fetchCategories = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/categories");
      if (!response.ok) throw new Error("Failed to fetch categories");
      const data = await response.json();
      setCategories(data);
      // By default, no categories are selected (show all)
      setSelectedCategoryIds([]);
    } catch (err) {
      console.error("Failed to fetch categories:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryUpdate = () => {
    fetchCategories();
    setRefreshTrigger(prev => prev + 1);
  };

  const handleAICategorize = () => {
    if (selectedMerchants.size === 0) return;
    
    // Store merchant list in sessionStorage to pass to AI suggestions page
    sessionStorage.setItem('ai_categorize_merchants', JSON.stringify(Array.from(selectedMerchants)));
    sessionStorage.setItem('ai_categorize_start_date', dateFilters.startDate);
    sessionStorage.setItem('ai_categorize_end_date', dateFilters.endDate);
    
    // Navigate to AI suggestions page
    router.push('/categories/ai-suggestions');
  };

  const handleRecategorizeAll = async () => {
    if (isRecategorizing) return;
    
    setIsRecategorizing(true);
    try {
      const response = await fetch(`${API_BASE_URL}/jobs/recategorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'test_user', // TODO: Get from auth context
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to start recategorization');
      }
      
      const data = await response.json();
      console.log('Recategorization job started:', data.job_id);
      // The NotificationManager will show progress via WebSocket
      
    } catch (error) {
      console.error('Failed to start recategorization:', error);
      // Could show error toast here
    } finally {
      // Button stays in loading state until job completes via WebSocket
      // For now, reset after a short delay
      setTimeout(() => {
        setIsRecategorizing(false);
        setRefreshTrigger(prev => prev + 1);
      }, 2000);
    }
  };

  // Quick filter handlers
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

    setDateFilters({
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

  const handleClearDateFilters = () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    setDateFilters({
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    });
  };

  const selectedCategory = selectedCategoryIds.length === 1 
    ? categories.find(c => c.id === selectedCategoryIds[0]) ?? null
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--color-primary)]"></div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Page Title - Same style as transactions page */}
      <div className="px-6 pt-6 pb-4 bg-[var(--color-bg-primary)]">
        <h1 className="text-title text-[var(--color-text-primary)]">Category Management</h1>
        <p className="text-body text-[var(--color-text-secondary)] mt-1">
          Manage categorization rules and organize merchants by category
        </p>
      </div>

      {/* Quick Filters Card - Same style as transactions page */}
      <div className="px-6 pb-4">
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

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Date Range */}
            <div>
              <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
                From Date
              </label>
              <input
                type="date"
                value={dateFilters.startDate}
                onChange={(e) => setDateFilters(prev => ({ ...prev, startDate: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
                To Date
              </label>
              <input
                type="date"
                value={dateFilters.endDate}
                onChange={(e) => setDateFilters(prev => ({ ...prev, endDate: e.target.value }))}
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
                placeholder="Search merchants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input"
              />
            </div>
            {/* Action Buttons */}
            <div className="flex items-end gap-2">
              <button
                onClick={handleClearDateFilters}
                className="text-caption font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-apple"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Category Filters and Actions */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]">
        <div className="px-6 py-4">
          <CategoryFilters
            categories={categories}
            selectedCategoryIds={selectedCategoryIds}
            onCategorySelect={setSelectedCategoryIds}
            onCategoryUpdate={handleCategoryUpdate}
          />
          <div className="flex items-center gap-4 mt-4">
            <div className="relative group">
              <button
                onClick={handleRecategorizeAll}
                disabled={isRecategorizing}
                className="btn btn-secondary flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                title="Re-apply all rules to recategorize transactions"
              >
                {isRecategorizing ? (
                  <>
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Recategorizing...
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Recategorize All
                  </>
                )}
              </button>
            </div>
            <div className="relative group">
              <button
                onClick={handleAICategorize}
                disabled={selectedMerchants.size === 0}
                className="btn btn-primary flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <SparkleIcon size={16} />
                {selectedMerchants.size > 0 
                  ? `AI Categorize (${selectedMerchants.size})` 
                  : 'AI Categorize'}
              </button>
              {selectedMerchants.size === 0 && (
                <div className="hidden group-hover:block absolute bottom-full right-0 mb-2 w-64 p-3 bg-gray-900 text-white text-caption rounded-lg shadow-lg z-50">
                  <div className="absolute bottom-0 right-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-gray-900"></div>
                  Select one or more merchants to categorize them with AI
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - 2 Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Rules Filter (25%) */}
        <div className="w-[25%] border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)] overflow-y-auto">
          <RulesFilter
            selectedCategory={selectedCategory}
            selectedRuleIndex={selectedRuleIndex}
            onRuleSelect={setSelectedRuleIndex}
            onCategoryUpdate={handleCategoryUpdate}
            selectedCategoryIds={selectedCategoryIds}
            categories={categories}
            searchQuery={searchQuery}
          />
        </div>

        {/* Right Panel - Merchants Grid (75%) */}
        <div className="flex-1 bg-[var(--color-bg-primary)] overflow-y-auto">
          <MerchantsGrid
            selectedCategoryIds={selectedCategoryIds}
            selectedCategory={selectedCategory}
            selectedRuleIndex={selectedRuleIndex}
            startDate={dateFilters.startDate}
            endDate={dateFilters.endDate}
            searchQuery={searchQuery}
            categories={categories}
            onCategoryUpdate={handleCategoryUpdate}
            selectedMerchants={selectedMerchants}
            onSelectedMerchantsChange={setSelectedMerchants}
            refreshTrigger={refreshTrigger}
          />
        </div>
      </div>
    </div>
  );
}
