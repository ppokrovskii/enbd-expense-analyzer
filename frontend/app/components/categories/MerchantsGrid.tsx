"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Category } from "../../categories/page";
import { API_URL } from "../../utils/api";

interface MerchantGroup {
  merchant: string;
  transaction_count: number;
  total_amount: number;
  category?: string | null;
}

interface MerchantsGridProps {
  selectedCategoryIds: number[];
  selectedCategory: Category | null;
  selectedRuleIndex: number | null;
  startDate: string;
  endDate: string;
  searchQuery: string;
  categories: Category[];
  onCategoryUpdate: () => void;
  selectedMerchants: Set<string>;
  onSelectedMerchantsChange: (merchants: Set<string>) => void;
  refreshTrigger?: number; // Optional refresh trigger
}

export default function MerchantsGrid({
  selectedCategoryIds,
  selectedCategory,
  selectedRuleIndex,
  startDate,
  endDate,
  searchQuery,
  categories,
  onCategoryUpdate,
  selectedMerchants,
  onSelectedMerchantsChange,
  refreshTrigger,
}: MerchantsGridProps) {
  const router = useRouter();
  const [merchants, setMerchants] = useState<MerchantGroup[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMerchants();
    onSelectedMerchantsChange(new Set()); // Clear selection when filters change
  }, [selectedCategoryIds, selectedCategory, selectedRuleIndex, startDate, endDate, refreshTrigger]);

  const fetchMerchants = async () => {
    setLoading(true);
    try {
      let url: string;
      const dateParams = `start_date=${startDate}&end_date=${endDate}`;

      // If single category and specific rule selected
      if (selectedCategory && selectedRuleIndex !== null) {
        url = `${API_URL}/api/categories/${selectedCategory.id}/rules/${selectedRuleIndex}/merchants?${dateParams}`;
      }
      // If single category selected (no specific rule)
      else if (selectedCategory) {
        url = `${API_URL}/api/categories/${selectedCategory.id}/all-rule-merchants?${dateParams}`;
      }
      // Default: show all merchants
      else {
        url = `${API_URL}/api/categories/all-merchants?${dateParams}`;
      }

      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch merchants");
      const data = await response.json();
      setMerchants(data);
    } catch (err) {
      console.error("Failed to fetch merchants:", err);
      setMerchants([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleViewTransactions = (merchant: string) => {
    router.push(
      `/transactions?startDate=${startDate}&endDate=${endDate}&merchant=${encodeURIComponent(
        merchant
      )}`
    );
  };

  const handleSelectMerchant = (merchant: string) => {
    const newSelected = new Set(selectedMerchants);
    if (newSelected.has(merchant)) {
      newSelected.delete(merchant);
    } else {
      newSelected.add(merchant);
    }
    onSelectedMerchantsChange(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedMerchants.size === filteredMerchants.length) {
      onSelectedMerchantsChange(new Set());
    } else {
      onSelectedMerchantsChange(new Set(filteredMerchants.map((m) => m.merchant)));
    }
  };

  // Client-side filter by search query only
  // (Category and rule filtering is already done by the backend endpoint)
  const filteredMerchants = merchants.filter((merchant) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      merchant.merchant.toLowerCase().includes(query) ||
      (merchant.category && merchant.category.toLowerCase().includes(query))
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--color-primary)]"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header with selection info */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-heading text-[var(--color-text-primary)] mb-1">
            Merchants
          </h2>
          <p className="text-caption text-[var(--color-text-secondary)]">
            {filteredMerchants.length} merchants
            {searchQuery && ` (filtered from ${merchants.length})`}
            {selectedMerchants.size > 0 && ` · ${selectedMerchants.size} selected`}
          </p>
        </div>
        {filteredMerchants.length > 0 && (
          <button
            onClick={handleSelectAll}
            className="text-caption text-[var(--color-primary)] hover:underline"
          >
            {selectedMerchants.size === filteredMerchants.length ? "Deselect All" : "Select All"}
          </button>
        )}
      </div>

      {/* Merchants Grid */}
      {filteredMerchants.length === 0 ? (
        <div className="card p-12 text-center">
          <svg
            className="w-20 h-20 mx-auto text-[var(--color-text-tertiary)] mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <h3 className="text-body font-semibold text-[var(--color-text-primary)] mb-2">
            No Merchants Found
          </h3>
          <p className="text-caption text-[var(--color-text-secondary)]">
            {searchQuery
              ? "Try adjusting your search or filters"
              : "No merchants match the selected filters"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {filteredMerchants.map((merchant) => {
            const isSelected = selectedMerchants.has(merchant.merchant);

            return (
              <div
                key={merchant.merchant}
                onClick={() => handleSelectMerchant(merchant.merchant)}
                className={`card p-4 transition-apple cursor-pointer ${
                  isSelected ? "border-2 border-[var(--color-primary)] bg-[var(--color-primary)] bg-opacity-5" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {}} // Handled by parent div onClick
                    onClick={(e) => e.stopPropagation()} // Prevent double toggle
                    className="w-5 h-5 rounded border-[var(--color-border)] cursor-pointer pointer-events-none"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-body font-medium text-[var(--color-text-primary)] truncate">
                        {merchant.merchant}
                      </h4>
                      {merchant.category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-caption font-medium bg-blue-100 text-blue-800">
                          {merchant.category}
                        </span>
                      )}
                      {!merchant.category && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-caption font-medium bg-amber-100 text-amber-800">
                          Uncategorized
                        </span>
                      )}
                    </div>
                    <p className="text-caption text-[var(--color-text-secondary)]">
                      <button
                        onClick={(e) => {
                          e.stopPropagation(); // Prevent card selection
                          handleViewTransactions(merchant.merchant);
                        }}
                        className="text-[var(--color-primary)] hover:underline cursor-pointer"
                      >
                        {merchant.transaction_count} {merchant.transaction_count === 1 ? 'transaction' : 'transactions'}
                      </button>
                      {' · '}
                      {formatCurrency(merchant.total_amount)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

