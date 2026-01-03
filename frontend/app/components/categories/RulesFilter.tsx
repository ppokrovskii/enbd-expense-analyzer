"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Category } from "../../categories/page";
import { API_BASE_URL } from "../../constants/api";

interface RulesFilterProps {
  selectedCategory: Category | null;
  selectedRuleIndex: number | null;
  onRuleSelect: (ruleIndex: number | null) => void;
  onCategoryUpdate: () => void;
  selectedCategoryIds: number[];
  categories: Category[];
  searchQuery: string;
}

interface RuleWithCategory {
  id: number;
  category_id: number;
  category_name: string;
  keywords: string[];
  exclude_keywords: string[];
  priority: number;
}

interface PaginatedRulesResponse {
  items: RuleWithCategory[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

const RULES_PAGE_SIZE = 20;

export default function RulesFilter({
  selectedCategory,
  selectedRuleIndex,
  onRuleSelect,
  onCategoryUpdate,
  selectedCategoryIds,
  categories,
  searchQuery,
}: RulesFilterProps) {
  // State for paginated rules (when no category is selected)
  const [allRules, setAllRules] = useState<RuleWithCategory[]>([]);
  const [totalRules, setTotalRules] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [offset, setOffset] = useState(0);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const loadingRef = useRef(false);

  // Fetch rules from API with pagination
  const fetchRules = useCallback(async (currentOffset: number, append: boolean = false) => {
    if (loadingRef.current) return;
    
    loadingRef.current = true;
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }

    try {
      const params = new URLSearchParams({
        offset: currentOffset.toString(),
        limit: RULES_PAGE_SIZE.toString(),
      });
      
      if (searchQuery) {
        params.append('search', searchQuery);
      }

      const response = await fetch(`${API_BASE_URL}/rules/?${params}`);
      if (!response.ok) throw new Error('Failed to fetch rules');
      
      const data: PaginatedRulesResponse = await response.json();
      
      if (append) {
        setAllRules(prev => [...prev, ...data.items]);
      } else {
        setAllRules(data.items);
      }
      
      setTotalRules(data.total);
      setHasMore(data.has_more);
      setOffset(currentOffset + data.items.length);
    } catch (err) {
      console.error('Failed to fetch rules:', err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
      loadingRef.current = false;
    }
  }, [searchQuery]);

  // Reset and fetch when search query changes or when switching to "all rules" view
  useEffect(() => {
    if (!selectedCategory && selectedCategoryIds.length === 0) {
      setOffset(0);
      setAllRules([]);
      fetchRules(0, false);
    }
  }, [selectedCategory, selectedCategoryIds.length, searchQuery, fetchRules]);

  // Load more rules on scroll
  const handleScroll = useCallback(() => {
    if (!containerRef.current || !hasMore || loadingRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // Load more when scrolled to 80% of the container
    if (scrollTop + clientHeight >= scrollHeight * 0.8) {
      fetchRules(offset, true);
    }
  }, [hasMore, offset, fetchRules]);

  // Attach scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (container && !selectedCategory && selectedCategoryIds.length === 0) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll, selectedCategory, selectedCategoryIds.length]);

  // Filter rules by search query (for single category view)
  const filterRulesBySearch = (rules: string[]) => {
    if (!searchQuery) return rules;
    const query = searchQuery.toLowerCase();
    return rules.filter(rule => rule.toLowerCase().includes(query));
  };

  // If single category selected, show its rules as filters
  if (selectedCategory) {
    const allCategoryRules = selectedCategory.keywords || [];
    const rules = filterRulesBySearch(allCategoryRules);

    return (
      <div className="p-4">
        <div className="mb-4">
          <h3 className="text-body font-semibold text-[var(--color-text-primary)] mb-1">
            Rules
            {selectedRuleIndex !== null && (
              <span className="ml-2 text-caption text-[var(--color-text-secondary)]">
                (1 selected)
              </span>
            )}
            {searchQuery && rules.length < allCategoryRules.length && (
              <span className="ml-2 text-caption text-[var(--color-text-secondary)]">
                ({rules.length} of {allCategoryRules.length})
              </span>
            )}
          </h3>
          <p className="text-caption text-[var(--color-text-secondary)]">
            for {selectedCategory.name}
          </p>
        </div>

        {rules.length === 0 ? (
          <div className="card p-6 text-center">
            <p className="text-caption text-[var(--color-text-secondary)]">
              {searchQuery ? 'No rules match your search' : 'No rules defined'}
            </p>
          </div>
        ) : (
          <>
            <div className="mb-3">
              <button
                onClick={() => onRuleSelect(null)}
                className="text-caption text-[var(--color-primary)] hover:underline"
              >
                {selectedRuleIndex !== null ? "Clear Filter" : "All Rules"}
              </button>
            </div>
            <div className="space-y-2">
              {rules.map((rule, index) => {
                const isSelected = selectedRuleIndex === index;
                const patternType = getPatternType(rule);

                return (
                  <button
                    key={index}
                    onClick={() => {
                      if (isSelected) {
                        onRuleSelect(null);
                      } else {
                        onRuleSelect(index);
                      }
                    }}
                    className={`w-full text-left p-3 rounded-lg transition-apple ${
                      isSelected
                        ? "bg-[var(--color-primary)] bg-opacity-10 border-2 border-[var(--color-primary)]"
                        : "bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)]"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-body font-medium text-[var(--color-text-primary)] truncate flex-1">
                        {rule}
                      </span>
                      {isSelected && (
                        <svg className="w-4 h-4 text-[var(--color-primary)] flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-caption font-medium ${getPatternTypeBadgeClass(
                        patternType
                      )}`}
                    >
                      {patternType}
                    </span>
                  </button>
                );
              })}
            </div>
          </>
        )}

        <div className="mt-4">
          <button
            className="w-full btn btn-secondary py-2 text-caption"
          >
            + Add Rule
          </button>
        </div>
      </div>
    );
  }

  // No category selected - show all rules with infinite scroll
  return (
    <div ref={containerRef} className="p-4 h-full overflow-y-auto">
      <div className="mb-4">
        <h3 className="text-body font-semibold text-[var(--color-text-primary)] mb-1">
          All Rules
          {!loading && (
            <span className="ml-2 text-caption text-[var(--color-text-secondary)]">
              ({totalRules} total)
            </span>
          )}
        </h3>
        <p className="text-caption text-[var(--color-text-secondary)]">
          {searchQuery 
            ? `Showing rules matching "${searchQuery}"`
            : 'Showing all rules from all categories'}
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]"></div>
        </div>
      ) : allRules.length === 0 ? (
        <div className="card p-6 text-center">
          <p className="text-caption text-[var(--color-text-secondary)]">
            {searchQuery ? 'No rules match your search' : 'No rules defined yet'}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {allRules.map((rule) => {
              // Display all keywords in the rule
              const keywordsDisplay = rule.keywords.join(', ');
              const patternType = getPatternTypeForKeywords(rule.keywords);

              return (
                <div
                  key={rule.id}
                  className="p-3 rounded-lg bg-[var(--color-bg-tertiary)] text-left"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-body font-medium text-[var(--color-text-primary)] truncate flex-1">
                      {keywordsDisplay}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-caption font-medium ${getPatternTypeBadgeClass(
                        patternType
                      )}`}
                    >
                      {patternType}
                    </span>
                    <span className="text-caption text-[var(--color-text-secondary)]">
                      → {rule.category_name}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Loading more indicator */}
          {loadingMore && (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--color-primary)]"></div>
            </div>
          )}
          
          {/* Load more button as fallback */}
          {hasMore && !loadingMore && (
            <div className="mt-4">
              <button
                onClick={() => fetchRules(offset, true)}
                className="w-full btn btn-secondary py-2 text-caption"
              >
                Load More ({totalRules - offset} remaining)
              </button>
            </div>
          )}
          
          {/* End of list indicator */}
          {!hasMore && allRules.length > 0 && (
            <p className="mt-4 text-caption text-[var(--color-text-secondary)] text-center">
              All {totalRules} rules loaded
            </p>
          )}
        </>
      )}

      <p className="mt-4 text-caption text-[var(--color-text-secondary)] text-center">
        Select a category to filter and manage specific rules
      </p>
    </div>
  );
}

function getPatternType(pattern: string): "Keyword" | "Keyword OR" | "Regex" {
  if (pattern.includes("|")) return "Keyword OR";
  if (/[\\^$.*+?()[\]{}]/.test(pattern)) return "Regex";
  return "Keyword";
}

function getPatternTypeForKeywords(keywords: string[]): "Keyword" | "Keyword OR" | "Regex" {
  // Check the first keyword to determine the type
  if (keywords.length === 0) return "Keyword";
  const firstKeyword = keywords[0];
  return getPatternType(firstKeyword);
}

function getPatternTypeBadgeClass(patternType: string): string {
  switch (patternType) {
    case "Keyword":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300";
    case "Keyword OR":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300";
    case "Regex":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300";
  }
}
