'use client';

import { useState, useEffect } from 'react';
import { API_URL } from '@/app/utils/api';

interface ContextModalProps {
  sessionId: string;
  onClose: () => void;
  onContextAdded: () => void;
  currentContext?: any;
}

type DatePreset = {
  label: string;
  months: number | null; // null means "all time"
};

const DATE_PRESETS: DatePreset[] = [
  { label: 'Last Month', months: 1 },
  { label: 'Last 3 Months', months: 3 },
  { label: 'Last 6 Months', months: 6 },
  { label: 'This Year', months: 0 }, // special case
  { label: 'All Time', months: null },
];

export default function ContextModal({
  sessionId,
  onClose,
  onContextAdded,
  currentContext,
}: ContextModalProps) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<string[]>([]);
  const [merchant, setMerchant] = useState('');
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [availableAccounts, setAvailableAccounts] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [estimating, setEstimating] = useState(false);
  const [estimate, setEstimate] = useState<any>(null);
  const [selectedPreset, setSelectedPreset] = useState<string>('Last 3 Months');

  useEffect(() => {
    // Set default date range to last 3 months
    applyDatePreset('Last 3 Months');

    // Load available categories and accounts
    loadFilters();

    // If there's existing context, populate the form
    if (currentContext?.transaction_filters) {
      const filters = currentContext.transaction_filters;
      if (filters.date_range?.from) setStartDate(filters.date_range.from);
      if (filters.date_range?.to) setEndDate(filters.date_range.to);
      if (filters.categories) setCategories(filters.categories);
      if (filters.accounts) setAccounts(filters.accounts);
      if (filters.merchant) setMerchant(filters.merchant);
      setSelectedPreset(''); // Custom dates
    }
  }, [currentContext]);

  useEffect(() => {
    // Auto-estimate when filters change
    const timer = setTimeout(() => {
      if (startDate && endDate) {
        estimateContext();
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [startDate, endDate, categories, accounts, merchant]);

  const loadFilters = async () => {
    try {
      const response = await fetch(`${API_URL}/api/data/filters`, {
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setAvailableCategories(data.categories || []);
        setAvailableAccounts(data.accounts || []);
      }
    } catch (error) {
      console.error('Failed to load filters:', error);
    }
  };

  const applyDatePreset = (presetLabel: string) => {
    const preset = DATE_PRESETS.find(p => p.label === presetLabel);
    if (!preset) return;

    const end = new Date();
    let start = new Date();

    if (preset.months === null) {
      // All time - set to a very old date
      start = new Date('2020-01-01');
    } else if (preset.months === 0) {
      // This year
      start = new Date(end.getFullYear(), 0, 1);
    } else {
      start.setMonth(start.getMonth() - preset.months);
    }

    setEndDate(end.toISOString().split('T')[0]);
    setStartDate(start.toISOString().split('T')[0]);
    setSelectedPreset(presetLabel);
  };

  const estimateContext = async () => {
    if (!startDate || !endDate) return;

    setEstimating(true);
    try {
      const response = await fetch(
        `${API_URL}/api/chat/sessions/context/estimate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-Id': 'default_user',
          },
          body: JSON.stringify({
            date_range: {
              from: startDate,
              to: endDate,
            },
            categories: categories.length > 0 ? categories : undefined,
            accounts: accounts.length > 0 ? accounts : undefined,
            merchant: merchant || undefined,
          }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setEstimate(data);
      }
    } catch (error) {
      console.error('Failed to estimate context:', error);
    } finally {
      setEstimating(false);
    }
  };

  const handleAddContext = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_URL}/api/chat/sessions/${sessionId}/context`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-User-Id': 'default_user',
          },
          body: JSON.stringify({
            date_range: {
              from: startDate,
              to: endDate,
            },
            categories: categories.length > 0 ? categories : undefined,
            accounts: accounts.length > 0 ? accounts : undefined,
            merchant: merchant || undefined,
          }),
        }
      );

      if (response.ok) {
        onContextAdded();
      }
    } catch (error) {
      console.error('Failed to add context:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (category: string) => {
    setCategories((prev) =>
      prev.includes(category)
        ? prev.filter((c) => c !== category)
        : [...prev, category]
    );
  };

  const toggleAccount = (account: string) => {
    setAccounts((prev) =>
      prev.includes(account)
        ? prev.filter((a) => a !== account)
        : [...prev, account]
    );
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-150">
      <div className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-1">
                Update Context
              </h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                Select transaction data for the AI to analyze
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] p-2 rounded-lg transition-all"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Quick Date Presets */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-3">
              Quick Select
            </label>
            <div className="flex flex-wrap gap-2">
              {DATE_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => applyDatePreset(preset.label)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    selectedPreset === preset.label
                      ? 'bg-[var(--color-primary)] text-white'
                      : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-3">
              Date Range
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[var(--color-text-secondary)] mb-2">From</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value);
                    setSelectedPreset(''); // Custom
                  }}
                  className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm px-3 py-2 rounded-lg focus:outline-none focus:border-[var(--color-primary)] transition-all"
                />
              </div>
              <div>
                <label className="block text-xs text-[var(--color-text-secondary)] mb-2">To</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value);
                    setSelectedPreset(''); // Custom
                  }}
                  className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm px-3 py-2 rounded-lg focus:outline-none focus:border-[var(--color-primary)] transition-all"
                />
              </div>
            </div>
          </div>

          {/* Categories */}
          {availableCategories.length > 0 && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-3">
                Categories <span className="text-[var(--color-text-tertiary)] font-normal text-xs">(optional)</span>
              </label>
              <div className="max-h-40 overflow-y-auto bg-[var(--color-bg-secondary)] border border-[var(--color-border)] rounded-lg p-3">
                <div className="space-y-2">
                  {availableCategories.map((category) => (
                    <label
                      key={category}
                      className="flex items-center gap-2 cursor-pointer hover:bg-[var(--color-bg-tertiary)] px-2 py-1.5 rounded transition-all"
                    >
                      <input
                        type="checkbox"
                        checked={categories.includes(category)}
                        onChange={() => toggleCategory(category)}
                        className="w-4 h-4 rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)] focus:ring-offset-0"
                      />
                      <span className="text-sm text-[var(--color-text-primary)]">{category}</span>
                    </label>
                  ))}
                </div>
              </div>
              {categories.length === 0 && (
                <p className="text-xs text-[var(--color-text-tertiary)] mt-2">
                  All categories will be included
                </p>
              )}
              {categories.length > 0 && (
                <p className="text-xs text-[var(--color-text-secondary)] mt-2">
                  {categories.length} selected
                </p>
              )}
            </div>
          )}

          {/* Accounts */}
          {availableAccounts.length > 0 && (
            <div className="mb-6">
              <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-3">
                Accounts <span className="text-[var(--color-text-tertiary)] font-normal text-xs">(optional)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {availableAccounts.map((account) => (
                  <button
                    key={account}
                    onClick={() => toggleAccount(account)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                      accounts.includes(account)
                        ? 'bg-[var(--color-primary)] text-white'
                        : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)] hover:text-[var(--color-text-primary)] border border-[var(--color-border)]'
                    }`}
                  >
                    {account}
                  </button>
                ))}
              </div>
              {accounts.length === 0 && (
                <p className="text-xs text-[var(--color-text-tertiary)] mt-2">
                  All accounts will be included
                </p>
              )}
            </div>
          )}

          {/* Merchant Search */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-3">
              Merchant <span className="text-[var(--color-text-tertiary)] font-normal text-xs">(optional)</span>
            </label>
            <input
              type="text"
              value={merchant}
              onChange={(e) => setMerchant(e.target.value)}
              placeholder="Search for a merchant..."
              className="w-full bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] text-sm px-3 py-2 rounded-lg focus:outline-none focus:border-[var(--color-primary)] transition-all"
            />
          </div>

          {/* Context Preview */}
          {estimate && (
            <div className="bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] rounded-lg p-4 mb-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-[var(--color-text-primary)]">
                  Context Preview
                </span>
                {estimating && (
                  <span className="text-xs text-[var(--color-text-tertiary)]">Calculating...</span>
                )}
              </div>
              <div className="flex items-center justify-center">
                <div className="text-center">
                  <div className={`text-3xl font-semibold tracking-tight ${
                    estimate.actual_transactions === 0 
                      ? 'text-red-400' 
                      : estimate.actual_transactions < 100 
                      ? 'text-yellow-400' 
                      : 'text-green-400'
                  }`}>
                    {estimate.actual_transactions}
                  </div>
                  <div className="text-xs text-[var(--color-text-secondary)] mt-1">
                    Transaction{estimate.actual_transactions !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>
              {estimate.limited && (
                <div className="mt-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-3 py-2 text-xs text-yellow-200 flex items-start">
                  <svg className="w-4 h-4 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  Limited to 1,000 most recent transactions
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleAddContext}
              disabled={loading || !startDate || !endDate || (estimate && estimate.actual_transactions === 0)}
              className="px-5 py-2.5 rounded-lg text-sm font-medium bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              {loading ? 'Updating...' : 'Update'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

