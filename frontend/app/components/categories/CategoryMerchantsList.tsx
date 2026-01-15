"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Modal from "./Modal";
import { Category } from "../../categories/page";
import { API_URL } from "../../utils/api";

interface MerchantGroup {
  merchant: string;
  transaction_count: number;
  total_amount: number;
}

interface CategoryMerchantsListProps {
  categoryId: number;
  statsWindow: 30 | 60 | 90;
  onCategoryUpdate: () => void;
  allCategories: Category[];
  searchQuery: string;
}

export default function CategoryMerchantsList({
  categoryId,
  statsWindow,
  onCategoryUpdate,
  allCategories,
  searchQuery,
}: CategoryMerchantsListProps) {
  const router = useRouter();
  const [merchants, setMerchants] = useState<MerchantGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [showChangeCategoryModal, setShowChangeCategoryModal] = useState(false);
  const [selectedMerchant, setSelectedMerchant] = useState<string | null>(null);
  const [targetCategoryId, setTargetCategoryId] = useState<number | null>(null);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetchMerchants();
  }, [categoryId, statsWindow]);

  const fetchMerchants = async () => {
    setLoading(true);
    try {
      // Fetch all merchants for this category (across all rules)
      const response = await fetch(
        `${API_URL}/api/categories/${categoryId}/all-rule-merchants?days=${statsWindow}`
      );
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

  const handleChangeCategoryClick = (merchant: string) => {
    setSelectedMerchant(merchant);
    setShowChangeCategoryModal(true);
  };

  const handleApplyCategory = async () => {
    if (!selectedMerchant || targetCategoryId === null) return;

    setApplying(true);
    try {
      const response = await fetch(`${API_URL}/api/categories/apply-to-merchant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          merchant: selectedMerchant,
          category_name: allCategories.find(c => c.id === targetCategoryId)?.name,
        }),
      });

      if (!response.ok) throw new Error("Failed to apply category to merchant");

      setShowChangeCategoryModal(false);
      setSelectedMerchant(null);
      setTargetCategoryId(null);
      onCategoryUpdate();
      fetchMerchants(); // Refresh the list
    } catch (err) {
      console.error("Failed to apply category:", err);
    } finally {
      setApplying(false);
    }
  };

  const handleViewTransactions = (merchant: string) => {
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

  // Client-side filter merchants by search query
  const filteredMerchants = merchants.filter((merchant) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return merchant.merchant.toLowerCase().includes(query);
  });

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
          No merchants found in the last {statsWindow} days
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
          {filteredMerchants.length} {filteredMerchants.length === 1 ? "merchant" : "merchants"}
          {searchQuery && ` (filtered from ${merchants.length})`}
        </h3>
      </div>

      <div className="space-y-2">
        {filteredMerchants.map((merchant) => {
          return (
            <div
              key={merchant.merchant}
              className="card p-4 transition-apple"
            >
              <div className="flex items-center gap-3">
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
                  <button
                    onClick={() => handleChangeCategoryClick(merchant.merchant)}
                    className="btn btn-primary text-caption py-1 px-3"
                  >
                    Change Category
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Change Category Modal */}
      {showChangeCategoryModal && selectedMerchant && (
        <Modal
          isOpen={showChangeCategoryModal}
          onClose={() => setShowChangeCategoryModal(false)}
          title={`Change Category for "${selectedMerchant}"`}
        >
          <div className="space-y-4">
            <div>
              <label
                htmlFor="targetCategory"
                className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1"
              >
                Target Category
              </label>
              <select
                id="targetCategory"
                className="input"
                value={targetCategoryId || ""}
                onChange={(e) => setTargetCategoryId(parseInt(e.target.value))}
                disabled={applying}
              >
                <option value="">Select a category</option>
                {allCategories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowChangeCategoryModal(false)}
                className="btn btn-secondary"
                disabled={applying}
              >
                Cancel
              </button>
              <button
                onClick={handleApplyCategory}
                className="btn btn-primary"
                disabled={applying || targetCategoryId === null}
              >
                {applying ? "Applying..." : "Apply Category"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

