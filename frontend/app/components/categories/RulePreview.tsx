"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { API_BASE_URL } from "../../constants/api";

interface MatchingMerchant {
  merchant: string;
  transaction_count: number;
  total_amount: number;
  matched_keyword: string;
}

interface SampleTransaction {
  id: number;
  date: string;
  merchant: string;
  description: string;
  amount: number;
  matched_text: string;
}

interface RuleTestResponse {
  matching_merchants: MatchingMerchant[];
  match_count: number;
  total_transactions: number;
  sample_transactions: SampleTransaction[];
}

interface RulePreviewProps {
  keywords: string[];
  excludeKeywords: string[];
  debounceMs?: number;
}

export default function RulePreview({
  keywords,
  excludeKeywords,
  debounceMs = 300,
}: RulePreviewProps) {
  const [preview, setPreview] = useState<RuleTestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTransactions, setShowTransactions] = useState(false);
  
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch preview with debouncing
  const fetchPreview = useCallback(async () => {
    if (keywords.length === 0) {
      setPreview(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/rules/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "test_user",
        },
        body: JSON.stringify({
          keywords,
          exclude_keywords: excludeKeywords,
          limit: 20,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch preview");
      }

      const data: RuleTestResponse = await response.json();
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setLoading(false);
    }
  }, [keywords, excludeKeywords]);

  // Debounced effect
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchPreview();
    }, debounceMs);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [fetchPreview, debounceMs]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Math.abs(amount));
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-AE", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  // Highlight matched text in a string
  const highlightMatch = (text: string, matchedText: string) => {
    if (!matchedText) return text;
    
    const lowerText = text.toLowerCase();
    const lowerMatch = matchedText.toLowerCase();
    const index = lowerText.indexOf(lowerMatch);
    
    if (index === -1) return text;
    
    const before = text.substring(0, index);
    const match = text.substring(index, index + matchedText.length);
    const after = text.substring(index + matchedText.length);
    
    return (
      <>
        {before}
        <mark className="bg-yellow-200 dark:bg-yellow-700 text-inherit rounded px-0.5">
          {match}
        </mark>
        {after}
      </>
    );
  };

  if (keywords.length === 0) {
    return (
      <div className="p-4 bg-[var(--color-bg-tertiary)] rounded-lg">
        <p className="text-caption text-[var(--color-text-secondary)] text-center">
          Enter keywords to preview matching merchants
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4 bg-[var(--color-bg-tertiary)] rounded-lg">
        <div className="flex items-center justify-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[var(--color-primary)]"></div>
          <span className="text-caption text-[var(--color-text-secondary)]">
            Loading preview...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
        <p className="text-caption text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!preview) {
    return null;
  }

  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-caption font-semibold text-[var(--color-text-primary)]">
            Preview Results
          </h4>
          <span className="text-caption text-[var(--color-text-secondary)]">
            {preview.match_count} merchants · {preview.total_transactions} transactions
          </span>
        </div>
        
        {preview.match_count === 0 ? (
          <p className="text-caption text-[var(--color-text-secondary)]">
            No merchants match these keywords
          </p>
        ) : (
          <div className="flex items-center gap-2 text-caption text-green-600 dark:text-green-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Rule will match {preview.match_count} merchant{preview.match_count !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Matching Merchants */}
      {preview.matching_merchants.length > 0 && (
        <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
          <h4 className="text-caption font-semibold text-[var(--color-text-primary)] mb-2">
            Matching Merchants
          </h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {preview.matching_merchants.map((m, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 bg-[var(--color-bg-secondary)] rounded"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-caption font-medium text-[var(--color-text-primary)] truncate">
                    {highlightMatch(m.merchant, m.matched_keyword)}
                  </p>
                  <p className="text-caption text-[var(--color-text-tertiary)]">
                    matched: "{m.matched_keyword}"
                  </p>
                </div>
                <div className="text-right flex-shrink-0 ml-2">
                  <p className="text-caption text-[var(--color-text-primary)]">
                    {formatCurrency(m.total_amount)}
                  </p>
                  <p className="text-caption text-[var(--color-text-tertiary)]">
                    {m.transaction_count} txn{m.transaction_count !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sample Transactions Toggle */}
      {preview.sample_transactions.length > 0 && (
        <div className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg">
          <button
            onClick={() => setShowTransactions(!showTransactions)}
            className="flex items-center justify-between w-full text-left"
          >
            <h4 className="text-caption font-semibold text-[var(--color-text-primary)]">
              Sample Transactions
            </h4>
            <svg
              className={`w-4 h-4 text-[var(--color-text-secondary)] transform transition-transform ${
                showTransactions ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showTransactions && (
            <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
              {preview.sample_transactions.map((txn) => (
                <div
                  key={txn.id}
                  className="p-2 bg-[var(--color-bg-secondary)] rounded text-caption"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-[var(--color-text-primary)]">
                      {txn.merchant}
                    </span>
                    <span className={`font-medium ${txn.amount < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                      {formatCurrency(txn.amount)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[var(--color-text-tertiary)] truncate max-w-[60%]">
                      {txn.description}
                    </span>
                    <span className="text-[var(--color-text-tertiary)]">
                      {formatDate(txn.date)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

