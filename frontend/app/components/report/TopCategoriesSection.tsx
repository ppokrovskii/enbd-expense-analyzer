"use client";

import { useState, useEffect } from "react";
import { getApiHeaders, API_URL } from "../../utils/api";
import SkeletonLoader from "../ui/SkeletonLoader";

interface SectionFilters {
  start_date?: string;
  end_date?: string;
  group_by?: string;
}

interface SectionContent {
  takeaway?: string;
  bullets?: string[];
}

interface TopCategoriesSectionProps {
  filters: SectionFilters;
  content: SectionContent;
  onContentChange: (content: SectionContent) => void;
}

interface CategoryBreakdown {
  category: string;
  total: number;
  percentage: number;
  transaction_count: number;
}

export default function TopCategoriesSection({ filters, content, onContentChange }: TopCategoriesSectionProps) {
  const [categories, setCategories] = useState<CategoryBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCategories();
  }, [filters.start_date, filters.end_date]);

  const fetchCategories = async () => {
    if (!filters.start_date || !filters.end_date) return;
    
    setLoading(true);
    try {
      const start = new Date(filters.start_date);
      const end = new Date(filters.end_date);
      const periodDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

      const response = await fetch(
        `${API_URL}/api/insights/generate?period_days=${periodDays}`,
        { headers: getApiHeaders() }
      );

      if (response.ok) {
        const data = await response.json();
        const categoryInsight = data.insights?.find(
          (i: any) => i.type === 'category_analysis'
        );
        
        if (categoryInsight?.data?.categories) {
          const breakdown = categoryInsight.data.categories.map((cat: any) => ({
            category: cat.category,
            total: Math.abs(cat.amount),
            percentage: cat.percentage,
            transaction_count: cat.count || 0
          }));
          setCategories(breakdown.slice(0, 7));
        }
      }
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'AED',
      minimumFractionDigits: 2,
    }).format(Math.abs(amount));
  };

  if (loading) {
    return <SkeletonLoader variant="table" count={5} />;
  }

  if (categories.length === 0) {
    return (
      <div className="text-center py-8 text-[var(--color-text-secondary)]">
        No category data available for this period.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {categories.map((cat, index) => (
        <div key={index} className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-body font-medium text-[var(--color-text-primary)]">
              {cat.category || 'Uncategorized'}
            </span>
            <div className="flex items-center gap-3">
              <span className="text-caption text-[var(--color-text-secondary)]">
                {cat.percentage.toFixed(1)}%
              </span>
              <span className="text-body font-semibold text-[var(--color-text-primary)]">
                {formatCurrency(cat.total)}
              </span>
            </div>
          </div>
          <div className="w-full bg-[var(--color-bg-tertiary)] rounded-full h-2">
            <div
              className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-hover)] h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(cat.percentage, 100)}%` }}
            />
          </div>
          <p className="text-caption text-[var(--color-text-secondary)]">
            {cat.transaction_count} transactions
          </p>
        </div>
      ))}
    </div>
  );
}

