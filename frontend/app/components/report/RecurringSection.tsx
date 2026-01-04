"use client";

import { useState } from "react";
import { getApiHeaders } from "../../utils/api";

interface SectionFilters {
  start_date?: string;
  end_date?: string;
  group_by?: string;
}

interface SectionContent {
  takeaway?: string;
  bullets?: string[];
}

interface RecurringSectionProps {
  filters: SectionFilters;
  content: SectionContent;
  onContentChange: (content: SectionContent) => void;
}

interface RecurringTransaction {
  id: string;
  pattern_name: string;
  merchant: string;
  estimated_amount: number;
  frequency: string;
  occurrences: number;
  last_seen_date: string;
  annualized_cost: number;
}

export default function RecurringSection({ filters, content, onContentChange }: RecurringSectionProps) {
  const [recurring, setRecurring] = useState<RecurringTransaction[]>([]);
  const [detected, setDetected] = useState(false);
  const [detecting, setDetecting] = useState(false);

  const detectRecurring = async () => {
    setDetecting(true);
    try {
      const response = await fetch('http://localhost:8000/api/recurring/detect', {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({
          start_date: filters.start_date,
          end_date: filters.end_date
        })
      });

      if (response.ok) {
        const data = await response.json();
        const patterns = data.recurring_groups || data.patterns || [];
        
        const transformed: RecurringTransaction[] = patterns.map((p: any) => {
          let annualized = p.estimated_amount;
          switch (p.frequency?.toLowerCase()) {
            case 'weekly': annualized *= 52; break;
            case 'monthly': annualized *= 12; break;
            case 'quarterly': annualized *= 4; break;
            case 'yearly': break;
            default: annualized *= 12;
          }
          return {
            id: p.id || p.pattern_name,
            pattern_name: p.pattern_name || p.merchant,
            merchant: p.merchant,
            estimated_amount: p.estimated_amount,
            frequency: p.frequency || 'monthly',
            occurrences: p.occurrences || 0,
            last_seen_date: p.last_seen_date,
            annualized_cost: annualized
          };
        });
        
        setRecurring(transformed);
        setDetected(true);
      }
    } catch (err) {
      console.error('Failed to detect recurring:', err);
    } finally {
      setDetecting(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'AED',
      minimumFractionDigits: 2,
    }).format(Math.abs(amount));
  };

  const formatFrequency = (freq: string) => {
    return freq.charAt(0).toUpperCase() + freq.slice(1).toLowerCase();
  };

  const totalMonthly = recurring
    .filter(r => r.frequency.toLowerCase() === 'monthly')
    .reduce((sum, r) => sum + r.estimated_amount, 0);
  
  const totalAnnualized = recurring.reduce((sum, r) => sum + r.annualized_cost, 0);

  if (!detected) {
    return (
      <div className="text-center py-8">
        <p className="text-body text-[var(--color-text-secondary)] mb-4">
          Detect recurring transactions to see your subscriptions and regular expenses.
        </p>
        <button
          onClick={detectRecurring}
          disabled={detecting}
          className="btn btn-primary flex items-center gap-2 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {detecting ? (
            <>
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Detecting...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Detect Recurring Transactions
            </>
          )}
        </button>
      </div>
    );
  }

  if (recurring.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-body text-[var(--color-text-secondary)]">
          No recurring transactions detected for this period.
        </p>
        <button
          onClick={detectRecurring}
          disabled={detecting}
          className="mt-3 text-caption text-[var(--color-primary)] hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 p-4 bg-[var(--color-bg-secondary)] rounded-lg">
        <div>
          <p className="text-caption text-[var(--color-text-secondary)]">Monthly Total</p>
          <p className="text-heading text-[var(--color-text-primary)]">{formatCurrency(totalMonthly)}</p>
        </div>
        <div>
          <p className="text-caption text-[var(--color-text-secondary)]">Annualized Total</p>
          <p className="text-heading text-[var(--color-text-primary)]">{formatCurrency(totalAnnualized)}</p>
        </div>
      </div>
      
      {/* List */}
      <div className="space-y-3">
        {recurring.map((item, index) => (
          <div
            key={item.id || index}
            className="flex items-center justify-between py-3 border-b border-[var(--color-border-light)] last:border-b-0"
          >
            <div className="flex-1">
              <p className="text-body font-medium text-[var(--color-text-primary)]">
                {item.pattern_name || item.merchant}
              </p>
              <p className="text-caption text-[var(--color-text-secondary)]">
                {formatFrequency(item.frequency)} • {item.occurrences} occurrences
              </p>
            </div>
            <div className="text-right">
              <p className="text-body font-semibold text-[var(--color-text-primary)]">
                {formatCurrency(item.estimated_amount)}/{item.frequency.toLowerCase() === 'monthly' ? 'mo' : item.frequency.slice(0, 2)}
              </p>
              <p className="text-caption text-[var(--color-text-secondary)]">
                {formatCurrency(item.annualized_cost)}/year
              </p>
            </div>
          </div>
        ))}
      </div>
      
      {/* Re-detect button */}
      <div className="pt-4 border-t border-[var(--color-border-light)] no-print">
        <button
          onClick={detectRecurring}
          disabled={detecting}
          className="text-caption text-[var(--color-primary)] hover:underline disabled:opacity-50"
        >
          {detecting ? "Detecting..." : "Re-detect recurring transactions"}
        </button>
      </div>
    </div>
  );
}

