"use client";

import { useState } from "react";
import { Category } from "../../categories/page";
import SparkleIcon from "../ui/SparkleIcon";
import MerchantsList from "./MerchantsList";
import CategoryMerchantsList from "./CategoryMerchantsList";
import Modal from "./Modal";
import AIBulkModal from "./AIBulkModal";
import { API_URL } from "../../utils/api";

interface RulesListProps {
  category: Category;
  onRuleSelect: (ruleIndex: number | null) => void;
  selectedRuleIndex: number | null;
  statsWindow: 30 | 60 | 90;
  onCategoryUpdate: () => void;
  allCategories?: Category[];
  searchQuery: string;
}

export default function RulesList({
  category,
  onRuleSelect,
  selectedRuleIndex,
  statsWindow,
  onCategoryUpdate,
  allCategories = [],
  searchQuery,
}: RulesListProps) {
  const [showAddRuleModal, setShowAddRuleModal] = useState(false);
  const [showChangeCategoryModal, setShowChangeCategoryModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const [selectedRuleIndexForMove, setSelectedRuleIndexForMove] = useState<number | null>(null);
  const [targetCategoryId, setTargetCategoryId] = useState<number | null>(null);
  const [moving, setMoving] = useState(false);
  const isOtherCategory = category.name === "Other";

  const handleChangeCategory = async () => {
    if (selectedRuleIndexForMove === null || targetCategoryId === null) return;

    setMoving(true);
    try {
      const response = await fetch(
        `${API_URL}/api/categories/${category.id}/rules/${selectedRuleIndexForMove}/move?target_category_id=${targetCategoryId}`,
        { method: "PUT" }
      );

      if (!response.ok) throw new Error("Failed to move rule");

      setShowChangeCategoryModal(false);
      setSelectedRuleIndexForMove(null);
      setTargetCategoryId(null);
      onCategoryUpdate();
    } catch (err) {
      console.error("Failed to move rule:", err);
    } finally {
      setMoving(false);
    }
  };

  if (isOtherCategory) {
    // For "Other" category, show dummy "No Rule" styled exactly like regular rules
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-heading text-[var(--color-text-primary)] mb-2">
              {category.name}
            </h2>
            <p className="text-body text-[var(--color-text-secondary)]">
              1 rule
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAIModal(true)}
              className="btn btn-primary flex items-center gap-2"
            >
              <SparkleIcon size={16} />
              AI Categorize
            </button>
          </div>
        </div>

        {/* "No Rule" styled exactly like regular rule cards */}
        <div className="space-y-3 mb-6">
          <div className="card p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-body font-semibold text-[var(--color-text-primary)] truncate">
                    No Rule
                  </h3>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-caption font-medium bg-amber-100 text-amber-800">
                    Uncategorized
                  </span>
                </div>
                <p className="text-caption text-[var(--color-text-secondary)]">
                  Merchants that haven't been categorized yet
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Show merchants directly for "Other" */}
        <MerchantsList
          categoryId={category.id}
          ruleIndex={null}
          statsWindow={statsWindow}
          onCategoryUpdate={onCategoryUpdate}
          isOtherCategory={true}
          searchQuery={searchQuery}
          allCategories={allCategories}
        />
      </div>
    );
  }

  // Regular category - show rules
  const rules = category.keywords || [];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-heading text-[var(--color-text-primary)] mb-2">
            {category.name}
          </h2>
          <p className="text-body text-[var(--color-text-secondary)]">
            {rules.length} {rules.length === 1 ? "rule" : "rules"}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAIModal(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <SparkleIcon size={16} />
            AI Categorize
          </button>
          <button
            onClick={() => setShowAddRuleModal(true)}
            className="btn btn-secondary"
          >
            + Add Rule
          </button>
        </div>
      </div>

      {rules.length === 0 ? (
        <div className="card p-8 text-center mb-6">
          <p className="text-body text-[var(--color-text-secondary)] mb-4">
            No rules defined for this category yet
          </p>
          <button
            onClick={() => setShowAddRuleModal(true)}
            className="btn btn-primary"
          >
            + Add First Rule
          </button>
        </div>
      ) : (
        <div className="space-y-3 mb-6">
          {rules.map((rule, index) => {
            const patternType = getPatternType(rule);
            const isSelected = selectedRuleIndex === index;

            return (
              <div
                key={index}
                className={`card p-4 transition-apple ${
                  isSelected
                    ? "border-2 border-[var(--color-primary)] bg-[var(--color-primary)] bg-opacity-5"
                    : ""
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <button
                    onClick={() => {
                      // Toggle: clicking on selected rule unselects it
                      if (isSelected) {
                        onRuleSelect(null);
                      } else {
                        onRuleSelect(index);
                      }
                    }}
                    className="flex-1 min-w-0 text-left hover:opacity-80 transition-apple"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-body font-semibold text-[var(--color-text-primary)] truncate">
                        {rule}
                      </h3>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-caption font-medium ${getPatternTypeBadgeClass(
                          patternType
                        )}`}
                      >
                        {patternType}
                      </span>
                      {isSelected && (
                        <span className="text-caption text-[var(--color-primary)] font-medium">
                          ✓ Selected
                        </span>
                      )}
                    </div>
                    <p className="text-caption text-[var(--color-text-secondary)]">
                      {isSelected
                        ? "Click to show all merchants in this category"
                        : "Click to filter merchants by this rule"}
                    </p>
                  </button>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedRuleIndexForMove(index);
                        setShowChangeCategoryModal(true);
                      }}
                      className="btn btn-secondary text-caption py-1 px-3"
                    >
                      Change Category
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Show merchants list - filtered by selected rule or all merchants if no rule selected */}
      <div className="mt-6">
        <h3 className="text-body font-semibold text-[var(--color-text-primary)] mb-4">
          {selectedRuleIndex !== null
            ? `Merchants matching "${rules[selectedRuleIndex]}"`
            : "All Merchants in this Category"}
        </h3>
        <CategoryMerchantsList
          categoryId={category.id}
          statsWindow={statsWindow}
          onCategoryUpdate={onCategoryUpdate}
          allCategories={allCategories}
          searchQuery={searchQuery}
        />
      </div>

      {/* Change Category Modal */}
      {showChangeCategoryModal && selectedRuleIndex !== null && (
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
                  Moving rule: <span className="font-semibold text-[var(--color-text-primary)]">{rules[selectedRuleIndex]}</span>
                </p>
                <p className="text-caption text-[var(--color-text-secondary)]">
                  From: {category.name}
                </p>
              </div>

              <div>
                <label className="block text-body font-medium text-[var(--color-text-primary)] mb-2">
                  To Category:
                </label>
                <select
                  value={targetCategoryId || ""}
                  onChange={(e) => setTargetCategoryId(parseInt(e.target.value))}
                  className="input w-full"
                >
                  <option value="">Select a category...</option>
                  {allCategories
                    .filter((c) => c.id !== category.id)
                    .map((c) => (
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
                  disabled={moving}
                >
                  Cancel
                </button>
                <button
                  onClick={handleChangeCategory}
                  className="flex-1 btn btn-primary"
                  disabled={moving || !targetCategoryId}
                >
                  {moving ? "Moving..." : "Move Rule"}
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
        level="category"
        categoryId={category.id}
        days={statsWindow}
        allCategories={allCategories}
        onSuccess={onCategoryUpdate}
      />
    </div>
  );
}

function getPatternType(pattern: string): "Keyword" | "Keyword OR" | "Regex" {
  if (pattern.includes("|")) return "Keyword OR";
  // Simple heuristic: if it contains regex special chars, it's regex
  if (/[\\^$.*+?()[\]{}]/.test(pattern)) return "Regex";
  return "Keyword";
}

function getPatternTypeBadgeClass(patternType: string): string {
  switch (patternType) {
    case "Keyword":
      return "bg-blue-100 text-blue-800";
    case "Keyword OR":
      return "bg-purple-100 text-purple-800";
    case "Regex":
      return "bg-orange-100 text-orange-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

