"use client";

import { useState, useEffect } from "react";
import { getApiHeaders, API_URL } from "../../utils/api";
import MetricCard from "../ui/MetricCard";
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

interface SummarySectionProps {
  filters: SectionFilters;
  content: SectionContent;
  onContentChange: (content: SectionContent) => void;
}

interface Stats {
  total_income: number;
  total_expenses: number;
  net: number;
  transaction_count: number;
}

export default function SummarySection({ filters, content, onContentChange }: SummarySectionProps) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [takeaway, setTakeaway] = useState(content.takeaway || "");

  useEffect(() => {
    fetchStats();
  }, [filters.start_date, filters.end_date]);

  useEffect(() => {
    setTakeaway(content.takeaway || "");
  }, [content.takeaway]);

  const fetchStats = async () => {
    if (!filters.start_date || !filters.end_date) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('start_date', filters.start_date);
      params.set('end_date', filters.end_date);

      const response = await fetch(
        `${API_URL}/api/stats/summary?${params.toString()}`,
        { headers: getApiHeaders() }
      );

      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateTakeaway = async () => {
    if (!stats) return;
    
    setGenerating(true);
    try {
      const response = await fetch(`${API_URL}/api/chat/quick`, {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({
          message: `Generate a brief 2-3 sentence summary takeaway for a financial report covering ${filters.start_date} to ${filters.end_date}. Total income: ${stats.total_income} AED, Total expenses: ${stats.total_expenses} AED, Net: ${stats.net} AED. Keep it factual, no advice.`
        })
      });

      if (response.ok) {
        const data = await response.json();
        const newTakeaway = data.response || data.message || "";
        setTakeaway(newTakeaway);
        onContentChange({ ...content, takeaway: newTakeaway });
      }
    } catch (err) {
      // Fallback
      const net = stats.net;
      const status = net >= 0 ? "positive" : "negative";
      const newTakeaway = `During this period, total spending was ${formatCurrency(stats.total_expenses)} against income of ${formatCurrency(stats.total_income)}, resulting in a ${status} balance of ${formatCurrency(Math.abs(net))}.`;
      setTakeaway(newTakeaway);
      onContentChange({ ...content, takeaway: newTakeaway });
    } finally {
      setGenerating(false);
    }
  };

  const handleTakeawayChange = (value: string) => {
    setTakeaway(value);
  };

  const handleTakeawayBlur = () => {
    if (takeaway !== content.takeaway) {
      onContentChange({ ...content, takeaway });
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
    return <SkeletonLoader variant="metric" />;
  }

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MetricCard
            title="Total Spending"
            value={stats.total_expenses}
            format="currency"
            gradient
            gradientType="expense"
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            }
          />
          <MetricCard
            title="Total Income"
            value={stats.total_income}
            format="currency"
            gradient
            gradientType="income"
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
          <MetricCard
            title="Net Balance"
            value={stats.net}
            format="currency"
            gradient
            gradientType={stats.net >= 0 ? "success" : "expense"}
            changeType={stats.net >= 0 ? "increase" : "decrease"}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            }
          />
        </div>
      )}

      {/* Summary Takeaway */}
      <div className="space-y-3">
        <div className="flex items-center justify-between no-print">
          <label className="text-body font-medium text-[var(--color-text-primary)]">
            Summary Takeaway
          </label>
          <button
            onClick={generateTakeaway}
            disabled={generating || !stats}
            className="btn btn-secondary text-caption py-1.5 px-3 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? (
              <>
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
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
          value={takeaway}
          onChange={(e) => handleTakeawayChange(e.target.value)}
          onBlur={handleTakeawayBlur}
          placeholder="Click 'Generate with AI' to create a summary, or write your own takeaway..."
          className="input min-h-[100px] resize-y print:border-none print:bg-transparent"
        />
      </div>
    </div>
  );
}

