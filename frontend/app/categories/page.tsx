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

export default function CategoriesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedRuleIndex, setSelectedRuleIndex] = useState<number | null>(null);
  const [statsWindow, setStatsWindow] = useState<30 | 60 | 90>(30);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedMerchants, setSelectedMerchants] = useState<Set<string>>(new Set());
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isRecategorizing, setIsRecategorizing] = useState(false);

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
    sessionStorage.setItem('ai_categorize_days', statsWindow.toString());
    
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
      {/* Header with Title and Time Window */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-heading text-[var(--color-text-primary)]">Category Management</h1>
            <div className="flex gap-2">
              {([30, 60, 90] as const).map((days) => (
                <button
                  key={days}
                  onClick={() => setStatsWindow(days)}
                  className={`py-2 px-4 text-body rounded-lg transition-apple ${
                    statsWindow === days
                      ? "bg-[var(--color-primary)] text-white"
                      : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]"
                  }`}
                >
                  {days} days
                </button>
              ))}
            </div>
          </div>
          <p className="text-body text-[var(--color-text-secondary)]">
            Filter by categories and rules to organize your transactions
          </p>
        </div>
      </div>

      {/* Search and Category Filters */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]">
        <div className="px-6 py-4">
          <div className="flex items-center gap-4 mb-4">
            <input
              type="text"
              placeholder="Search merchants..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input flex-1"
            />
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

          <CategoryFilters
            categories={categories}
            selectedCategoryIds={selectedCategoryIds}
            onCategorySelect={setSelectedCategoryIds}
            onCategoryUpdate={handleCategoryUpdate}
          />
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
            statsWindow={statsWindow}
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
