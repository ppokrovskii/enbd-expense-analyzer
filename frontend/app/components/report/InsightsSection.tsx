"use client";

import { useState, useEffect } from "react";
import { getApiHeaders, API_URL } from "../../utils/api";

interface SectionFilters {
  start_date?: string;
  end_date?: string;
  group_by?: string;
}

interface SectionContent {
  takeaway?: string;
  bullets?: string[];
}

interface InsightsSectionProps {
  filters: SectionFilters;
  content: SectionContent;
  onContentChange: (content: SectionContent) => void;
}

export default function InsightsSection({ filters, content, onContentChange }: InsightsSectionProps) {
  const [insights, setInsights] = useState<string[]>(content.bullets || []);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    setInsights(content.bullets || []);
  }, [content.bullets]);

  const generateInsights = async () => {
    setGenerating(true);
    try {
      const start = new Date(filters.start_date || '');
      const end = new Date(filters.end_date || '');
      const periodDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

      const response = await fetch(
        `${API_URL}/api/insights/generate?period_days=${periodDays}`,
        { headers: getApiHeaders() }
      );

      if (response.ok) {
        const data = await response.json();
        const insightItems: string[] = [];
        
        if (data.insights && data.insights.length > 0) {
          data.insights.forEach((i: any) => {
            if (i.description) insightItems.push(i.description);
          });
        }
        
        // Fallback if no insights
        if (insightItems.length === 0) {
          insightItems.push("No significant insights detected for this period.");
        }
        
        const finalInsights = insightItems.slice(0, 5);
        setInsights(finalInsights);
        onContentChange({ ...content, bullets: finalInsights });
      }
    } catch (err) {
      const fallback = [
        "Review your spending patterns to identify areas for optimization.",
        "Track your recurring expenses to ensure they're still necessary.",
        "Compare this period with previous periods to spot trends."
      ];
      setInsights(fallback);
      onContentChange({ ...content, bullets: fallback });
    } finally {
      setGenerating(false);
    }
  };

  const updateInsight = (index: number, value: string) => {
    const newInsights = [...insights];
    newInsights[index] = value;
    setInsights(newInsights);
  };

  const saveInsights = () => {
    onContentChange({ ...content, bullets: insights });
  };

  if (insights.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-body text-[var(--color-text-secondary)] mb-4">
          Generate AI-powered insights about your financial data.
        </p>
        <button
          onClick={generateInsights}
          disabled={generating}
          className="btn btn-primary flex items-center gap-2 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? (
            <>
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Generating...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Generate Insights
            </>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between no-print">
        <p className="text-caption text-[var(--color-text-secondary)]">
          AI-generated insights about your financial data
        </p>
        <button
          onClick={generateInsights}
          disabled={generating}
          className="btn btn-secondary text-caption py-1.5 px-3 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? (
            <>
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Regenerating...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Regenerate
            </>
          )}
        </button>
      </div>
      
      <ul className="space-y-3">
        {insights.map((insight, index) => (
          <li key={index} className="flex items-start gap-3">
            <div className="flex-shrink-0 p-1.5 rounded-lg bg-[var(--color-primary)]/10 print:bg-gray-200">
              <svg className="w-4 h-4 text-[var(--color-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <input
              type="text"
              value={insight}
              onChange={(e) => updateInsight(index, e.target.value)}
              onBlur={saveInsights}
              className="flex-1 bg-transparent border-b border-transparent hover:border-[var(--color-border)] focus:border-[var(--color-primary)] focus:outline-none py-1 text-body text-[var(--color-text-primary)] print:border-none"
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

