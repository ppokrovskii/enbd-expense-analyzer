"use client";

import { useState, useEffect } from "react";

interface SectionFilters {
  start_date?: string;
  end_date?: string;
  group_by?: string;
}

interface FilterPopupProps {
  isOpen: boolean;
  onClose: () => void;
  filters: SectionFilters;
  onSave: (filters: SectionFilters) => void;
  showGroupBy?: boolean;
}

export default function FilterPopup({
  isOpen,
  onClose,
  filters,
  onSave,
  showGroupBy = false,
}: FilterPopupProps) {
  const [localFilters, setLocalFilters] = useState<SectionFilters>(filters);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters, isOpen]);

  if (!isOpen) return null;

  const handleQuickFilter = (filterType: string) => {
    const now = new Date();
    let startYear: number, startMonth: number, startDay: number;
    let endYear: number, endMonth: number, endDay: number;

    switch (filterType) {
      case 'this-month':
        startYear = now.getFullYear();
        startMonth = now.getMonth() + 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        break;
      
      case 'last-month':
        const lastMonth = now.getMonth() === 0 ? 11 : now.getMonth() - 1;
        const lastMonthYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = lastMonthYear;
        startMonth = lastMonth + 1;
        startDay = 1;
        endYear = lastMonthYear;
        endMonth = lastMonth + 1;
        endDay = new Date(lastMonthYear, lastMonth + 1, 0).getDate();
        break;
      
      case 'last-3-months':
        const threeMonthsAgo = (now.getMonth() - 3 + 12) % 12;
        const threeMonthsAgoYear = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
        startYear = threeMonthsAgoYear;
        startMonth = threeMonthsAgo + 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        break;
      
      case 'this-year':
        startYear = now.getFullYear();
        startMonth = 1;
        startDay = 1;
        endYear = now.getFullYear();
        endMonth = 12;
        endDay = 31;
        break;
      
      case 'last-year':
        startYear = now.getFullYear() - 1;
        startMonth = 1;
        startDay = 1;
        endYear = now.getFullYear() - 1;
        endMonth = 12;
        endDay = 31;
        break;
      
      case 'last-7-days': {
        const sevenDaysAgo = new Date(now);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        startYear = sevenDaysAgo.getFullYear();
        startMonth = sevenDaysAgo.getMonth() + 1;
        startDay = sevenDaysAgo.getDate();
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = now.getDate();
        break;
      }
      
      case 'last-30-days': {
        const thirtyDaysAgo = new Date(now);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        startYear = thirtyDaysAgo.getFullYear();
        startMonth = thirtyDaysAgo.getMonth() + 1;
        startDay = thirtyDaysAgo.getDate();
        endYear = now.getFullYear();
        endMonth = now.getMonth() + 1;
        endDay = now.getDate();
        break;
      }
      
      default:
        return;
    }

    setLocalFilters({
      ...localFilters,
      start_date: `${startYear}-${String(startMonth).padStart(2, '0')}-${String(startDay).padStart(2, '0')}`,
      end_date: `${endYear}-${String(endMonth).padStart(2, '0')}-${String(endDay).padStart(2, '0')}`,
    });
  };

  const getQuickFilterLabel = (filterType: string): string => {
    const now = new Date();
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'];
    
    switch (filterType) {
      case 'this-month':
        return monthNames[now.getMonth()];
      case 'last-month':
        return monthNames[(now.getMonth() - 1 + 12) % 12];
      default:
        return filterType;
    }
  };

  const handleSave = () => {
    onSave(localFilters);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-[var(--color-bg-primary)] rounded-xl shadow-xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-heading text-[var(--color-text-primary)]">
            Section Filters
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="space-y-6">
          {/* Quick Filters */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              Quick Filters
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleQuickFilter('this-month')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                {getQuickFilterLabel('this-month')}
              </button>
              <button
                onClick={() => handleQuickFilter('last-month')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                {getQuickFilterLabel('last-month')}
              </button>
              <button
                onClick={() => handleQuickFilter('last-7-days')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                Last 7 Days
              </button>
              <button
                onClick={() => handleQuickFilter('last-30-days')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                Last 30 Days
              </button>
              <button
                onClick={() => handleQuickFilter('last-3-months')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                Last 3 Months
              </button>
              <button
                onClick={() => handleQuickFilter('this-year')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                This Year
              </button>
              <button
                onClick={() => handleQuickFilter('last-year')}
                className="px-3 py-1.5 text-caption rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-primary)] hover:text-white transition-apple"
              >
                Last Year
              </button>
            </div>
          </div>

          {/* Custom Date Range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
                From Date
              </label>
              <input
                type="date"
                value={localFilters.start_date || ''}
                onChange={(e) => setLocalFilters({ ...localFilters, start_date: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
                To Date
              </label>
              <input
                type="date"
                value={localFilters.end_date || ''}
                onChange={(e) => setLocalFilters({ ...localFilters, end_date: e.target.value })}
                className="input"
              />
            </div>
          </div>

          {/* Group By (only for Expense Overview) */}
          {showGroupBy && (
            <div>
              <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
                Group By
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setLocalFilters({ ...localFilters, group_by: 'week' })}
                  className={`flex-1 py-2 px-4 rounded-lg text-body transition-colors ${
                    localFilters.group_by === 'week'
                      ? 'bg-[var(--color-primary)] text-white'
                      : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]'
                  }`}
                >
                  Weekly
                </button>
                <button
                  onClick={() => setLocalFilters({ ...localFilters, group_by: 'month' })}
                  className={`flex-1 py-2 px-4 rounded-lg text-body transition-colors ${
                    localFilters.group_by === 'month' || !localFilters.group_by
                      ? 'bg-[var(--color-primary)] text-white'
                      : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]'
                  }`}
                >
                  Monthly
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Actions */}
        <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-[var(--color-border-light)]">
          <button
            onClick={onClose}
            className="btn btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="btn btn-primary"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  );
}

