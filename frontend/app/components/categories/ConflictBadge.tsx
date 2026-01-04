"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE_URL } from "../../constants/api";

interface RuleConflict {
  rule_id: number;
  category_id: number;
  category_name: string;
  keywords: string[];
  overlapping_keywords: string[];
  severity: "error" | "warning";
}

interface ConflictCheckResponse {
  conflicts: RuleConflict[];
  has_conflicts: boolean;
}

interface ConflictBadgeProps {
  keywords: string[];
  excludeKeywords: string[];
  ruleId?: number; // Exclude this rule from conflict check (edit mode)
  debounceMs?: number;
  onConflictsChange?: (hasConflicts: boolean, conflicts: RuleConflict[]) => void;
}

export default function ConflictBadge({
  keywords,
  excludeKeywords,
  ruleId,
  debounceMs = 300,
  onConflictsChange,
}: ConflictBadgeProps) {
  const [conflicts, setConflicts] = useState<RuleConflict[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Check for conflicts with debouncing
  const checkConflicts = useCallback(async () => {
    if (keywords.length === 0) {
      setConflicts([]);
      onConflictsChange?.(false, []);
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/rules/check-conflicts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "test_user",
        },
        body: JSON.stringify({
          keywords,
          exclude_keywords: excludeKeywords,
          rule_id: ruleId || null,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to check conflicts");
      }

      const data: ConflictCheckResponse = await response.json();
      setConflicts(data.conflicts);
      onConflictsChange?.(data.has_conflicts, data.conflicts);
    } catch (err) {
      console.error("Conflict check failed:", err);
      setConflicts([]);
      onConflictsChange?.(false, []);
    } finally {
      setLoading(false);
    }
  }, [keywords, excludeKeywords, ruleId, onConflictsChange]);

  // Debounced effect
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      checkConflicts();
    }, debounceMs);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [checkConflicts, debounceMs]);

  if (loading) {
    return (
      <span className="inline-flex items-center gap-1 text-caption text-[var(--color-text-tertiary)]">
        <div className="animate-spin rounded-full h-3 w-3 border-b border-current"></div>
        Checking...
      </span>
    );
  }

  if (conflicts.length === 0) {
    return null;
  }

  const hasError = conflicts.some((c) => c.severity === "error");
  const badgeColor = hasError
    ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
    : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";

  const iconColor = hasError
    ? "text-red-500 dark:text-red-400"
    : "text-amber-500 dark:text-amber-400";

  return (
    <div className="relative">
      {/* Badge */}
      <button
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-caption font-medium ${badgeColor} transition-apple hover:opacity-80`}
      >
        {/* Warning/Error Icon */}
        <svg className={`w-4 h-4 ${iconColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {hasError ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          )}
        </svg>
        {conflicts.length} conflict{conflicts.length !== 1 ? "s" : ""}
        {/* Expand/Collapse Arrow */}
        <svg
          className={`w-3 h-3 transform transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div className="absolute z-10 mt-2 left-0 w-80 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg shadow-lg">
          <div className="p-3 border-b border-[var(--color-border-light)]">
            <h4 className="text-caption font-semibold text-[var(--color-text-primary)]">
              Rule Conflicts
            </h4>
            <p className="text-caption text-[var(--color-text-secondary)] mt-1">
              {hasError
                ? "These keywords conflict with existing rules"
                : "These keywords may overlap with existing rules"}
            </p>
          </div>

          <div className="max-h-64 overflow-y-auto p-2 space-y-2">
            {conflicts.map((conflict, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg ${
                  conflict.severity === "error"
                    ? "bg-red-50 dark:bg-red-900/20"
                    : "bg-amber-50 dark:bg-amber-900/20"
                }`}
              >
                <div className="flex items-start gap-2">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 rounded text-caption font-medium uppercase ${
                      conflict.severity === "error"
                        ? "bg-red-200 text-red-800 dark:bg-red-800 dark:text-red-200"
                        : "bg-amber-200 text-amber-800 dark:bg-amber-800 dark:text-amber-200"
                    }`}
                  >
                    {conflict.severity}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-caption font-medium text-[var(--color-text-primary)]">
                      {conflict.category_name}
                    </p>
                    <p className="text-caption text-[var(--color-text-secondary)] mt-1">
                      Rule keywords: {conflict.keywords.join(", ")}
                    </p>
                    <p className="text-caption text-[var(--color-text-tertiary)] mt-0.5">
                      Overlapping: <span className="font-medium">{conflict.overlapping_keywords.join(", ")}</span>
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Suggestions */}
          <div className="p-3 border-t border-[var(--color-border-light)] bg-[var(--color-bg-secondary)]">
            <p className="text-caption text-[var(--color-text-secondary)]">
              <strong>Suggestions:</strong>
              {hasError ? (
                <span> Remove duplicate keywords or merge with existing rule.</span>
              ) : (
                <span> Consider adding exclude keywords to avoid overlaps.</span>
              )}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

