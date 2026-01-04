"use client";

import { useMemo, useCallback, useState } from "react";
import SpendingChart from "../SpendingChart";
import { usePerson } from "../../hooks/usePerson";

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
  const [isGenerating, setIsGenerating] = useState(false);
  const { activePerson } = usePerson();

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

  const handleGenerateTakeaway = async () => {
    setIsGenerating(true);
    try {
      // Calculate period days from filters
      let periodDays = 30;
      if (filters.start_date && filters.end_date) {
        const start = new Date(filters.start_date);
        const end = new Date(filters.end_date);
        periodDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
      }

      const params = new URLSearchParams({
        period_days: periodDays.toString(),
      });
      if (activePerson?.id) {
        params.append('person_id', activePerson.id.toString());
      }

      const response = await fetch(`/api/insights/generate?${params}`, {
        headers: { "X-User-Id": "default_user" },
      });

      if (response.ok) {
        const data = await response.json();
        // Extract a summary takeaway from insights
        const takeaway = data.insights?.length > 0 
          ? `Key findings: ${data.insights.slice(0, 3).map((i: { title: string }) => i.title).join('. ')}.`
          : "No significant spending patterns detected for this period.";
        
        onContentChange({ ...content, takeaway });
      }
    } catch (error) {
      console.error("Failed to generate takeaway:", error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Chart */}
      <SpendingChart
        filters={chartFilters}
        onGroupByChange={handleGroupByChange}
        filterMode="none"
        filteredCategories={emptyCategories}
        allAvailableCategories={emptyCategories}
      />

      {/* Summary Takeaway */}
      <div className="border-t border-[var(--color-border)] pt-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-body font-medium text-[var(--color-text-primary)]">Summary Takeaway</h4>
          <button
            onClick={handleGenerateTakeaway}
            disabled={isGenerating}
            className="btn btn-secondary text-sm flex items-center gap-2"
          >
            {isGenerating ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Generate with AI
              </>
            )}
          </button>
        </div>
        <textarea
          value={content.takeaway || ''}
          onChange={(e) => onContentChange({ ...content, takeaway: e.target.value })}
          placeholder="Add a summary of key spending patterns for this period..."
          className="input w-full h-24 resize-none"
        />
      </div>
    </div>
  );
}

