"use client";

import { useState, useEffect } from "react";
import { Category, CategoryDetailedStats } from "../../categories/page";
import SparkleIcon from "../ui/SparkleIcon";
import AIBulkModal from "./AIBulkModal";
import { API_URL } from "../../utils/api";

interface CategoryListProps {
  categories: Category[];
  selectedCategoryId: number | null;
  onCategorySelect: (categoryId: number) => void;
  statsWindow: 30 | 60 | 90;
  searchQuery: string;
  onCategoryUpdate: () => void;
}

export default function CategoryList({
  categories,
  selectedCategoryId,
  onCategorySelect,
  statsWindow,
  searchQuery,
  onCategoryUpdate,
}: CategoryListProps) {
  const [categoryStats, setCategoryStats] = useState<Record<number, CategoryDetailedStats>>({});
  const [loading, setLoading] = useState<Set<number>>(new Set());
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newCategoryKeywords, setNewCategoryKeywords] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch stats for all categories
  useEffect(() => {
    categories.forEach((category) => {
      fetchCategoryStats(category.id);
    });
  }, [categories, statsWindow]);

  const fetchCategoryStats = async (categoryId: number) => {
    setLoading((prev) => new Set(prev).add(categoryId));
    try {
      const response = await fetch(
        `${API_URL}/api/categories/${categoryId}/detailed-stats?days=${statsWindow}`
      );
      if (!response.ok) throw new Error("Failed to fetch stats");
      const stats = await response.json();
      setCategoryStats((prev) => ({ ...prev, [categoryId]: stats }));
    } catch (err) {
      console.error(`Failed to fetch stats for category ${categoryId}:`, err);
    } finally {
      setLoading((prev) => {
        const newSet = new Set(prev);
        newSet.delete(categoryId);
        return newSet;
      });
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

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) {
      setError("Category name is required");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const keywords = newCategoryKeywords
        .split(",")
        .map((k) => k.trim())
        .filter((k) => k.length > 0);

      const response = await fetch(`${API_URL}/api/categories/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newCategoryName.trim(),
          keywords,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create category");
      }

      // Success
      setShowAddModal(false);
      setNewCategoryName("");
      setNewCategoryKeywords("");
      onCategoryUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create category");
    } finally {
      setCreating(false);
    }
  };

  // Sort categories: "Other" first, then alphabetically
  const sortedCategories = [...categories].sort((a, b) => {
    if (a.name === "Other") return -1;
    if (b.name === "Other") return 1;
    return a.name.localeCompare(b.name);
  });

  // Filter categories by search query
  const filteredCategories = sortedCategories.filter((category) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      category.name.toLowerCase().includes(query) ||
      category.keywords.some((kw) => kw.toLowerCase().includes(query))
    );
  });

  return (
    <div className="flex flex-col h-full">
      {/* Action Buttons Section */}
      <div className="p-4 space-y-3 border-b border-[var(--color-border-light)]">
        {/* AI Recategorize Button */}
        <button
          onClick={() => setShowAIModal(true)}
          className="w-full btn btn-primary py-2 flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        >
          <SparkleIcon size={18} />
          AI Categorize
        </button>

        {/* Add Category Button */}
        <button
          onClick={() => setShowAddModal(true)}
          className="w-full btn btn-secondary py-2"
        >
          + Add Category
        </button>
      </div>

      {/* Categories List */}
      <div className="flex-1 overflow-y-auto">
        {filteredCategories.length === 0 ? (
          <div className="p-4 text-center text-[var(--color-text-tertiary)]">
            <p className="text-body">No categories found</p>
          </div>
        ) : (
          <div className="p-2 space-y-1">
                {filteredCategories.map((category) => {
                  const stats = categoryStats[category.id];
                  const isSelected = selectedCategoryId === category.id;
                  const isOther = category.name === "Other";
                  const isLoading = loading.has(category.id);

                  return (
                    <button
                      key={category.id}
                      onClick={() => {
                        // Allow toggling: clicking on selected category unselects it
                        if (isSelected) {
                          onCategorySelect(null as any); // Unselect
                        } else {
                          onCategorySelect(category.id);
                        }
                      }}
                      className={`w-full text-left p-3 rounded-lg transition-apple ${
                        isSelected
                          ? "bg-[var(--color-primary)] bg-opacity-10 border border-[var(--color-primary)]"
                          : "hover:bg-[var(--color-bg-tertiary)]"
                      } ${isOther ? "border-l-4 border-l-amber-500" : ""}`}
                    >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-body font-semibold text-[var(--color-text-primary)] truncate">
                        {category.name}
                        {isOther && (
                          <span className="ml-2 text-caption text-amber-600">●</span>
                        )}
                      </h3>
                      {isLoading ? (
                        <div className="mt-1 h-4 w-24 bg-[var(--color-bg-tertiary)] animate-pulse rounded"></div>
                      ) : stats ? (
                        <div className="mt-1 text-caption text-[var(--color-text-secondary)] space-y-0.5">
                          <p>{formatCurrency(stats.total_amount)}</p>
                          <p>
                            {stats.transaction_count} transactions · {stats.rule_count} rules ·{" "}
                            {stats.merchant_count} merchants
                          </p>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Category Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowAddModal(false)}
          />

          {/* Modal */}
          <div className="relative bg-[var(--color-bg-primary)] rounded-xl shadow-lg max-w-md w-full mx-4">
            <div className="border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
              <h2 className="text-heading text-[var(--color-text-primary)]">Add Category</h2>
              <button
                onClick={() => setShowAddModal(false)}
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
              {error && (
                <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-red-800 text-caption">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-body font-medium text-[var(--color-text-primary)] mb-2">
                  Category Name
                </label>
                <input
                  type="text"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="e.g., Food & Dining"
                  className="input w-full"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-body font-medium text-[var(--color-text-primary)] mb-2">
                  Keywords (comma-separated)
                </label>
                <input
                  type="text"
                  value={newCategoryKeywords}
                  onChange={(e) => setNewCategoryKeywords(e.target.value)}
                  placeholder="e.g., RESTAURANT, CAFE, FOOD"
                  className="input w-full"
                />
                <p className="mt-1 text-caption text-[var(--color-text-secondary)]">
                  Enter keywords to match merchant names
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 btn btn-secondary"
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCategory}
                  className="flex-1 btn btn-primary"
                  disabled={creating}
                >
                  {creating ? "Creating..." : "Create Category"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Bulk Modal */}
      <AIBulkModal
        isOpen={showAIModal}
        onClose={() => setShowAIModal(false)}
        level="global"
        days={statsWindow}
        allCategories={categories}
        onSuccess={onCategoryUpdate}
      />
    </div>
  );
}

