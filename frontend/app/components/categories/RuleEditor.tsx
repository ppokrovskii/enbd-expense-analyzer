"use client";

import { useState, useEffect, useMemo } from "react";
import { Category } from "../../categories/page";
import { API_BASE_URL } from "../../constants/api";
import RulePreview from "./RulePreview";
import ConflictBadge from "./ConflictBadge";

interface RuleWithCategory {
  id: number;
  category_id: number;
  category_name: string;
  keywords: string[];
  exclude_keywords: string[];
  priority: number;
}

interface RuleEditorProps {
  rule: RuleWithCategory;
  categories: Category[];
  onSave: () => void;
  onCancel: () => void;
  onDelete?: () => void;
}

export default function RuleEditor({
  rule,
  categories,
  onSave,
  onCancel,
  onDelete,
}: RuleEditorProps) {
  const [keywords, setKeywords] = useState<string>(rule.keywords.join(", "));
  const [excludeKeywords, setExcludeKeywords] = useState<string>(
    rule.exclude_keywords.join(", ")
  );
  const [categoryId, setCategoryId] = useState<number>(rule.category_id);
  const [priority, setPriority] = useState<number>(rule.priority);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(true);
  const [hasConflicts, setHasConflicts] = useState(false);

  // Reset form when rule changes
  useEffect(() => {
    setKeywords(rule.keywords.join(", "));
    setExcludeKeywords(rule.exclude_keywords.join(", "));
    setCategoryId(rule.category_id);
    setPriority(rule.priority);
    setError(null);
    setHasConflicts(false);
  }, [rule]);

  // Parse keywords for preview
  const keywordList = useMemo(() => {
    return keywords
      .split(",")
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0);
  }, [keywords]);

  const excludeList = useMemo(() => {
    return excludeKeywords
      .split(",")
      .map((kw) => kw.trim())
      .filter((kw) => kw.length > 0);
  }, [excludeKeywords]);

  const handleConflictsChange = (hasConflicts: boolean) => {
    setHasConflicts(hasConflicts);
  };

  const handleSave = async () => {
    if (keywordList.length === 0) {
      setError("At least one keyword is required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/rules/${rule.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "test_user",
        },
        body: JSON.stringify({
          keywords: keywordList,
          exclude_keywords: excludeList,
          priority,
          category_id: categoryId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update rule");
      }

      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update rule");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this rule?")) {
      return;
    }

    setDeleting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/rules/${rule.id}`, {
        method: "DELETE",
        headers: {
          "X-User-Id": "test_user",
        },
      });

      if (!response.ok) {
        throw new Error("Failed to delete rule");
      }

      onDelete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete rule");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="bg-[var(--color-bg-secondary)] rounded-lg border border-[var(--color-border)] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-light)]">
        <div className="flex items-center gap-3">
          <h4 className="text-body font-semibold text-[var(--color-text-primary)]">
            Edit Rule
          </h4>
          {/* Conflict Badge */}
          <ConflictBadge
            keywords={keywordList}
            excludeKeywords={excludeList}
            ruleId={rule.id}
            debounceMs={500}
            onConflictsChange={handleConflictsChange}
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className={`text-caption px-2 py-1 rounded transition-apple ${
              showPreview 
                ? "bg-[var(--color-primary)] bg-opacity-10 text-[var(--color-primary)]" 
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            {showPreview ? "Hide Preview" : "Show Preview"}
          </button>
          <button
            onClick={onCancel}
            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className={`${showPreview ? 'flex flex-col lg:flex-row' : ''}`}>
        {/* Editor Panel */}
        <div className={`p-4 space-y-4 ${showPreview ? 'lg:w-1/2 lg:border-r lg:border-[var(--color-border-light)]' : ''}`}>
          {/* Keywords */}
          <div>
            <label className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1">
              Keywords (comma-separated)
            </label>
            <textarea
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="e.g., STARBUCKS, COSTA"
              rows={2}
              className="input w-full text-sm"
            />
            <p className="text-caption text-[var(--color-text-tertiary)] mt-1">
              Use | for OR patterns: STARBUCKS|COSTA
            </p>
          </div>

          {/* Exclude Keywords */}
          <div>
            <label className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1">
              Exclude Keywords (comma-separated)
            </label>
            <input
              type="text"
              value={excludeKeywords}
              onChange={(e) => setExcludeKeywords(e.target.value)}
              placeholder="e.g., REFUND, REVERSAL"
              className="input w-full text-sm"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1">
              Category
            </label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(Number(e.target.value))}
              className="input w-full text-sm"
            >
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1">
              Priority (higher = checked first)
            </label>
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
              min={0}
              max={100}
              className="input w-20 text-sm"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <p className="text-caption text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {/* Conflict Warning */}
          {hasConflicts && (
            <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
              <p className="text-caption text-amber-700 dark:text-amber-400">
                <strong>Warning:</strong> This rule has potential conflicts with other rules.
                You can still save, but consider resolving overlaps.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border-light)]">
            <button
              onClick={handleDelete}
              disabled={deleting || saving}
              className="text-caption text-red-600 dark:text-red-400 hover:underline disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete Rule"}
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={onCancel}
                disabled={saving || deleting}
                className="btn btn-secondary text-caption py-1.5 px-3"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || deleting}
                className="btn btn-primary text-caption py-1.5 px-3"
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>

        {/* Preview Panel */}
        {showPreview && (
          <div className="p-4 lg:w-1/2 bg-[var(--color-bg-primary)] border-t lg:border-t-0 border-[var(--color-border-light)]">
            <RulePreview
              keywords={keywordList}
              excludeKeywords={excludeList}
              debounceMs={300}
            />
          </div>
        )}
      </div>
    </div>
  );
}
