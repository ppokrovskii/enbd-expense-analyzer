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

interface TrendsSectionProps {
  filters: SectionFilters;
  content: SectionContent;
  onContentChange: (content: SectionContent) => void;
}

export default function TrendsSection({ filters, content, onContentChange }: TrendsSectionProps) {
  const [trends, setTrends] = useState<string[]>(content.bullets || []);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    setTrends(content.bullets || []);
  }, [content.bullets]);

  const generateTrends = async () => {
    setGenerating(true);
    try {
      const start = new Date(filters.start_date || '');
      const end = new Date(filters.end_date || '');
      const periodDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

      const response = await fetch(
        `${API_URL}/api/insights/spending-trends?period_days=${periodDays}`,
        { headers: getApiHeaders() }
      );

      if (response.ok) {
        const data = await response.json();
        const trendItems: string[] = [];
        
        if (data.trends && data.trends.length > 0) {
          data.trends.forEach((t: any) => {
            if (t.description) trendItems.push(t.description);
          });
        }
        
        // Fallback if no trends
        if (trendItems.length === 0) {
          trendItems.push("No significant trends detected for this period.");
        }
        
        const finalTrends = trendItems.slice(0, 5);
        setTrends(finalTrends);
        onContentChange({ ...content, bullets: finalTrends });
      }
    } catch (err) {
      const fallback = ["Unable to analyze trends. Please try again."];
      setTrends(fallback);
      onContentChange({ ...content, bullets: fallback });
    } finally {
      setGenerating(false);
    }
  };

  const updateTrend = (index: number, value: string) => {
    const newTrends = [...trends];
    newTrends[index] = value;
    setTrends(newTrends);
  };

  const saveTrends = () => {
    onContentChange({ ...content, bullets: trends });
  };

  if (trends.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-body text-[var(--color-text-secondary)] mb-4">
          Generate AI analysis of spending patterns and unusual transactions.
        </p>
        <button
          onClick={generateTrends}
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              Generate Trends
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
          AI-generated analysis of spending patterns and unusual transactions
        </p>
        <button
          onClick={generateTrends}
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
        {trends.map((trend, index) => (
          <li key={index} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] flex items-center justify-center text-caption font-medium print:bg-gray-200">
              {index + 1}
            </span>
            <input
              type="text"
              value={trend}
              onChange={(e) => updateTrend(index, e.target.value)}
              onBlur={saveTrends}
              className="flex-1 bg-transparent border-b border-transparent hover:border-[var(--color-border)] focus:border-[var(--color-primary)] focus:outline-none py-1 text-body text-[var(--color-text-primary)] print:border-none"
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

