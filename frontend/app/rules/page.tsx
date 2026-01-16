/**
 * Rule Manager Page - Card-based Design Similar to AI Suggestions
 * 
 * Features:
 * - View all categorization rules in cards
 * - AI Suggestions mode: Generate rule suggestions for selected merchants
 * - Inline editing with live preview
 * - Conflict detection
 * - Search and filter by category
 * - Create new rules
 */

"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getApiHeaders, API_URL } from "../utils/api";

// Types
interface Rule {
  id: number;
  category_id: number;
  category_name: string;
  keywords: string[];
  exclude_keywords: string[];
  priority: number;
}

interface Category {
  id: number;
  name: string;
  color?: string;
}

interface PreviewResult {
  merchant: string;
  transaction_count: number;
  total_amount: number;
}

interface Conflict {
  rule_id: number;
  category_name: string;
  overlapping_keywords: string[];
  severity: "error" | "warning";
  suggestion: string;
}

interface EditingRule extends Rule {
  edited_keywords: string;
  edited_exclude_keywords: string;
  edited_category_id: number;
  edited_priority: number;
  isNew?: boolean;
}

interface AISuggestion {
  merchant: string;
  suggested_category: string;
  suggested_pattern: string;
  pattern_type: string;
  transaction_count: number;
  total_amount: number;
  is_new_category?: boolean;
}

interface PendingSuggestion extends AISuggestion {
  id: string;
  edited_category: string;
  edited_pattern: string;
  edited_pattern_type: string;
  status: "pending" | "applied" | "rejected";
  categoryId?: number;
}

export default function RulesManagerPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isAIMode = searchParams.get("mode") === "ai-suggest";
  
  // Data state
  const [rules, setRules] = useState<Rule[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // AI Suggestions state
  const [aiSuggestions, setAiSuggestions] = useState<PendingSuggestion[]>([]);
  const [aiMerchants, setAiMerchants] = useState<string[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [appliedCount, setAppliedCount] = useState(0);
  const [returnUrl, setReturnUrl] = useState<string | null>(null);
  
  // Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | null>(null);
  
  // Editing state
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [editingRule, setEditingRule] = useState<EditingRule | null>(null);
  const [saving, setSaving] = useState(false);
  
  // Preview state
  const [previewResults, setPreviewResults] = useState<PreviewResult[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // Conflict state
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [conflictsLoading, setConflictsLoading] = useState(false);
  
  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  
  // Recategorization
  const [isRecategorizing, setIsRecategorizing] = useState(false);
  
  // Pagination
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  // Initialize AI mode from sessionStorage
  useEffect(() => {
    if (isAIMode && typeof window !== "undefined") {
      const merchants = sessionStorage.getItem("rules_ai_merchants");
      const returnUrlStored = sessionStorage.getItem("rules_ai_return_url");
      
      if (merchants) {
        try {
          const parsed = JSON.parse(merchants);
          setAiMerchants(parsed);
        } catch (e) {
          console.error("Failed to parse merchants", e);
        }
      }
      
      if (returnUrlStored) {
        setReturnUrl(returnUrlStored);
      }
    }
  }, [isAIMode]);

  // Load categories and then rules/suggestions
  useEffect(() => {
    const init = async () => {
      await loadCategories();
      if (isAIMode && aiMerchants.length > 0) {
        await fetchAISuggestions();
      } else if (!isAIMode) {
        await loadRules();
      } else {
        setLoading(false);
      }
    };
    init();
  }, [isAIMode, aiMerchants]);

  // Reload rules when filters change (non-AI mode only)
  useEffect(() => {
    if (!isAIMode && !loading) {
      loadRules();
    }
  }, [categoryFilter, searchQuery]);

  // Refresh when person changes
  useEffect(() => {
    const handlePersonChange = () => {
      loadCategories();
      if (!isAIMode) {
        loadRules();
      }
    };
    window.addEventListener("personChanged", handlePersonChange);
    return () => window.removeEventListener("personChanged", handlePersonChange);
  }, [isAIMode]);

  const loadCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/categories/`, {
        headers: getApiHeaders(),
      });
      if (!response.ok) {
        const errorText = await response.text();
        console.error("Categories API error:", response.status, errorText);
        throw new Error("Failed to load categories");
      }
      const data = await response.json();
      console.log("Loaded categories:", data.length);
      setCategories(data);
    } catch (err) {
      console.error("Error loading categories:", err);
      setError(err instanceof Error ? err.message : "Failed to load categories");
    }
  };

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let url = `${API_URL}/api/rules/?limit=100`;
      if (categoryFilter) url += `&category_id=${categoryFilter}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
      
      const response = await fetch(url, {
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error("Failed to load rules");
      
      const data = await response.json();
      setRules(data.items);
      setTotal(data.total);
      setHasMore(data.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rules");
    } finally {
      setLoading(false);
    }
  };

  const fetchAISuggestions = async () => {
    setAiLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_URL}/api/categories/ai-bulk-suggest`,
        {
          method: "POST",
          headers: getApiHeaders(),
          body: JSON.stringify({
            days: 90,
            level: "global",
            merchants: aiMerchants,
            limit: 1000,
          }),
        }
      );

      if (!response.ok) {
        // Try to parse error response for user-friendly message
        try {
          const errorData = await response.json();
          const detail = errorData.detail;
          if (detail && typeof detail === 'object' && detail.user_message) {
            throw new Error(detail.user_message);
          } else if (detail && typeof detail === 'string') {
            throw new Error(detail);
          }
        } catch (parseError) {
          // If parsing fails, use generic message
          if (parseError instanceof Error && parseError.message !== "Failed to fetch AI suggestions") {
            throw parseError;
          }
        }
        throw new Error("Failed to fetch AI suggestions. Please try again later.");
      }
      
      const data = await response.json();
      
      const mapped: PendingSuggestion[] = data.map((s: AISuggestion, idx: number) => {
        const categoryExists = categories.find(cat => cat.name === s.suggested_category);
        return {
          ...s,
          id: `ai-${idx}`,
          edited_category: s.suggested_category,
          edited_pattern: s.suggested_pattern,
          edited_pattern_type: s.pattern_type,
          status: "pending" as const,
          categoryId: categoryExists?.id,
        };
      });
      
      setAiSuggestions(mapped);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AI suggestions");
    } finally {
      setAiLoading(false);
      setLoading(false);
    }
  };

  // Preview debounce
  useEffect(() => {
    if (!editingRule || !editingRule.edited_keywords.trim()) {
      setPreviewResults([]);
      return;
    }

    const timer = setTimeout(() => {
      fetchPreview();
    }, 300);

    return () => clearTimeout(timer);
  }, [editingRule?.edited_keywords, editingRule?.edited_exclude_keywords]);

  // Conflict check debounce
  useEffect(() => {
    if (!editingRule || !editingRule.edited_keywords.trim()) {
      setConflicts([]);
      return;
    }

    const timer = setTimeout(() => {
      checkConflicts();
    }, 300);

    return () => clearTimeout(timer);
  }, [editingRule?.edited_keywords]);

  const fetchPreview = async () => {
    if (!editingRule) return;
    
    setPreviewLoading(true);
    try {
      const keywords = editingRule.edited_keywords.split("|").map(k => k.trim()).filter(Boolean);
      const excludeKeywords = editingRule.edited_exclude_keywords.split("|").map(k => k.trim()).filter(Boolean);
      
      const response = await fetch(`${API_URL}/api/rules/test`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({
          keywords,
          exclude_keywords: excludeKeywords,
          limit: 10,
        }),
      });
      
      if (!response.ok) throw new Error("Preview failed");
      
      const data = await response.json();
      setPreviewResults(data.merchants || []);
    } catch (err) {
      console.error("Preview error:", err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const checkConflicts = async () => {
    if (!editingRule) return;
    
    setConflictsLoading(true);
    try {
      const keywords = editingRule.edited_keywords.split("|").map(k => k.trim()).filter(Boolean);
      
      const response = await fetch(`${API_URL}/api/rules/check-conflicts`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({
          keywords,
          exclude_rule_id: editingRule.isNew ? undefined : editingRule.id,
        }),
      });
      
      if (!response.ok) throw new Error("Conflict check failed");
      
      const data = await response.json();
      setConflicts(data.conflicts || []);
    } catch (err) {
      console.error("Conflict check error:", err);
    } finally {
      setConflictsLoading(false);
    }
  };

  const showToast = (message: string, duration: number = 6000) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), duration);
  };

  const startEditing = (rule: Rule) => {
    setEditingRuleId(rule.id);
    setEditingRule({
      ...rule,
      edited_keywords: rule.keywords.join(" | "),
      edited_exclude_keywords: rule.exclude_keywords.join(" | "),
      edited_category_id: rule.category_id,
      edited_priority: rule.priority,
    });
    setPreviewResults([]);
    setConflicts([]);
  };

  const startCreating = () => {
    const newRule: EditingRule = {
      id: -1,
      category_id: categories[0]?.id || 0,
      category_name: categories[0]?.name || "",
      keywords: [],
      exclude_keywords: [],
      priority: 0,
      edited_keywords: "",
      edited_exclude_keywords: "",
      edited_category_id: categories[0]?.id || 0,
      edited_priority: 0,
      isNew: true,
    };
    setEditingRuleId(-1);
    setEditingRule(newRule);
    setPreviewResults([]);
    setConflicts([]);
  };

  const cancelEditing = () => {
    setEditingRuleId(null);
    setEditingRule(null);
    setPreviewResults([]);
    setConflicts([]);
  };

  const saveRule = async () => {
    if (!editingRule) return;
    
    const keywords = editingRule.edited_keywords.split("|").map(k => k.trim()).filter(Boolean);
    const excludeKeywords = editingRule.edited_exclude_keywords.split("|").map(k => k.trim()).filter(Boolean);
    
    if (keywords.length === 0) {
      setError("At least one keyword is required");
      return;
    }
    
    setSaving(true);
    setError(null);
    
    try {
      if (editingRule.isNew) {
        const response = await fetch(`${API_URL}/api/rules/`, {
          method: "POST",
          headers: getApiHeaders(),
          body: JSON.stringify({
            category_id: editingRule.edited_category_id,
            keywords,
            exclude_keywords: excludeKeywords,
            priority: editingRule.edited_priority,
            auto_apply: true,
          }),
        });
        
        if (!response.ok) throw new Error("Failed to create rule");
        
        // Don't show local toast - WebSocket 'rules_applied' message will handle it
        // with proper transaction count and amount from the backend
      } else {
        const response = await fetch(`${API_URL}/api/rules/${editingRule.id}`, {
          method: "PUT",
          headers: getApiHeaders(),
          body: JSON.stringify({
            keywords,
            exclude_keywords: excludeKeywords,
            priority: editingRule.edited_priority,
          }),
        });
        
        if (!response.ok) throw new Error("Failed to update rule");
        showToast("Rule updated successfully");
      }
      
      cancelEditing();
      loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save rule");
    } finally {
      setSaving(false);
    }
  };

  const deleteRule = async (ruleId: number) => {
    if (!confirm("Are you sure you want to delete this rule?")) return;
    
    try {
      const response = await fetch(`${API_URL}/api/rules/${ruleId}`, {
        method: "DELETE",
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error("Failed to delete rule");
      
      showToast("Rule deleted");
      loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete rule");
    }
  };

  // Recategorize all transactions using all rules
  const handleRecategorizeAll = async () => {
    if (!confirm("This will re-apply all rules to all transactions. Continue?")) return;
    
    setIsRecategorizing(true);
    try {
      const response = await fetch(`${API_URL}/api/jobs/recategorize`, {
        method: "POST",
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error("Failed to start recategorization");
      
      // Don't show immediate toast - WebSocket will notify when complete
      // Just show a subtle indicator that the job has started
      showToast("Recategorization started in background...", 2000);
      
      // Reset button after a short delay - WebSocket will show actual completion
      setTimeout(() => setIsRecategorizing(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start recategorization");
      setIsRecategorizing(false);
    }
  };

  // AI Suggestion handlers
  const handleApplySuggestion = async (suggestion: PendingSuggestion) => {
    try {
      // Find or create category
      let categoryId = suggestion.categoryId;
      
      // First, check if the category already exists by name
      if (!categoryId) {
        const existingCategory = categories.find(
          c => c.name.toLowerCase() === suggestion.edited_category.toLowerCase()
        );
        if (existingCategory) {
          categoryId = existingCategory.id;
        }
      }
      
      // If still no category found, create a new one
      if (!categoryId) {
        const catResponse = await fetch(`${API_URL}/api/categories/`, {
          method: "POST",
          headers: getApiHeaders(),
          body: JSON.stringify({ name: suggestion.edited_category }),
        });
        
        if (!catResponse.ok) {
          const errorData = await catResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || "Failed to create category");
        }
        const catResult = await catResponse.json();
        // API returns { category: {...}, transactions_affected: N }
        const newCat = catResult.category;
        categoryId = newCat.id;
        
        // Update categories list
        setCategories(prev => [...prev, newCat]);
      }
      
      // Create the rule
      const keywords = suggestion.edited_pattern.split("|").map(k => k.trim()).filter(Boolean);
      
      const response = await fetch(`${API_URL}/api/rules/`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({
          category_id: categoryId,
          keywords,
          exclude_keywords: [],
          priority: 0,
          auto_apply: true,
        }),
      });
      
      if (!response.ok) throw new Error("Failed to create rule");
      
      // Consume response (WebSocket will show the toast with full details)
      await response.json();
      
      // Mark as applied
      setAiSuggestions(prev => 
        prev.map(s => s.id === suggestion.id ? { ...s, status: "applied" as const } : s)
      );
      setAppliedCount(prev => prev + 1);
      
      // Remove after animation
      setTimeout(() => {
        setAiSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply suggestion");
    }
  };

  const handleRejectSuggestion = (suggestionId: string) => {
    setAiSuggestions(prev => 
      prev.map(s => s.id === suggestionId ? { ...s, status: "rejected" as const } : s)
    );
    
    setTimeout(() => {
      setAiSuggestions(prev => prev.filter(s => s.id !== suggestionId));
    }, 500);
  };

  const handleApplyAll = async () => {
    const pending = aiSuggestions.filter(s => s.status === "pending");
    
    for (const suggestion of pending) {
      try {
        await handleApplySuggestion(suggestion);
      } catch (err) {
        console.error(`Failed to apply suggestion for ${suggestion.merchant}:`, err);
      }
    }
    // WebSocket will show individual toasts for each rule applied
  };

  const handleDone = () => {
    // Clean up sessionStorage
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("rules_ai_merchants");
      sessionStorage.removeItem("rules_ai_referrer");
      sessionStorage.removeItem("rules_ai_return_url");
    }
    
    if (returnUrl) {
      window.location.href = returnUrl;
    } else {
      router.push("/transactions");
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getCategoryColor = (categoryName: string) => {
    const cat = categories.find(c => c.name === categoryName);
    return cat?.color || "#6366f1";
  };

  const filteredRules = useMemo(() => rules, [rules]);
  const pendingSuggestions = aiSuggestions.filter(s => s.status === "pending");
  const allProcessed = isAIMode && aiSuggestions.length === 0 && !aiLoading && appliedCount > 0;
  
  // Calculate totals for pending suggestions
  const { totalTransactionCount, totalSuggestionsAmount } = useMemo(() => {
    return pendingSuggestions.reduce(
      (acc, s) => ({
        totalTransactionCount: acc.totalTransactionCount + (s.transaction_count || 0),
        totalSuggestionsAmount: acc.totalSuggestionsAmount + (s.total_amount || 0),
      }),
      { totalTransactionCount: 0, totalSuggestionsAmount: 0 }
    );
  }, [pendingSuggestions]);

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
                onClick={isAIMode ? handleDone : () => router.back()}
                className="flex-shrink-0 p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-apple"
                aria-label="Go back"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {isAIMode ? (
                    <svg className="w-5 h-5 text-purple-500 flex-shrink-0" viewBox="0 0 24 24" fill="none">
                      <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-[var(--color-primary)] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  )}
                  <h1 className="text-lg sm:text-xl font-semibold text-[var(--color-text-primary)]">
                    {isAIMode 
                      ? `${pendingSuggestions.length} Rule Suggestion${pendingSuggestions.length !== 1 ? 's' : ''}`
                      : "Rule Manager"
                    }
                  </h1>
                </div>
                {isAIMode ? (
                  <div className="flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
                    <div className="flex items-center gap-1.5">
                      <div className="w-24 h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-purple-500 transition-all duration-500"
                          style={{ width: `${aiMerchants.length > 0 ? (appliedCount / aiMerchants.length) * 100 : 0}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium">
                        {appliedCount} of {aiMerchants.length}
                      </span>
                    </div>
                    {totalTransactionCount > 0 && (
                      <span className="text-xs text-[var(--color-text-secondary)] border-l border-[var(--color-border)] pl-3">
                        {totalTransactionCount} transaction{totalTransactionCount !== 1 ? 's' : ''} · {formatCurrency(totalSuggestionsAmount)}
                      </span>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    {total} rule{total !== 1 ? 's' : ''} total
                  </p>
                )}
              </div>
            </div>
            
            {isAIMode ? (
              <div className="flex items-center gap-2">
                {pendingSuggestions.length > 0 && (
                  <button
                    onClick={handleApplyAll}
                    className="btn btn-primary text-sm sm:text-base"
                  >
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Apply All ({pendingSuggestions.length})
                    </span>
                  </button>
                )}
                {pendingSuggestions.length === 0 && !aiLoading && (
                  <button onClick={handleDone} className="btn btn-primary text-sm sm:text-base">
                    Done
                  </button>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRecategorizeAll}
                  disabled={isRecategorizing || editingRuleId !== null}
                  className="btn btn-secondary text-sm sm:text-base disabled:opacity-50"
                  title="Re-apply all rules to all transactions"
                >
                  <span className="flex items-center gap-1">
                    {isRecategorizing ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Running...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Recategorize All
                      </>
                    )}
                  </span>
                </button>
                <button
                  onClick={startCreating}
                  disabled={editingRuleId !== null}
                  className="btn btn-primary text-sm sm:text-base disabled:opacity-50"
                >
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    New Rule
                  </span>
                </button>
              </div>
            )}
          </div>
          
          {/* Filters - only show in non-AI mode */}
          {!isAIMode && (
            <div className="flex gap-3 mt-4">
              <div className="relative flex-1 max-w-md">
                <svg
                  className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[var(--color-text-tertiary)]"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search keywords..."
                  className="input pl-10 w-full"
                />
              </div>
              
              <select
                value={categoryFilter || ""}
                onChange={(e) => setCategoryFilter(e.target.value ? parseInt(e.target.value) : null)}
                className="input w-48"
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 sm:px-6 py-4 sm:py-6 max-w-5xl">
        {error && (
          <div className="mb-6 p-5 bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/20 border border-red-200 dark:border-red-800 rounded-xl shadow-sm">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-red-800 dark:text-red-200 mb-1">
                  {error.includes('quota') || error.includes('billing') 
                    ? 'AI Service Temporarily Unavailable'
                    : error.includes('rate') || error.includes('demand')
                    ? 'High Demand'
                    : 'Error'}
                </h3>
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
                {isAIMode && (
                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={() => {
                        setError(null);
                        fetchAISuggestions();
                      }}
                      className="px-4 py-2 text-sm font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                    >
                      Try Again
                    </button>
                    <button
                      onClick={() => {
                        setError(null);
                        router.push(returnUrl || '/transactions');
                      }}
                      className="px-4 py-2 text-sm font-medium bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-700 rounded-lg transition-colors"
                    >
                      Go Back
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* AI Mode Content */}
        {isAIMode && (
          <>
            {aiLoading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="relative">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-500"></div>
                  <svg className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-6 h-6 text-purple-500" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
                  </svg>
                </div>
                <p className="text-sm sm:text-base text-[var(--color-text-secondary)] mt-4">
                  Analyzing merchants with AI...
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
                  {appliedCount} rule{appliedCount !== 1 ? 's' : ''} created successfully
                </p>
              </div>
            ) : aiSuggestions.length === 0 && !aiLoading ? (
              <div className="text-center py-16">
                <div className="w-20 h-20 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mx-auto mb-4">
                  <svg className="w-10 h-10 text-[var(--color-text-tertiary)]" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
                  </svg>
                </div>
                <p className="text-sm sm:text-base text-[var(--color-text-secondary)]">
                  No rule suggestions found
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {aiSuggestions.filter(s => s.status !== "rejected").map((suggestion) => (
                  <AISuggestionCard
                    key={suggestion.id}
                    suggestion={suggestion}
                    categories={categories}
                    onApply={() => handleApplySuggestion(suggestion)}
                    onReject={() => handleRejectSuggestion(suggestion.id)}
                    onUpdate={(updates) => {
                      setAiSuggestions(prev =>
                        prev.map(s => s.id === suggestion.id ? { ...s, ...updates } : s)
                      );
                    }}
                    formatCurrency={formatCurrency}
                    getCategoryColor={getCategoryColor}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* Normal Rules Mode Content */}
        {!isAIMode && (
          <>
            {/* New Rule Card (when creating) */}
            {editingRuleId === -1 && editingRule && (
              <div className="mb-4">
                <RuleCard
                  rule={editingRule}
                  editing={true}
                  categories={categories}
                  onEdit={() => {}}
                  onDelete={() => cancelEditing()}
                  onSave={saveRule}
                  onCancel={cancelEditing}
                  editingRule={editingRule}
                  setEditingRule={setEditingRule}
                  previewResults={previewResults}
                  previewLoading={previewLoading}
                  conflicts={conflicts}
                  conflictsLoading={conflictsLoading}
                  saving={saving}
                  formatCurrency={formatCurrency}
                  getCategoryColor={getCategoryColor}
                  isNew={true}
                />
              </div>
            )}

            {loading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[var(--color-primary)]"></div>
                <p className="text-sm sm:text-base text-[var(--color-text-secondary)] mt-4">
                  Loading rules...
                </p>
              </div>
            ) : filteredRules.length === 0 ? (
              <div className="text-center py-16">
                <div className="w-20 h-20 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mx-auto mb-4">
                  <svg className="w-10 h-10 text-[var(--color-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
                  No rules found
                </h2>
                <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                  {searchQuery || categoryFilter ? "Try adjusting your filters" : "Create your first categorization rule"}
                </p>
                {!searchQuery && !categoryFilter && (
                  <button onClick={startCreating} className="btn btn-primary">
                    Create First Rule
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredRules.map((rule) => (
                  <RuleCard
                    key={rule.id}
                    rule={rule}
                    editing={editingRuleId === rule.id}
                    categories={categories}
                    onEdit={() => startEditing(rule)}
                    onDelete={() => deleteRule(rule.id)}
                    onSave={saveRule}
                    onCancel={cancelEditing}
                    editingRule={editingRuleId === rule.id ? editingRule : null}
                    setEditingRule={setEditingRule}
                    previewResults={editingRuleId === rule.id ? previewResults : []}
                    previewLoading={editingRuleId === rule.id ? previewLoading : false}
                    conflicts={editingRuleId === rule.id ? conflicts : []}
                    conflictsLoading={editingRuleId === rule.id ? conflictsLoading : false}
                    saving={saving}
                    formatCurrency={formatCurrency}
                    getCategoryColor={getCategoryColor}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// AI Suggestion Card Component
interface AISuggestionCardProps {
  suggestion: PendingSuggestion;
  categories: Category[];
  onApply: () => void;
  onReject: () => void;
  onUpdate: (updates: Partial<PendingSuggestion>) => void;
  formatCurrency: (amount: number) => string;
  getCategoryColor: (name: string) => string;
}

function AISuggestionCard({
  suggestion,
  categories,
  onApply,
  onReject,
  onUpdate,
  formatCurrency,
  getCategoryColor,
}: AISuggestionCardProps) {
  const isApplied = suggestion.status === "applied";
  const categoryExists = categories.some(c => c.name === suggestion.edited_category);
  
  return (
    <div
      className={`
        bg-[var(--color-bg-secondary)] 
        border border-[var(--color-border)]
        rounded-xl p-4 sm:p-5
        transition-all duration-300 
        hover:border-[var(--color-border-hover)]
        ${isApplied ? "animate-success-fade-out bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" : ""}
      `}
    >
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
                onClick={onApply}
                className="p-2 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/30 text-green-600 dark:text-green-400 transition-apple"
                title="Apply suggestion"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
              <button
                onClick={onReject}
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

        {/* Row 2: Category */}
        <div>
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
            Category
            {!categoryExists && (
              <span className="ml-2 text-xs text-amber-500">(will be created)</span>
            )}
          </label>
          <div className="flex gap-2">
            <select
              value={categoryExists ? suggestion.edited_category : ""}
              onChange={(e) => {
                if (e.target.value) {
                  const cat = categories.find(c => c.name === e.target.value);
                  onUpdate({ edited_category: e.target.value, categoryId: cat?.id });
                }
              }}
              disabled={isApplied}
              className="input text-sm flex-shrink-0 w-48 disabled:opacity-60"
            >
              <option value="">-- Select Existing --</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.name}>
                  {cat.name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={suggestion.edited_category}
              onChange={(e) => {
                const cat = categories.find(c => c.name === e.target.value);
                onUpdate({ edited_category: e.target.value, categoryId: cat?.id });
              }}
              disabled={isApplied}
              className="input flex-1 text-sm disabled:opacity-60"
              placeholder="Or type new category name..."
            />
          </div>
        </div>

        {/* Row 3: Pattern + Type */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <label className="block text-sm font-medium text-[var(--color-text-secondary)]">
              Pattern
            </label>
            <select
              value={suggestion.edited_pattern_type}
              onChange={(e) => onUpdate({ edited_pattern_type: e.target.value })}
              disabled={isApplied}
              className="input text-xs py-1 px-2 w-auto disabled:opacity-60"
              title="Pattern matching type"
            >
              <option value="keyword">Keyword (substring)</option>
              <option value="keyword_or">Keyword OR (pipe-separated)</option>
              <option value="regex">Regex</option>
            </select>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              suggestion.edited_pattern_type === 'regex' 
                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                : suggestion.edited_pattern_type === 'keyword_or'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
            }`}>
              {suggestion.edited_pattern_type === 'regex' ? '.*' : suggestion.edited_pattern_type === 'keyword_or' ? 'A|B' : 'ABC'}
            </span>
          </div>
          <input
            type="text"
            value={suggestion.edited_pattern}
            onChange={(e) => onUpdate({ edited_pattern: e.target.value })}
            disabled={isApplied}
            className="input w-full text-sm font-mono disabled:opacity-60"
            placeholder={
              suggestion.edited_pattern_type === 'regex' 
                ? '^PATTERN\\b or \\bWORD\\b'
                : suggestion.edited_pattern_type === 'keyword_or'
                ? 'keyword1|keyword2|keyword3'
                : 'keyword (matches as substring)'
            }
          />
          <p className="text-xs text-[var(--color-text-tertiary)]">
            {suggestion.edited_pattern_type === 'regex' 
              ? 'Regex: Use ^ for start, $ for end, \\b for word boundary'
              : suggestion.edited_pattern_type === 'keyword_or'
              ? 'Pipe-separated: Matches if ANY keyword is found'
              : 'Keyword: Matches if this text appears anywhere in merchant name'}
          </p>
        </div>
      </div>
    </div>
  );
}

// Rule Card Component
interface RuleCardProps {
  rule: Rule | EditingRule;
  editing: boolean;
  categories: Category[];
  onEdit: () => void;
  onDelete: () => void;
  onSave: () => void;
  onCancel: () => void;
  editingRule: EditingRule | null;
  setEditingRule: (rule: EditingRule | null) => void;
  previewResults: PreviewResult[];
  previewLoading: boolean;
  conflicts: Conflict[];
  conflictsLoading: boolean;
  saving: boolean;
  formatCurrency: (amount: number) => string;
  getCategoryColor: (name: string) => string;
  isNew?: boolean;
}

function RuleCard({
  rule,
  editing,
  categories,
  onEdit,
  onDelete,
  onSave,
  onCancel,
  editingRule,
  setEditingRule,
  previewResults,
  previewLoading,
  conflicts,
  saving,
  formatCurrency,
  getCategoryColor,
  isNew,
}: RuleCardProps) {
  const hasErrors = conflicts.some(c => c.severity === "error");
  
  if (editing && editingRule) {
    return (
      <div className="bg-[var(--color-bg-secondary)] border-2 border-[var(--color-primary)] rounded-xl p-4 sm:p-5">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
              {isNew ? "New Rule" : "Editing Rule"}
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={onCancel}
                className="px-3 py-1.5 text-sm rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-bg-tertiary)] transition-apple"
              >
                Cancel
              </button>
              <button
                onClick={onSave}
                disabled={saving || hasErrors}
                className="btn btn-primary text-sm disabled:opacity-50"
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                    Saving...
                  </span>
                ) : (
                  "Save"
                )}
              </button>
            </div>
          </div>
          
          {/* Category & Priority */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Category
              </label>
              <select
                value={editingRule.edited_category_id}
                onChange={(e) => setEditingRule({ ...editingRule, edited_category_id: parseInt(e.target.value) })}
                className="input w-full"
                disabled={!isNew}
              >
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="w-32">
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                Priority
              </label>
              <input
                type="number"
                value={editingRule.edited_priority}
                onChange={(e) => setEditingRule({ ...editingRule, edited_priority: parseInt(e.target.value) || 0 })}
                className="input w-full"
                min={0}
                max={100}
              />
            </div>
          </div>
          
          {/* Keywords */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Keywords <span className="text-[var(--color-text-tertiary)]">(separate with |)</span>
            </label>
            <input
              type="text"
              value={editingRule.edited_keywords}
              onChange={(e) => setEditingRule({ ...editingRule, edited_keywords: e.target.value })}
              placeholder="keyword1 | keyword2 | keyword3"
              className="input w-full font-mono"
              autoFocus
            />
          </div>
          
          {/* Exclude Keywords */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
              Exclude Keywords <span className="text-[var(--color-text-tertiary)]">(optional)</span>
            </label>
            <input
              type="text"
              value={editingRule.edited_exclude_keywords}
              onChange={(e) => setEditingRule({ ...editingRule, edited_exclude_keywords: e.target.value })}
              placeholder="exclude1 | exclude2"
              className="input w-full font-mono"
            />
          </div>
          
          {/* Conflict Warnings */}
          {conflicts.length > 0 && (
            <div className={`p-3 rounded-lg border ${hasErrors ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'}`}>
              <div className="flex items-start gap-2">
                <svg className={`w-5 h-5 flex-shrink-0 ${hasErrors ? 'text-red-500' : 'text-amber-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div className="flex-1">
                  <p className={`text-sm font-medium ${hasErrors ? 'text-red-800 dark:text-red-200' : 'text-amber-800 dark:text-amber-200'}`}>
                    {hasErrors ? 'Rule Conflicts Detected' : 'Potential Overlaps'}
                  </p>
                  <ul className="mt-1 space-y-1">
                    {conflicts.map((c, i) => (
                      <li key={i} className={`text-xs ${hasErrors ? 'text-red-700 dark:text-red-300' : 'text-amber-700 dark:text-amber-300'}`}>
                        <span className="font-medium">{c.category_name}</span>: {c.overlapping_keywords.join(", ")}
                        {c.suggestion && <span className="block text-[var(--color-text-tertiary)]">→ {c.suggestion}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
          
          {/* Preview */}
          {editingRule.edited_keywords.trim() && (
            <div className="border-t border-[var(--color-border)] pt-4">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-4 h-4 text-[var(--color-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span className="text-sm font-medium text-[var(--color-text-primary)]">
                  Live Preview
                </span>
                {previewLoading && (
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-[var(--color-primary)]"></div>
                )}
              </div>
              
              {previewResults.length > 0 ? (
                <div className="space-y-2">
                  {previewResults.map((m, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-[var(--color-bg-tertiary)] rounded-lg text-sm">
                      <span className="font-medium text-[var(--color-text-primary)] truncate">{m.merchant}</span>
                      <span className="text-[var(--color-text-secondary)] flex-shrink-0 ml-2">
                        {m.transaction_count} txn · {formatCurrency(m.total_amount)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : !previewLoading ? (
                <p className="text-sm text-[var(--color-text-tertiary)]">
                  No matching merchants found
                </p>
              ) : null}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Read-only view
  const categoryColor = getCategoryColor(rule.category_name);
  
  return (
    <div className="bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-xl p-4 sm:p-5 hover:border-[var(--color-border-hover)] transition-apple group">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Category Badge */}
          <div className="flex items-center gap-2 mb-2">
            <span
              className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
              style={{
                backgroundColor: `${categoryColor}20`,
                color: categoryColor,
              }}
            >
              {rule.category_name}
            </span>
            {rule.priority > 0 && (
              <span className="text-xs text-[var(--color-text-tertiary)]">
                Priority: {rule.priority}
              </span>
            )}
          </div>
          
          {/* Keywords */}
          <div className="mb-2">
            <span className="text-sm font-medium text-[var(--color-text-primary)]">
              {rule.keywords.join(" | ")}
            </span>
          </div>
          
          {/* Exclude Keywords */}
          {rule.exclude_keywords.length > 0 && (
            <div className="text-xs text-[var(--color-text-tertiary)]">
              <span className="text-red-400">Excludes:</span> {rule.exclude_keywords.join(" | ")}
            </div>
          )}
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-apple">
          <button
            onClick={onEdit}
            className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-apple"
            title="Edit rule"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            onClick={onDelete}
            className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30 text-[var(--color-text-secondary)] hover:text-red-500 transition-apple"
            title="Delete rule"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
