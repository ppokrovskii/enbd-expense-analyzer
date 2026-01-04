"use client";

import { useState, useEffect } from "react";
import { getApiHeaders } from "../utils/api";

interface CategoryTotal {
  category: string;
  total: number;
  isIncome: boolean;
}

interface CategoryFilterGridProps {
  startDate: string;
  endDate: string;
  selectedCategoryIds: number[];
  onCategorySelect: (categoryIds: number[]) => void;
  categories: Array<{ id: number; name: string; color?: string }>;
}

const INCOME_CATEGORIES = ["Salary", "Incoming Transfer"];

export default function CategoryFilterGrid({
  startDate,
  endDate,
  selectedCategoryIds,
  onCategorySelect,
  categories,
}: CategoryFilterGridProps) {
  const [categoryTotals, setCategoryTotals] = useState<CategoryTotal[]>([]);
  const [categoryColors, setCategoryColors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  // Fetch category colors
  useEffect(() => {
    const colorMap: Record<string, string> = {};
    categories.forEach((cat) => {
      if (cat.color) {
        colorMap[cat.name] = cat.color;
      }
    });
    setCategoryColors(colorMap);
  }, [categories]);

  // Fetch category totals based on date range
  useEffect(() => {
    const fetchCategoryTotals = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);

        const response = await fetch(
          `http://localhost:8000/api/chart/weekly${params.toString() ? `?${params.toString()}` : ""}`,
          { headers: getApiHeaders() }
        );

        if (!response.ok) {
          throw new Error("Failed to fetch category totals");
        }

        const result = await response.json();
        
        // Calculate totals per category
        const totalsMap: Record<string, number> = {};
        result.data?.forEach((item: { category: string; total: number }) => {
          totalsMap[item.category] = (totalsMap[item.category] || 0) + Number(item.total);
        });

        // Convert to array with income flag
        const totals: CategoryTotal[] = categories.map((cat) => ({
          category: cat.name,
          total: totalsMap[cat.name] || 0,
          isIncome: INCOME_CATEGORIES.includes(cat.name),
        }));

        // Sort by total descending
        totals.sort((a, b) => b.total - a.total);
        setCategoryTotals(totals);
      } catch (error) {
        console.error("Failed to fetch category totals:", error);
        // Set empty totals on error
        setCategoryTotals(
          categories.map((cat) => ({
            category: cat.name,
            total: 0,
            isIncome: INCOME_CATEGORIES.includes(cat.name),
          }))
        );
      } finally {
        setLoading(false);
      }
    };

    fetchCategoryTotals();
  }, [startDate, endDate, categories]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getCategoryColor = (categoryName: string, isIncome: boolean): string => {
    if (isIncome) return "#34C759"; // Green for income

    // Use color from categories if available
    if (categoryColors[categoryName]) {
      return categoryColors[categoryName];
    }

    // Fallback color map
    const colorMap: Record<string, string> = {
      "Other": "#64748B",
      "Transfer Between My Accounts": "#64748B",
      "Outgoing Transfer": "#94A3B8",
      "Incoming Transfer": "#34C759",
    };

    return colorMap[categoryName] || "#94A3B8";
  };

  const handleCategoryToggle = (categoryId: number) => {
    if (selectedCategoryIds.includes(categoryId)) {
      onCategorySelect(selectedCategoryIds.filter((id) => id !== categoryId));
    } else {
      onCategorySelect([...selectedCategoryIds, categoryId]);
    }
  };

  const handleCategoryExclude = (categoryId: number) => {
    // Exclude acts as toggle - if already selected, remove it
    if (selectedCategoryIds.includes(categoryId)) {
      onCategorySelect(selectedCategoryIds.filter((id) => id !== categoryId));
    }
  };

  const handleClearSelection = () => {
    onCategorySelect([]);
  };

  const getCategoryId = (categoryName: string): number | undefined => {
    const cat = categories.find((c) => c.name === categoryName);
    return cat?.id;
  };

  const noneSelected = selectedCategoryIds.length === 0;

  if (loading) {
    return (
      <div className="animate-pulse space-y-2">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-10 bg-[var(--color-bg-tertiary)] rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
          All Categories
        </h3>
        <button
          onClick={handleClearSelection}
          disabled={noneSelected}
          className="text-label text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-apple"
        >
          Clear Selection
        </button>
      </div>

      {/* Category list with 2 columns - scrollable with max height */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 max-h-[300px] overflow-y-auto">
        {categoryTotals.map(({ category, total, isIncome }) => {
          const categoryId = getCategoryId(category);
          if (!categoryId) return null;

          const color = getCategoryColor(category, isIncome);
          const isSelected = selectedCategoryIds.includes(categoryId);
          const sign = isIncome ? "+" : "-";

          return (
            <div
              key={category}
              className={`
                w-full flex items-center justify-between p-3 rounded-lg
                transition-all duration-apple
                ${!isSelected && !noneSelected ? "opacity-40 hover:opacity-100" : ""}
                hover:bg-white/5
                group
              `}
            >
              <button
                onClick={() => handleCategoryToggle(categoryId)}
                className="flex items-center gap-3 min-w-0 flex-1 text-left"
              >
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0 ring-2 ring-offset-2 ring-offset-[var(--color-bg-primary)]"
                  style={{
                    backgroundColor: color,
                    ["--tw-ring-color" as string]:
                      isSelected || noneSelected ? `${color}40` : "transparent",
                  } as React.CSSProperties}
                />
                <p className="text-body text-[var(--color-text-primary)] truncate">
                  {category}
                </p>
              </button>
              <div className="flex items-center gap-2">
                <p
                  className={`text-body font-semibold tabular-nums ${
                    isIncome
                      ? "text-[var(--color-success)]"
                      : "text-[var(--color-text-secondary)]"
                  }`}
                >
                  {sign} {formatCurrency(Math.abs(total))}
                </p>
                {/* X button for excluding categories */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCategoryExclude(categoryId);
                  }}
                  className={`
                    ml-2 p-1 rounded transition-all
                    ${isSelected
                      ? "bg-gray-200 dark:bg-gray-700"
                      : "hover:bg-gray-200 dark:hover:bg-gray-700"
                    }
                  `}
                  title={isSelected ? "Remove from selection" : "Click category name to select"}
                >
                  <svg
                    className={`w-4 h-4 ${
                      isSelected
                        ? "text-gray-600 dark:text-gray-400"
                        : "text-gray-500 dark:text-gray-300"
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

