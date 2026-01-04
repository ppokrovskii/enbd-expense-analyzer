"use client";

import { useMemo, useCallback } from "react";
import SpendingChart from "../SpendingChart";

interface SectionFilters {
  start_date?: string;
  end_date?: string;
  group_by?: string;
}

interface SectionContent {
  takeaway?: string;
  bullets?: string[];
}

interface ExpenseOverviewSectionProps {
  filters: SectionFilters;
  content: SectionContent;
  onContentChange: (content: SectionContent) => void;
}

export default function ExpenseOverviewSection({ filters, content, onContentChange }: ExpenseOverviewSectionProps) {
  const chartFilters = useMemo(() => ({
    startDate: filters.start_date || '',
    endDate: filters.end_date || '',
    categories: [] as string[],
    accounts: [] as string[],
    merchant: '',
    groupBy: (filters.group_by || 'month') as 'week' | 'month',
  }), [filters.start_date, filters.end_date, filters.group_by]);

  const emptyCategories = useMemo(() => [] as string[], []);

  // No-op for group by change since it's controlled by filters
  const handleGroupByChange = useCallback((value: 'week' | 'month') => {
    // Group by is controlled by section filters, not inline
  }, []);

  return (
    <SpendingChart
      filters={chartFilters}
      onGroupByChange={handleGroupByChange}
      filterMode="none"
      filteredCategories={emptyCategories}
      allAvailableCategories={emptyCategories}
    />
  );
}

