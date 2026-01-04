/**
 * Rule Manager Page - Card-based Design Similar to AI Suggestions
 * 
 * Features:
 * - View all categorization rules in cards
 * - Inline editing with live preview
 * - Conflict detection
 * - Search and filter by category
 * - Create new rules
 */

"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getApiHeaders } from "../utils/api";

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

export default function RulesManagerPage() {
  const router = useRouter();
  
  // Data state
  const [rules, setRules] = useState<Rule[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
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
  
  // Pagination
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  // Load data
  useEffect(() => {
    loadCategories();
    loadRules();
  }, [categoryFilter, searchQuery]);

  // Refresh when person changes
  useEffect(() => {
    const handlePersonChange = () => {
      loadCategories();
      loadRules();
    };
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, []);

  const loadCategories = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/categories/", {
        headers: getApiHeaders(),
      });
      if (!response.ok) throw new Error("Failed to load categories");
      const data = await response.json();
      setCategories(data);
    } catch (err) {
      console.error("Error loading categories:", err);
    }
  };

  const loadRules = async () => {
    setLoading(true);
    setError(null);
    
    try {
      let url = "http://localhost:8000/api/rules/?limit=100";
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
      
      const response = await fetch("http://localhost:8000/api/rules/test", {
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
      
      const response = await fetch("http://localhost:8000/api/rules/check-conflicts", {
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

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 3000);
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
        // Create new rule
        const response = await fetch("http://localhost:8000/api/rules/", {
          method: "POST",
          headers: getApiHeaders(),
          body: JSON.stringify({
            category_id: editingRule.edited_category_id,
            keywords,
            exclude_keywords: excludeKeywords,
            priority: editingRule.edited_priority,
          }),
        });
        
        if (!response.ok) throw new Error("Failed to create rule");
        
        showToast("Rule created successfully");
      } else {
        // Update existing rule
        const response = await fetch(`http://localhost:8000/api/rules/${editingRule.id}`, {
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
      const response = await fetch(`http://localhost:8000/api/rules/${ruleId}`, {
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

  // Filter rules based on search
  const filteredRules = useMemo(() => {
    return rules;
  }, [rules]);

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
                onClick={() => router.back()}
                className="flex-shrink-0 p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-apple"
                aria-label="Go back"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <svg className="w-5 h-5 text-[var(--color-primary)] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <h1 className="text-lg sm:text-xl font-semibold text-[var(--color-text-primary)]">
                    Rule Manager
                  </h1>
                </div>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  {total} rule{total !== 1 ? 's' : ''} total
                </p>
              </div>
            </div>
            
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
          
          {/* Filters */}
          <div className="flex gap-3 mt-4">
            {/* Search */}
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
            
            {/* Category filter */}
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
  conflictsLoading,
  saving,
  formatCurrency,
  getCategoryColor,
  isNew,
}: RuleCardProps) {
  const hasErrors = conflicts.some(c => c.severity === "error");
  const hasWarnings = conflicts.some(c => c.severity === "warning");
  
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

