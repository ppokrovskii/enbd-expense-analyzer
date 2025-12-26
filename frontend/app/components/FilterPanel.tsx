"use client";

import { useState, useEffect } from "react";
import FilterChip from "./ui/FilterChip";
import FilterModal from "./FilterModal";

interface FilterOptions {
  categories: string[];
  accounts: string[];
  min_date: string | null;
  max_date: string | null;
}

interface FilterValues {
  startDate: string;
  endDate: string;
  categories: string[];
  accounts: string[];
  merchant: string;
}

interface FilterPanelProps {
  onFilterChange: (filters: FilterValues) => void;
  onReset: () => void;
  currentFilters: FilterValues;
}

export default function FilterPanel({ onFilterChange, onReset, currentFilters }: FilterPanelProps) {
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [tempAccounts, setTempAccounts] = useState<string[]>(currentFilters.accounts);

  // Fetch filter options on mount
  useEffect(() => {
    fetch("http://localhost:8000/api/filters/options")
      .then(res => res.json())
      .then(data => setFilterOptions(data))
      .catch(err => console.error("Failed to fetch filter options:", err));
  }, []);

  // Sync tempAccounts when currentFilters changes
  useEffect(() => {
    setTempAccounts(currentFilters.accounts);
  }, [currentFilters.accounts]);

  const handleApplyFilters = () => {
    const newFilters = { ...currentFilters, accounts: tempAccounts };
    onFilterChange(newFilters);
    setIsModalOpen(false);
  };

  const handleRemoveAccount = (account: string) => {
    const newFilters = {
      ...currentFilters,
      accounts: currentFilters.accounts.filter(a => a !== account)
    };
    onFilterChange(newFilters);
  };

  const toggleAccount = (account: string) => {
    setTempAccounts(prev =>
      prev.includes(account)
        ? prev.filter(a => a !== account)
        : [...prev, account]
    );
  };

  const hasAccountFilters = currentFilters.accounts.length > 0;

  return (
    <>
      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Accounts Button */}
        <button
          onClick={() => {
            setTempAccounts(currentFilters.accounts);
            setIsModalOpen(true);
          }}
          className="btn btn-secondary flex items-center gap-2 relative overflow-hidden group"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-primary)]/0 via-[var(--color-primary)]/5 to-[var(--color-primary)]/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          <svg className="w-4 h-4 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
          </svg>
          <span className="relative z-10">Accounts</span>
          {hasAccountFilters && (
            <span className="relative z-10 px-1.5 py-0.5 bg-[var(--color-primary)] text-white text-label rounded-full shadow-lg">
              {currentFilters.accounts.length}
            </span>
          )}
        </button>

        {/* Active Account Chips */}
        {currentFilters.accounts.map((acc) => (
          <FilterChip
            key={acc}
            label={acc}
            onRemove={() => handleRemoveAccount(acc)}
            color="orange"
          />
        ))}
      </div>

      {/* Account Filter Modal */}
      <FilterModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        {!filterOptions ? (
          <div className="py-8 text-center text-[var(--color-text-secondary)]">
            Loading accounts...
          </div>
        ) : (
          <div className="space-y-6">
            {/* Accounts */}
            <div>
              <label className="block text-body font-medium text-[var(--color-text-primary)] mb-3">
                Select Accounts ({tempAccounts.length} selected)
              </label>
              <div className="space-y-1">
                {filterOptions.accounts.map((account) => (
                  <label key={account} className="flex items-center space-x-3 p-3 hover:bg-white/5 rounded-lg cursor-pointer transition-apple">
                    <input
                      type="checkbox"
                      checked={tempAccounts.includes(account)}
                      onChange={() => toggleAccount(account)}
                      className="w-4 h-4 rounded border-[var(--color-border)] bg-[var(--color-bg-primary)] text-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-0"
                    />
                    <span className="text-body text-[var(--color-text-primary)]">{account}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4 border-t border-[var(--color-border)]">
              <button
                onClick={handleApplyFilters}
                className="flex-1 btn btn-primary"
              >
                Apply Filter
              </button>
              <button
                onClick={() => setIsModalOpen(false)}
                className="flex-1 btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </FilterModal>
    </>
  );
}

