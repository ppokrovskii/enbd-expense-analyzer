"use client";

import { useState, useEffect } from "react";
import SparkleIcon from "../ui/SparkleIcon";
import { Category } from "../../categories/page";

interface AISuggestion {
  merchant: string;
  suggested_category: string;
  suggested_pattern: string;
  pattern_type: string;
  transaction_count: number;
  total_amount: number;
}

interface EditableSuggestion extends AISuggestion {
  edited_category?: string;
  edited_pattern?: string;
  create_new_category?: boolean;
  status?: "pending" | "applied" | "rejected"; // Track status of each suggestion
}

interface AIBulkModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  level: "global" | "category" | "rule" | "merchant";
  categoryId?: number;
  ruleIndex?: number;
  merchant?: string;
  days: 30 | 60 | 90;
  allCategories: Category[];
  merchantsToCategorize?: string[]; // Optional list of specific merchants to categorize
}

export default function AIBulkModal({
  isOpen,
  onClose,
  onSuccess,
  level,
  categoryId,
  ruleIndex,
  merchant,
  days,
  allCategories,
  merchantsToCategorize,
}: AIBulkModalProps) {
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [suggestions, setSuggestions] = useState<EditableSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newCategoryName, setNewCategoryName] = useState("");

  useEffect(() => {
    if (isOpen) {
      fetchSuggestions();
    }
  }, [isOpen, level, categoryId, ruleIndex, merchant, days, merchantsToCategorize]);

  const fetchSuggestions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        days: days.toString(),
        level,
      });
      if (categoryId) params.set("category_id", categoryId.toString());
      if (ruleIndex !== undefined) params.set("rule_index", ruleIndex.toString());
      if (merchant) params.set("merchant", merchant);
      
      // If specific merchants are provided, add them as query params
      if (merchantsToCategorize && merchantsToCategorize.length > 0) {
        merchantsToCategorize.forEach(m => params.append("merchants", m));
      }

      const response = await fetch(
        `http://localhost:8000/api/categories/ai-bulk-suggest?${params}`
      );

      if (!response.ok) throw new Error("Failed to fetch AI suggestions");

      const data = await response.json();
      setSuggestions(data.map((s: AISuggestion) => ({ ...s, status: "pending" })));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load suggestions");
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setApplying(true);
    setError(null);

    try {
      // Only apply suggestions that are pending (not rejected or already applied)
      const pendingSuggestions = suggestions.filter(s => s.status === "pending");
      
      if (pendingSuggestions.length === 0) {
        // Nothing to apply, just close
        onClose();
        return;
      }
      
      const payload = {
        suggestions: pendingSuggestions.map((s) => ({
          merchant: s.merchant,
          category: s.edited_category || s.suggested_category,
          pattern: s.edited_pattern || s.suggested_pattern,
          pattern_type: s.pattern_type,
          create_new_category: s.create_new_category || false,
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

      // Close modal and refresh parent data
      onSuccess();
      onClose();
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
          category: suggestion.edited_category || suggestion.suggested_category,
          pattern: suggestion.edited_pattern || suggestion.suggested_pattern,
          pattern_type: suggestion.pattern_type,
          create_new_category: suggestion.create_new_category || false,
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

      if (!response.ok) throw new Error("Failed to apply suggestion");

      // Mark as applied
      const newSuggestions = [...suggestions];
      newSuggestions[index].status = "applied";
      setSuggestions(newSuggestions);
      
      // Auto-remove after 1 second (matching animation duration)
      setTimeout(() => {
        const filteredSuggestions = [...suggestions];
        filteredSuggestions[index].status = "rejected"; // Use rejected to hide it
        setSuggestions(filteredSuggestions);
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply suggestion");
    }
  };

  const handleReject = (index: number) => {
    const newSuggestions = [...suggestions];
    newSuggestions[index].status = "rejected";
    setSuggestions(newSuggestions);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (!isOpen) return null;

  // Filter to show only pending and applied suggestions (hide rejected)
  const visibleSuggestions = suggestions.filter(s => s.status !== "rejected");
  const pendingSuggestions = suggestions.filter(s => s.status === "pending");
  const appliedCount = suggestions.filter(s => s.status === "applied").length;
  const allProcessed = suggestions.length > 0 && visibleSuggestions.length === 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative bg-[var(--color-bg-primary)] rounded-xl shadow-lg max-w-6xl w-full mx-4 max-h-[90vh] flex flex-col">
        <div className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <SparkleIcon size={24} className="text-[var(--color-primary)]" />
            <h2 className="text-heading text-[var(--color-text-primary)]">
              AI Categorization Suggestions
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded-lg text-red-800 text-caption">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--color-primary)] mb-4"></div>
              <p className="text-body text-[var(--color-text-secondary)]">
                Analyzing merchants with AI...
              </p>
            </div>
          ) : visibleSuggestions.length === 0 ? (
            <div className="text-center py-12">
              {allProcessed ? (
                <div className="flex flex-col items-center">
                  <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4">
                    <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-heading text-[var(--color-text-primary)] mb-2">
                    All Suggestions Processed! ✨
                  </p>
                  <p className="text-body text-[var(--color-text-secondary)]">
                    {appliedCount} {appliedCount === 1 ? 'merchant' : 'merchants'} successfully categorized
                  </p>
                </div>
              ) : (
                <p className="text-body text-[var(--color-text-secondary)]">
                  No merchants found to categorize
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {visibleSuggestions.map((suggestion, visibleIndex) => {
                const originalIndex = suggestions.indexOf(suggestion);
                const isApplied = suggestion.status === "applied";
                
                return (
                <div 
                  key={originalIndex} 
                  className={`card p-4 transition-all duration-300 ${
                    isApplied 
                      ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800" 
                      : ""
                  }`}
                  style={isApplied ? { animation: "fadeOut 1s forwards" } : {}}
                >
                  <div className="grid grid-cols-12 gap-4 items-start">
                    <div className="col-span-4">
                      <p className="text-caption text-[var(--color-text-secondary)] mb-1">
                        Merchant
                      </p>
                      <p className="text-body font-medium text-[var(--color-text-primary)]">
                        {suggestion.merchant}
                      </p>
                      <p className="text-caption text-[var(--color-text-tertiary)]">
                        {suggestion.transaction_count} transactions ·{" "}
                        {formatCurrency(suggestion.total_amount)}
                      </p>
                    </div>

                    <div className="col-span-2">
                      <p className="text-caption text-[var(--color-text-secondary)] mb-1">
                        Category
                      </p>
                      {suggestion.create_new_category ? (
                        <div className="relative">
                          <input
                            type="text"
                            value={suggestion.edited_category || ""}
                            onChange={(e) => {
                              const newSuggestions = [...suggestions];
                              newSuggestions[originalIndex].edited_category = e.target.value;
                              setSuggestions(newSuggestions);
                            }}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && suggestion.edited_category) {
                                // Switch back to dropdown and show the new category
                                const newSuggestions = [...suggestions];
                                newSuggestions[originalIndex].create_new_category = false;
                                setSuggestions(newSuggestions);
                              } else if (e.key === 'Escape') {
                                // Cancel and go back to dropdown
                                const newSuggestions = [...suggestions];
                                newSuggestions[originalIndex].create_new_category = false;
                                newSuggestions[originalIndex].edited_category = suggestion.suggested_category;
                                setSuggestions(newSuggestions);
                              }
                            }}
                            placeholder="New category name (Enter to confirm)"
                            disabled={isApplied}
                            className="input w-full text-caption disabled:opacity-60"
                            autoFocus
                          />
                          <p className="text-caption text-[var(--color-text-tertiary)] mt-1">
                            Press Enter to confirm or Esc to cancel
                          </p>
                        </div>
                      ) : (
                        <select
                          value={suggestion.edited_category || suggestion.suggested_category}
                          onChange={(e) => {
                            const newSuggestions = [...suggestions];
                            if (e.target.value === "__new__") {
                              newSuggestions[originalIndex].create_new_category = true;
                              newSuggestions[originalIndex].edited_category = "";
                            } else {
                              newSuggestions[originalIndex].edited_category = e.target.value;
                              newSuggestions[originalIndex].create_new_category = false;
                            }
                            setSuggestions(newSuggestions);
                          }}
                          disabled={isApplied}
                          className="input w-full text-caption disabled:opacity-60"
                        >
                          {allCategories.map((cat) => (
                            <option key={cat.id} value={cat.name}>
                              {cat.name}
                            </option>
                          ))}
                          <option value="__new__">+ Create New...</option>
                        </select>
                      )}
                    </div>

                    <div className="col-span-2">
                      <p className="text-caption text-[var(--color-text-secondary)] mb-1">
                        Pattern
                      </p>
                      <input
                        type="text"
                        value={suggestion.edited_pattern || suggestion.suggested_pattern}
                        onChange={(e) => {
                          const newSuggestions = [...suggestions];
                          newSuggestions[originalIndex].edited_pattern = e.target.value;
                          setSuggestions(newSuggestions);
                        }}
                        disabled={isApplied}
                        className="input w-full text-caption disabled:opacity-60"
                      />
                    </div>

                    <div className="col-span-1">
                      <p className="text-caption text-[var(--color-text-secondary)] mb-1">
                        Type
                      </p>
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded text-caption font-medium ${
                          suggestion.pattern_type === "keyword"
                            ? "bg-blue-100 text-blue-800"
                            : suggestion.pattern_type === "keyword_or"
                            ? "bg-purple-100 text-purple-800"
                            : "bg-orange-100 text-orange-800"
                        }`}
                      >
                        {suggestion.pattern_type}
                      </span>
                    </div>

                    <div className="col-span-3 flex gap-2 justify-end pt-6">
                      {isApplied ? (
                        <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          <span className="text-caption font-medium">Applied</span>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={() => handleApplySingle(originalIndex)}
                            className="btn btn-primary text-caption py-1 px-3"
                          >
                            Apply
                          </button>
                          <button
                            onClick={() => handleReject(originalIndex)}
                            className="btn btn-secondary text-caption py-1 px-3"
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )})}
            </div>
          )}
        </div>

        <div className="border-t border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
          <p className="text-caption text-[var(--color-text-secondary)]">
            {pendingSuggestions.length} pending · {suggestions.filter(s => s.status === "applied").length} applied · {" "}
            {pendingSuggestions.reduce((sum, s) => sum + s.transaction_count, 0)} transactions affected
          </p>
          <div className="flex gap-3">
            {pendingSuggestions.length > 0 ? (
              <>
                <button
                  onClick={onClose}
                  className="btn btn-secondary"
                  disabled={applying}
                >
                  Cancel
                </button>
                <button
                  onClick={handleApply}
                  className="btn btn-primary flex items-center gap-2"
                  disabled={applying}
                >
                  <SparkleIcon size={16} />
                  {applying ? "Applying..." : `Apply ${pendingSuggestions.length} Pending`}
                </button>
              </>
            ) : (
              <button
                onClick={() => {
                  onSuccess(); // Refresh data when closing after all processed
                  onClose();
                }}
                className="btn btn-primary"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

