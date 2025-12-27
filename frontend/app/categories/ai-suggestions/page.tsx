/**
 * AI Categorization Suggestions Page - Apple Quality Redesign
 * 
 * Design Principles:
 * - Confident: Clear hierarchy, obvious actions
 * - Efficient: Compact cards, batch operations, keyboard shortcuts
 * - Delightful: Smooth animations, satisfying feedback
 * - Accessible: Proper contrast, keyboard navigation
 */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import SparkleIcon from "../../components/ui/SparkleIcon";

interface AISuggestion {
  merchant: string;
  suggested_category: string;
  suggested_pattern: string;
  pattern_type: string;
  transaction_count: number;
  total_amount: number;
  is_new_category?: boolean;
}

interface EditableSuggestion extends AISuggestion {
  edited_category: string;
  edited_pattern: string;
  status: "pending" | "applied" | "rejected";
  is_new_category?: boolean;
  create_new_category?: boolean;
}

interface Category {
  id: number;
  name: string;
  keywords: string[];
}

export default function AICategorizationSuggestionsPage() {
  const router = useRouter();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<EditableSuggestion[]>([]);
  const [allCategories, setAllCategories] = useState<Category[]>([]);
  const [applying, setApplying] = useState(false);
  const [creatingCategoryForIndex, setCreatingCategoryForIndex] = useState<number | null>(null);
  const [appliedCount, setAppliedCount] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [autocompleteIndex, setAutocompleteIndex] = useState<number | null>(null);
  const [autocompleteQuery, setAutocompleteQuery] = useState<string>("");

  // Get parameters from sessionStorage
  const [merchants, setMerchants] = useState<string[]>([]);
  const [days, setDays] = useState(30);
  const [referrer, setReferrer] = useState<string | null>(null);

  useEffect(() => {
    const storedMerchants = sessionStorage.getItem('ai_categorize_merchants');
    const storedDays = sessionStorage.getItem('ai_categorize_days');
    const storedReferrer = sessionStorage.getItem('ai_categorize_referrer');
    
    if (storedMerchants) {
      try {
        const parsedMerchants = JSON.parse(storedMerchants);
        setMerchants(parsedMerchants);
      } catch (e) {
        console.error('Failed to parse merchants', e);
      }
    }
    
    if (storedDays) {
      setDays(parseInt(storedDays));
    }
    
    if (storedReferrer) {
      setReferrer(storedReferrer);
    }
  }, []);

  useEffect(() => {
    if (merchants.length === 0) return;
    
    const init = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/categories/");
        if (!response.ok) throw new Error("Failed to fetch categories");
        const categories = await response.json();
        setAllCategories(categories);
        await fetchSuggestions(categories);
      } catch (err) {
        console.error("Error during initialization:", err);
        setError(err instanceof Error ? err.message : "Failed to initialize");
      }
    };

    init();
  }, [merchants, days]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return; // Don't trigger when typing
      
      // Can add keyboard shortcuts here if needed later
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [suggestions]);

  const fetchSuggestions = async (categories: Category[]) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        "http://localhost:8000/api/categories/ai-bulk-suggest",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            days: days,
            level: "global",
            merchants: merchants,
            limit: 1000
          })
        }
      );

      if (!response.ok) throw new Error("Failed to fetch AI suggestions");
      const data = await response.json();
      
      const mappedSuggestions = data.map((s: AISuggestion) => {
        const categoryExists = categories.some(cat => cat.name === s.suggested_category);
        
        return {
          ...s,
          edited_category: s.suggested_category,
          edited_pattern: s.suggested_pattern,
          status: "pending" as const,
          is_new_category: s.is_new_category && !categoryExists,
          create_new_category: s.is_new_category && !categoryExists,
        };
      });
      
      setSuggestions(mappedSuggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load suggestions");
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleCreateCategoryFirst = async (index: number) => {
    const suggestion = suggestions[index];
    const categoryName = suggestion.edited_category;
    
    if (!categoryName.trim()) {
      setError("Category name cannot be empty");
      return;
    }
    
    if (allCategories.some(cat => cat.name === categoryName)) {
      const newSuggestions = [...suggestions];
      newSuggestions[index].create_new_category = false;
      newSuggestions[index].is_new_category = false;
      setSuggestions(newSuggestions);
      return;
    }
    
    setCreatingCategoryForIndex(index);
    setError(null);
    
    try {
      const response = await fetch("http://localhost:8000/api/categories/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: categoryName, keywords: [] }),
      });
      
      if (!response.ok) throw new Error("Failed to create category");
      
      const newCategory = await response.json();
      
      // Update allCategories state so the new category appears in ALL dropdowns
      setAllCategories(prev => [...prev, newCategory]);
      
      // Update this suggestion to mark it as no longer new (switches back to dropdown mode)
      const newSuggestions = [...suggestions];
      newSuggestions[index].create_new_category = false;
      newSuggestions[index].is_new_category = false;
      setSuggestions(newSuggestions);
      
      // Clear autocomplete state
      setAutocompleteQuery('');
      setAutocompleteIndex(null);
      
      showToast(`✓ Category "${categoryName}" created`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create category");
    } finally {
      setCreatingCategoryForIndex(null);
    }
  };

  const handleApplySelected = async () => {
    // Not used anymore - kept for potential future batch operations
    return;
  };

  const handleApplyAll = async () => {
    const pending = suggestions.filter(s => s.status === "pending");
    
    // Check if any suggestions have new categories that need to be created
    const hasNewCategories = pending.some(s => s.is_new_category || s.create_new_category);
    if (hasNewCategories) {
      setError("Please create all new categories first before applying all suggestions.");
      return;
    }
    
    setApplying(true);
    setError(null);

    try {
      const payload = {
        suggestions: pending.map(s => ({
          merchant: s.merchant,
          category: s.edited_category,
          pattern: s.edited_pattern,
          pattern_type: s.pattern_type,
          create_new_category: false,
        })),
        auto_create_rules: true,
      };

      const response = await fetch(
        "http://localhost:8000/api/categories/ai-bulk-apply",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) throw new Error("Failed to apply suggestions");

      // Mark all as applied
      const newSuggestions = suggestions.map(s => 
        s.status === "pending" ? { ...s, status: "applied" as const } : s
      );
      setSuggestions(newSuggestions);
      setAppliedCount(prev => prev + pending.length);
      
      showToast(`✓ Applied ${pending.length} suggestion${pending.length > 1 ? 's' : ''}`);
      
      // Clear all applied suggestions after a short delay
      setTimeout(() => {
        setSuggestions(prev => prev.filter(s => s.status !== "applied"));
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply suggestions");
    } finally {
      setApplying(false);
    }
  };

  const handleApplySingle = async (index: number) => {
    const suggestion = suggestions[index];
    setError(null);

    try {
      const payload = {
        suggestions: [{
          merchant: suggestion.merchant,
          category: suggestion.edited_category,
          pattern: suggestion.edited_pattern,
          pattern_type: suggestion.pattern_type,
          create_new_category: suggestion.is_new_category || suggestion.create_new_category || false,
        }],
        auto_create_rules: true,
      };

      const response = await fetch(
        "http://localhost:8000/api/categories/ai-bulk-apply",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) throw new Error("Failed to apply");

      const newSuggestions = [...suggestions];
      newSuggestions[index].status = "applied";
      setSuggestions(newSuggestions);
      setAppliedCount(prev => prev + 1);
      
      showToast(`✓ ${suggestion.merchant} → ${suggestion.edited_category}`);
      
      setTimeout(() => {
        setSuggestions(prev => prev.filter((_, i) => i !== index));
      }, 1000);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply");
    }
  };

  const handleRejectSingle = (index: number) => {
    const newSuggestions = [...suggestions];
    newSuggestions[index].status = "rejected";
    setSuggestions(newSuggestions);
    
    setTimeout(() => {
      setSuggestions(prev => prev.filter((_, i) => i !== index));
    }, 500);
  };

  const toggleSelection = (index: number) => {
    // Not used anymore
  };

  const toggleSelectAll = () => {
    // Not used anymore
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const visibleSuggestions = suggestions.filter(s => s.status !== "rejected");
  const pendingSuggestions = visibleSuggestions.filter(s => s.status === "pending");
  const allProcessed = visibleSuggestions.length === 0 && !loading && suggestions.length > 0;
  const totalCount = merchants.length;
  const processedCount = appliedCount;

  const handleDone = () => {
    // If opened from transactions page, return to the exact URL with filters
    if (referrer === 'transactions' && typeof window !== 'undefined') {
      const returnUrl = sessionStorage.getItem('ai_categorize_return_url');
      
      if (returnUrl) {
        // Clean up sessionStorage
        sessionStorage.removeItem('ai_categorize_return_url');
        sessionStorage.removeItem('ai_categorize_referrer');
        
        // Navigate back to the exact URL with all filters preserved
        window.location.href = returnUrl;
      } else {
        // Fallback: go to transactions page
        router.push('/transactions');
      }
    } else {
      // Normal flow: go back to categories page
      router.back();
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="bg-green-600 dark:bg-green-700 text-white px-6 py-3 rounded-full shadow-lg text-sm font-medium flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {toastMessage}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="sticky top-0 z-10 bg-[var(--color-bg-primary)]/95 backdrop-blur-xl border-b border-[var(--color-border)]">
        <div className="container mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 min-w-0 flex-1">
              <button
                onClick={handleDone}
                className="flex-shrink-0 p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-apple"
                aria-label="Go back"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <SparkleIcon size={20} className="text-[var(--color-primary)] flex-shrink-0" />
                  <h1 className="text-lg sm:text-xl font-semibold text-[var(--color-text-primary)]">
                    {pendingSuggestions.length > 0 
                      ? `${pendingSuggestions.length} Merchant${pendingSuggestions.length > 1 ? 's' : ''} to Review`
                      : "AI Suggestions"
                    }
                  </h1>
                </div>
                {totalCount > 0 && (
                  <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                    <div className="flex items-center gap-1.5">
                      <div className="w-24 h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-[var(--color-primary)] transition-all duration-500"
                          style={{ width: `${(processedCount / totalCount) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium">
                        {processedCount} of {totalCount}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              {pendingSuggestions.length > 0 && (
                <div className="relative group">
                  <button
                    onClick={handleApplyAll}
                    disabled={applying || pendingSuggestions.some(s => s.is_new_category || s.create_new_category)}
                    className="btn btn-primary text-sm sm:text-base disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {applying ? (
                      <span className="flex items-center gap-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Applying...
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Apply All ({pendingSuggestions.length})
                      </span>
                    )}
                  </button>
                  
                  {/* Tooltip for disabled state */}
                  {pendingSuggestions.some(s => s.is_new_category || s.create_new_category) && (
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-50 pointer-events-none">
                      <div className="bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg border border-gray-700">
                        Please create all new categories first
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                          <div className="border-4 border-transparent border-t-gray-900 dark:border-t-gray-800"></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
              {pendingSuggestions.length === 0 && !loading && (
                <button
                  onClick={handleDone}
                  className="btn btn-primary text-sm sm:text-base"
                >
                  Done
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 sm:px-6 py-4 sm:py-6 max-w-5xl">
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-red-800 dark:text-red-200 text-sm flex items-start gap-3">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="relative">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[var(--color-primary)]"></div>
              <SparkleIcon size={24} className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-[var(--color-primary)]" />
            </div>
            <p className="text-sm sm:text-base text-[var(--color-text-secondary)] mt-4">
              Analyzing with AI...
            </p>
          </div>
        ) : allProcessed ? (
          <div className="text-center py-16">
            <div className="w-20 h-20 rounded-full bg-green-50 dark:bg-green-900/30 flex items-center justify-center mx-auto mb-4">
              <svg className="w-10 h-10 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
              All Done! ✨
            </h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {appliedCount} merchant{appliedCount !== 1 ? 's' : ''} successfully categorized
            </p>
          </div>
        ) : visibleSuggestions.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-20 h-20 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mx-auto mb-4">
              <SparkleIcon size={32} className="text-[var(--color-text-tertiary)]" />
            </div>
            <p className="text-sm sm:text-base text-[var(--color-text-secondary)]">
              No merchants to categorize
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {visibleSuggestions.map((suggestion, visibleIndex) => {
              const originalIndex = suggestions.indexOf(suggestion);
              const isApplied = suggestion.status === "applied";
              
              return (
                <div 
                  key={`${suggestion.merchant}-${originalIndex}`}
                  className={`
                    bg-[var(--color-bg-secondary)] 
                    border border-[var(--color-border)]
                    rounded-xl p-4 sm:p-5
                    transition-all duration-300 
                    hover:border-[var(--color-border-hover)]
                    ${isApplied 
                      ? "animate-success-fade-out bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" 
                      : ""
                    }
                  `}
                >
                  {/* All fields visible - no checkboxes */}
                  <div className="space-y-4">
                    {/* Row 1: Merchant + Quick Actions */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-base font-semibold text-[var(--color-text-primary)] break-words">
                            {suggestion.merchant}
                          </h3>
                          <a
                            href={`https://www.google.com/search?q=${encodeURIComponent(suggestion.merchant)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-xs text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] transition-colors flex-shrink-0"
                            title="Search in Google"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <span>Google</span>
                          </a>
                        </div>
                        <p className="text-sm text-[var(--color-text-secondary)]">
                          {suggestion.transaction_count} transaction{suggestion.transaction_count !== 1 ? 's' : ''} 
                          {suggestion.total_amount > 0 && ` · ${formatCurrency(suggestion.total_amount)}`}
                        </p>
                      </div>

                      {/* Quick Actions */}
                      {!isApplied && (
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={() => handleApplySingle(originalIndex)}
                            disabled={suggestion.is_new_category || suggestion.create_new_category}
                            className="p-2 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/30 text-green-600 dark:text-green-400 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-apple"
                            title={
                              suggestion.is_new_category || suggestion.create_new_category
                                ? "Create category first"
                                : "Apply suggestion"
                            }
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleRejectSingle(originalIndex)}
                            className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-apple"
                            title="Reject"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Row 2: Category (full width) - Smart Dropdown + Input Combo */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                          Category
                        </label>
                      </div>
                      
                      <div className="flex gap-2">
                        {/* Dropdown OR Create button (smart switch) */}
                        {suggestion.is_new_category || suggestion.create_new_category ? (
                          // Show Create button when new category is being typed
                          <button
                            onClick={() => handleCreateCategoryFirst(originalIndex)}
                            disabled={creatingCategoryForIndex === originalIndex || !suggestion.edited_category.trim()}
                            className="btn bg-amber-500 hover:bg-amber-600 text-white text-sm h-[38px] flex-shrink-0 w-48 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {creatingCategoryForIndex === originalIndex ? (
                              <span className="flex items-center justify-center gap-2">
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                                Creating...
                              </span>
                            ) : (
                              <span className="flex items-center justify-center gap-1">
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Create
                              </span>
                            )}
                          </button>
                        ) : (
                          // Show dropdown when selecting existing category
                          <select
                            value={suggestion.edited_category}
                            onChange={(e) => {
                              const newSuggestions = [...suggestions];
                              newSuggestions[originalIndex].edited_category = e.target.value;
                              const categoryExists = allCategories.some(cat => cat.name === e.target.value);
                              newSuggestions[originalIndex].is_new_category = !categoryExists;
                              newSuggestions[originalIndex].create_new_category = !categoryExists;
                              setSuggestions(newSuggestions);
                              // Clear autocomplete state
                              setAutocompleteQuery('');
                              setAutocompleteIndex(null);
                            }}
                            disabled={isApplied}
                            className="input text-sm disabled:opacity-60 flex-shrink-0 w-48"
                          >
                            <option value="">-- Select Category --</option>
                            {allCategories.map((cat) => (
                              <option key={cat.id} value={cat.name}>
                                {cat.name}
                              </option>
                            ))}
                          </select>
                        )}

                        {/* Editable input for typing new category with autocomplete */}
                        <div className="flex-1 relative">
                          <input
                            type="text"
                            value={suggestion.is_new_category || suggestion.create_new_category ? suggestion.edited_category : ''}
                            onChange={(e) => {
                              const newValue = e.target.value;
                              const newSuggestions = [...suggestions];
                              
                              if (newValue.trim() === '') {
                                // Reset to dropdown mode if input is cleared
                                newSuggestions[originalIndex].edited_category = '';
                                newSuggestions[originalIndex].is_new_category = false;
                                newSuggestions[originalIndex].create_new_category = false;
                                setAutocompleteIndex(null);
                              } else {
                                // Switch to new category mode
                                newSuggestions[originalIndex].edited_category = newValue;
                                const categoryExists = allCategories.some(cat => cat.name === newValue);
                                newSuggestions[originalIndex].is_new_category = !categoryExists;
                                newSuggestions[originalIndex].create_new_category = !categoryExists;
                                
                                // Show autocomplete if typing
                                setAutocompleteIndex(originalIndex);
                                setAutocompleteQuery(newValue);
                              }
                              
                              setSuggestions(newSuggestions);
                            }}
                            onFocus={() => {
                              if (suggestion.edited_category) {
                                setAutocompleteIndex(originalIndex);
                                setAutocompleteQuery(suggestion.edited_category);
                              }
                            }}
                            onBlur={() => {
                              // Delay to allow clicking on autocomplete items
                              setTimeout(() => setAutocompleteIndex(null), 200);
                            }}
                            disabled={isApplied || creatingCategoryForIndex === originalIndex}
                            className="input w-full text-sm disabled:opacity-60"
                            placeholder="Type here to create new category..."
                          />
                          
                          {/* Autocomplete dropdown */}
                          {autocompleteIndex === originalIndex && autocompleteQuery && autocompleteQuery.trim() && (
                            (() => {
                              const matches = allCategories.filter(cat => 
                                cat.name.toLowerCase().includes((autocompleteQuery || '').toLowerCase())
                              );
                              
                              return matches.length > 0 ? (
                                <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-[var(--color-border)] rounded-lg shadow-lg max-h-48 overflow-y-auto z-10">
                                  {matches.map((cat) => (
                                    <button
                                      key={cat.id}
                                      type="button"
                                      onClick={() => {
                                        const newSuggestions = [...suggestions];
                                        newSuggestions[originalIndex].edited_category = cat.name;
                                        newSuggestions[originalIndex].is_new_category = false;
                                        newSuggestions[originalIndex].create_new_category = false;
                                        setSuggestions(newSuggestions);
                                        setAutocompleteQuery('');
                                        setAutocompleteIndex(null);
                                      }}
                                      className="w-full px-3 py-2 text-left text-sm hover:bg-[var(--color-bg-secondary)] transition-colors border-b border-[var(--color-border)] last:border-b-0"
                                    >
                                      <span className="text-[var(--color-text-primary)] font-medium">
                                        {cat.name}
                                      </span>
                                    </button>
                                  ))}
                                </div>
                              ) : null;
                            })()
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Row 3: Type + Pattern (together) */}
                    <div className="flex gap-3 items-start">
                      {/* Type (dropdown) - same width as category dropdown/button */}
                      <div className="flex-shrink-0 w-48">
                        <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                          Type
                        </label>
                        <select
                          value={suggestion.pattern_type}
                          onChange={(e) => {
                            const newSuggestions = [...suggestions];
                            newSuggestions[originalIndex].pattern_type = e.target.value;
                            setSuggestions(newSuggestions);
                          }}
                          disabled={isApplied}
                          className="input w-full text-sm disabled:opacity-60"
                        >
                          <option value="keyword">keyword</option>
                          <option value="keyword_or">keyword_or</option>
                          <option value="regex">regex</option>
                        </select>
                      </div>

                      {/* Pattern */}
                      <div className="flex-1 min-w-0">
                        <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                          Pattern
                        </label>
                        <input
                          type="text"
                          value={suggestion.edited_pattern}
                          onChange={(e) => {
                            const newSuggestions = [...suggestions];
                            newSuggestions[originalIndex].edited_pattern = e.target.value;
                            setSuggestions(newSuggestions);
                          }}
                          disabled={isApplied}
                          className="input w-full text-sm disabled:opacity-60 font-mono"
                          placeholder="Pattern"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
