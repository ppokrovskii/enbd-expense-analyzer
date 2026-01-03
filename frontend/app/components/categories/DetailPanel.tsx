"use client";

import { useState } from "react";
import { Category } from "../../categories/page";
import RulesList from "./RulesList";
import MerchantsList from "./MerchantsList";
import SparkleIcon from "../ui/SparkleIcon";
import AIBulkModal from "./AIBulkModal";
import AllMerchantsList from "./AllMerchantsList";

interface DetailPanelProps {
  selectedCategoryId: number | null;
  selectedRuleIndex: number | null;
  onRuleSelect: (ruleIndex: number | null) => void;
  statsWindow: 30 | 60 | 90;
  categories: Category[];
  onCategoryUpdate: () => void;
  searchQuery: string;
}

export default function DetailPanel({
  selectedCategoryId,
  selectedRuleIndex,
  onRuleSelect,
  statsWindow,
  categories,
  onCategoryUpdate,
  searchQuery,
}: DetailPanelProps) {
  const [showAIModal, setShowAIModal] = useState(false);

  // If no category selected, show all merchants across all categories
  if (!selectedCategoryId) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-heading text-[var(--color-text-primary)] mb-2">
                All Merchants
              </h2>
              <p className="text-body text-[var(--color-text-secondary)]">
                Showing merchants across all categories
              </p>
            </div>
            <button
              onClick={() => setShowAIModal(true)}
              className="btn btn-primary flex items-center gap-2"
            >
              <SparkleIcon size={16} />
              AI Categorize All
            </button>
          </div>

          {/* Show all merchants from all categories */}
          <AllMerchantsList
            statsWindow={statsWindow}
            onCategoryUpdate={onCategoryUpdate}
            allCategories={categories}
            searchQuery={searchQuery}
          />
        </div>

        {showAIModal && (
          <AIBulkModal
            isOpen={showAIModal}
            onClose={() => setShowAIModal(false)}
            onSuccess={onCategoryUpdate}
            allCategories={categories}
            level="global"
            days={statsWindow}
          />
        )}
      </div>
    );
  }

  const selectedCategory = categories.find((c) => c.id === selectedCategoryId);
  if (!selectedCategory) return null;

  // Always show rules list - rules act as filters, not as navigation
  return (
    <div className="h-full overflow-y-auto">
      <RulesList
        category={selectedCategory}
        onRuleSelect={onRuleSelect}
        selectedRuleIndex={selectedRuleIndex}
        statsWindow={statsWindow}
        onCategoryUpdate={onCategoryUpdate}
        allCategories={categories}
        searchQuery={searchQuery}
      />
      {showAIModal && (
        <AIBulkModal
          isOpen={showAIModal}
          onClose={() => setShowAIModal(false)}
          onSuccess={onCategoryUpdate}
          allCategories={categories}
          level="category"
          categoryId={selectedCategoryId ?? undefined}
          days={statsWindow}
        />
      )}
    </div>
  );
}

