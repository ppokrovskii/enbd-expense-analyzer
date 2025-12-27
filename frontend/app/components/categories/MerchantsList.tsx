"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface MerchantGroup {
  merchant: string;
  transaction_count: number;
  total_amount: number;
}

interface Category {
  id: number;
  name: string;
  keywords: string[];
}

interface MerchantsListProps {
  categoryId: number;
  ruleIndex: number | null;
  statsWindow: 30 | 60 | 90;
  onCategoryUpdate: () => void;
  isOtherCategory?: boolean;
  searchQuery: string;
  allCategories?: Category[];
}

export default function MerchantsList({
  categoryId,
  ruleIndex,
  statsWindow,
  onCategoryUpdate,
  isOtherCategory = false,
  searchQuery,
  allCategories = [],
}: MerchantsListProps) {
  const router = useRouter();
  const [merchants, setMerchants] = useState<MerchantGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedMerchants, setSelectedMerchants] = useState<Set<string>>(new Set());
  const [showChangeCategoryModal, setShowChangeCategoryModal] = useState(false);
  const [selectedMerchant, setSelectedMerchant] = useState<string | null>(null);
  const [targetCategoryId, setTargetCategoryId] = useState<number | null>(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetchMerchants();
  }, [categoryId, ruleIndex, statsWindow]);

  const fetchMerchants = async () => {
    setLoading(true);
    try {
      let url: string;
      if (isOtherCategory || ruleIndex === null) {
        // Fetch uncategorized merchants
        url = `http://localhost:8000/api/categories/other/merchants?days=${statsWindow}`;
      } else {
        // Fetch merchants for specific rule
        url = `http://localhost:8000/api/categories/${categoryId}/rules/${ruleIndex}/merchants?days=${statsWindow}`;
      }

      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch merchants");
      const data = await response.json();
      setMerchants(data);
    } catch (err) {
      console.error("Failed to fetch merchants:", err);
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

  const handleSelectAll = () => {
    if (selectedMerchants.size === merchants.length) {
      setSelectedMerchants(new Set());
    } else {
      setSelectedMerchants(new Set(merchants.map((m) => m.merchant)));
    }
  };

  const handleSelectMerchant = (merchant: string) => {
    const newSelected = new Set(selectedMerchants);
    if (newSelected.has(merchant)) {
      newSelected.delete(merchant);
    } else {
      newSelected.add(merchant);
    }
    setSelectedMerchants(newSelected);
  };

  const handleChangeCategoryClick = (merchant: string) => {
    setSelectedMerchant(merchant);
    setTargetCategoryId(null);
    setShowChangeCategoryModal(true);
  };

  const handleApplyCategory = async () => {
    if (!selectedMerchant || !targetCategoryId) return;

    setApplying(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/categories/${targetCategoryId}/apply-merchant`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ merchant: selectedMerchant }),
        }
      );

      if (!response.ok) throw new Error("Failed to apply category");

      setShowChangeCategoryModal(false);
      setSelectedMerchant(null);
      setTargetCategoryId(null);
      onCategoryUpdate();
      fetchMerchants();
    } catch (err) {
      console.error("Failed to apply category:", err);
    } finally {
      setApplying(false);
    }
  };

  const handleViewTransactions = (merchant: string) => {
    // Navigate to transactions page with merchant filter
    const endDate = new Date().toISOString().split("T")[0];
    const startDate = new Date(Date.now() - statsWindow * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0];
    router.push(
      `/transactions?startDate=${startDate}&endDate=${endDate}&merchant=${encodeURIComponent(
        merchant
      )}`
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-primary)]"></div>
      </div>
    );
  }

  if (merchants.length === 0) {
    return (
      <div className="card p-8 text-center">
        <svg
          className="w-16 h-16 mx-auto text-[var(--color-text-tertiary)] mb-4"
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
        <p className="text-body text-[var(--color-text-secondary)]">
          No merchants found {searchQuery ? `matching "${searchQuery}"` : `in the last ${statsWindow} days`}
        </p>
      </div>
    );
  }

  // Filter merchants by search query
  const filteredMerchants = searchQuery
    ? merchants.filter((m) => m.merchant.toLowerCase().includes(searchQuery.toLowerCase()))
    : merchants;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
            Merchants ({filteredMerchants.length}{filteredMerchants.length !== merchants.length ? ` of ${merchants.length}` : ""})
          </h3>
          {isOtherCategory && (
            <label className="flex items-center gap-2 text-caption text-[var(--color-text-secondary)] cursor-pointer">
              <input
                type="checkbox"
                checked={selectedMerchants.size === merchants.length}
                onChange={handleSelectAll}
                className="w-4 h-4 rounded border-[var(--color-border)]"
              />
              Select All
            </label>
          )}
        </div>
        {selectedMerchants.size > 0 && isOtherCategory && (
          <button
            onClick={() => setShowChangeCategoryModal(true)}
            className="btn btn-primary text-caption"
          >
            Change Category ({selectedMerchants.size})
          </button>
        )}
      </div>

      <div className="space-y-2">
        {filteredMerchants.map((merchant) => {
          const isSelected = selectedMerchants.has(merchant.merchant);

          return (
            <div
              key={merchant.merchant}
              className={`card p-4 transition-apple ${
                isSelected ? "border-[var(--color-primary)] bg-blue-50 bg-opacity-5" : ""
              }`}
            >
              <div className="flex items-center gap-3">
                {isOtherCategory && (
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleSelectMerchant(merchant.merchant)}
                    className="w-4 h-4 rounded border-[var(--color-border)]"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <h4 className="text-body font-medium text-[var(--color-text-primary)] truncate">
                    {merchant.merchant}
                  </h4>
                  <p className="text-caption text-[var(--color-text-secondary)] mt-1">
                    {merchant.transaction_count} transactions ·{" "}
                    {formatCurrency(merchant.total_amount)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleViewTransactions(merchant.merchant)}
                    className="btn btn-secondary text-caption py-1 px-3"
                  >
                    View
                  </button>
                  {isOtherCategory && (
                    <button
                      onClick={() => handleChangeCategoryClick(merchant.merchant)}
                      className="btn btn-primary text-caption py-1 px-3"
                    >
                      Change Category
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Change Category Modal */}
      {showChangeCategoryModal && selectedMerchant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowChangeCategoryModal(false)}
          />
          <div className="relative bg-[var(--color-bg-primary)] rounded-xl shadow-lg max-w-md w-full mx-4">
            <div className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
              <h2 className="text-heading text-[var(--color-text-primary)]">Change Category</h2>
              <button
                onClick={() => setShowChangeCategoryModal(false)}
                className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <p className="text-body text-[var(--color-text-secondary)] mb-2">
                  Merchant: <span className="font-semibold text-[var(--color-text-primary)]">{selectedMerchant}</span>
                </p>
              </div>

              <div>
                <label className="block text-body font-medium text-[var(--color-text-primary)] mb-2">
                  New Category:
                </label>
                <select
                  value={targetCategoryId || ""}
                  onChange={(e) => setTargetCategoryId(parseInt(e.target.value))}
                  className="input w-full"
                >
                  <option value="">Select a category...</option>
                  {allCategories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowChangeCategoryModal(false)}
                  className="flex-1 btn btn-secondary"
                  disabled={applying}
                >
                  Cancel
                </button>
                <button
                  onClick={handleApplyCategory}
                  className="flex-1 btn btn-primary"
                  disabled={applying || !targetCategoryId}
                >
                  {applying ? "Applying..." : "Apply"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

