"use client";

import { Category } from "../../categories/page";

interface RulesFilterProps {
  selectedCategory: Category | null;
  selectedRuleIndex: number | null;
  onRuleSelect: (ruleIndex: number | null) => void;
  onCategoryUpdate: () => void;
  selectedCategoryIds: number[];
  categories: Category[];
  searchQuery: string;
}

export default function RulesFilter({
  selectedCategory,
  selectedRuleIndex,
  onRuleSelect,
  onCategoryUpdate,
  selectedCategoryIds,
  categories,
  searchQuery,
}: RulesFilterProps) {
  // Determine which categories to show rules from
  const categoriesToShow = selectedCategoryIds.length === 0
    ? categories // Show all categories if none selected
    : categories.filter(c => selectedCategoryIds.includes(c.id));

  // Filter rules by search query
  const filterRulesBySearch = (rules: string[]) => {
    if (!searchQuery) return rules;
    const query = searchQuery.toLowerCase();
    return rules.filter(rule => rule.toLowerCase().includes(query));
  };

  // If single category selected, show its rules as filters
  if (selectedCategory) {
    const allRules = selectedCategory.keywords || [];
    const rules = filterRulesBySearch(allRules);

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
            {searchQuery && rules.length < allRules.length && (
              <span className="ml-2 text-caption text-[var(--color-text-secondary)]">
                ({rules.length} of {allRules.length})
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

  // Multiple or no categories selected - show all rules from those categories
  const allCategoriesToShow = categoriesToShow.map(cat => ({
    ...cat,
    filteredKeywords: filterRulesBySearch(cat.keywords || [])
  }));
  
  const totalRules = allCategoriesToShow.reduce((sum, cat) => sum + cat.filteredKeywords.length, 0);
  const totalAllRules = categoriesToShow.reduce((sum, cat) => sum + (cat.keywords?.length || 0), 0);

  return (
    <div className="p-4">
      <div className="mb-4">
        <h3 className="text-body font-semibold text-[var(--color-text-primary)] mb-1">
          Rules
          {searchQuery && totalRules < totalAllRules && (
            <span className="ml-2 text-caption text-[var(--color-text-secondary)]">
              ({totalRules} of {totalAllRules})
            </span>
          )}
        </h3>
        <p className="text-caption text-[var(--color-text-secondary)]">
          {selectedCategoryIds.length === 0
            ? `${totalRules} rules from all categories`
            : `${totalRules} rules from ${selectedCategoryIds.length} ${selectedCategoryIds.length === 1 ? 'category' : 'categories'}`}
        </p>
      </div>

      {totalRules === 0 ? (
        <div className="card p-6 text-center">
          <p className="text-caption text-[var(--color-text-secondary)]">
            {searchQuery ? 'No rules match your search' : 'No rules in selected categories'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {allCategoriesToShow.map((category) => {
            const rules = category.filteredKeywords;
            if (rules.length === 0) return null;

            return (
              <div key={category.id}>
                <h4 className="text-caption font-semibold text-[var(--color-text-primary)] mb-2">
                  {category.name}
                </h4>
                <div className="space-y-2">
                  {rules.map((rule, index) => {
                    const patternType = getPatternType(rule);

                    return (
                      <div
                        key={`${category.id}-${index}`}
                        className="p-3 rounded-lg bg-[var(--color-bg-tertiary)] text-left"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-body font-medium text-[var(--color-text-primary)] truncate flex-1">
                            {rule}
                          </span>
                        </div>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-caption font-medium ${getPatternTypeBadgeClass(
                            patternType
                          )}`}
                        >
                          {patternType}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p className="mt-4 text-caption text-[var(--color-text-secondary)] text-center">
        Select a single category to filter by specific rules
      </p>
    </div>
  );
}

function getPatternType(pattern: string): "Keyword" | "Keyword OR" | "Regex" {
  if (pattern.includes("|")) return "Keyword OR";
  if (/[\\^$.*+?()[\]{}]/.test(pattern)) return "Regex";
  return "Keyword";
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

