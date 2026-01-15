"use client";

import { useState } from "react";
import { Category } from "../../categories/page";
import Modal from "./Modal";
import { API_URL } from "../../utils/api";

interface CategoryFiltersProps {
  categories: Category[];
  selectedCategoryIds: number[];
  onCategorySelect: (categoryIds: number[]) => void;
  onCategoryUpdate: () => void;
}

export default function CategoryFilters({
  categories,
  selectedCategoryIds,
  onCategorySelect,
  onCategoryUpdate,
}: CategoryFiltersProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) {
      setError("Category name cannot be empty.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/categories/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newCategoryName.trim(),
          keywords: [], // No keywords at category level
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to create category");
      }

      setShowAddModal(false);
      setNewCategoryName("");
      onCategoryUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create category");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteCategories = async () => {
    // Validate confirmation for single category
    if (selectedCategoryIds.length === 1) {
      const categoryToDelete = categories.find(c => c.id === selectedCategoryIds[0]);
      if (categoryToDelete && deleteConfirmation !== categoryToDelete.name) {
        setDeleteError(`Please type "${categoryToDelete.name}" to confirm deletion.`);
        return;
      }
    }

    setDeleting(true);
    setDeleteError(null);

    try {
      // Delete each selected category
      const deletePromises = selectedCategoryIds.map(categoryId =>
        fetch(`${API_URL}/api/categories/${categoryId}`, {
          method: "DELETE",
        })
      );

      const responses = await Promise.all(deletePromises);
      
      // Check if any failed
      const failedResponses = responses.filter(r => !r.ok);
      if (failedResponses.length > 0) {
        throw new Error(`Failed to delete ${failedResponses.length} category(ies)`);
      }

      // Success - close modal and update
      setShowDeleteModal(false);
      setDeleteConfirmation("");
      onCategorySelect([]); // Clear selection
      onCategoryUpdate();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete categories");
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleCategory = (categoryId: number) => {
    if (selectedCategoryIds.includes(categoryId)) {
      onCategorySelect(selectedCategoryIds.filter(id => id !== categoryId));
    } else {
      onCategorySelect([...selectedCategoryIds, categoryId]);
    }
  };

  const handleClearSelection = () => {
    onCategorySelect([]);
  };

  // Sort categories: "Other" first, then alphabetically
  const sortedCategories = [...categories].sort((a, b) => {
    if (a.name === "Other") return -1;
    if (b.name === "Other") return 1;
    return a.name.localeCompare(b.name);
  });

  const noneSelected = selectedCategoryIds.length === 0;
  const selectedCategories = categories.filter(c => selectedCategoryIds.includes(c.id));
  const hasOtherSelected = selectedCategories.some(c => c.name === "Other");

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-4">
          <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
            Categories
            {!noneSelected && (
              <span className="ml-2 text-caption text-[var(--color-text-secondary)]">
                ({selectedCategoryIds.length} selected)
              </span>
            )}
          </h3>
          <button
            onClick={handleClearSelection}
            disabled={noneSelected}
            className="text-caption text-[var(--color-primary)] hover:underline disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Clear Selection
          </button>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowDeleteModal(true)}
            disabled={noneSelected || hasOtherSelected}
            className="btn btn-secondary text-caption py-1 px-3 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-40 disabled:cursor-not-allowed"
            title={
              hasOtherSelected 
                ? "Cannot delete 'Other' category" 
                : noneSelected 
                ? "Select categories to delete" 
                : undefined
            }
          >
            Delete Selected
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn btn-primary text-caption py-1 px-3"
          >
            + Add Category
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {sortedCategories.map((category) => {
          const isSelected = selectedCategoryIds.includes(category.id);

          return (
            <button
              key={category.id}
              onClick={() => handleToggleCategory(category.id)}
              className={`inline-flex items-center px-3 py-1.5 rounded-full text-caption font-medium transition-apple ${
                isSelected
                  ? "bg-[var(--color-primary)] text-white"
                  : "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]"
              }`}
            >
              {category.name}
              {isSelected && (
                <svg className="w-4 h-4 ml-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          );
        })}
      </div>

      {/* Add Category Modal */}
      {showAddModal && (
        <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Add New Category">
          <form onSubmit={(e) => {
            e.preventDefault();
            if (!creating && newCategoryName.trim()) {
              handleAddCategory();
            }
          }} className="space-y-4">
            <div>
              <label htmlFor="categoryName" className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1">
                Category Name
              </label>
              <input
                type="text"
                id="categoryName"
                className="input"
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                placeholder="e.g., Food & Dining"
                disabled={creating}
                autoFocus
              />
              <p className="text-caption text-[var(--color-text-tertiary)] mt-1">
                Keywords are added at the rule level, not category level
              </p>
            </div>
            {error && <p className="text-destructive text-caption">{error}</p>}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="btn btn-secondary"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={creating || !newCategoryName.trim()}
              >
                {creating ? "Adding..." : "Add Category"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Delete Category Modal */}
      {showDeleteModal && (
        <Modal 
          isOpen={showDeleteModal} 
          onClose={() => {
            setShowDeleteModal(false);
            setDeleteConfirmation("");
            setDeleteError(null);
          }} 
          title="Delete Categories"
        >
          <div className="space-y-4">
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start gap-3">
                <svg className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <h4 className="font-semibold text-red-800 dark:text-red-200 mb-1">
                    Warning: This action cannot be undone
                  </h4>
                  <p className="text-caption text-red-700 dark:text-red-300">
                    All transactions in {selectedCategories.length === 1 ? 'this category' : 'these categories'} will be moved to "Other" category.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <p className="text-body text-[var(--color-text-primary)] mb-2">
                Categories to delete:
              </p>
              <ul className="list-disc list-inside space-y-1 text-body text-[var(--color-text-secondary)]">
                {selectedCategories.map(cat => (
                  <li key={cat.id}>{cat.name}</li>
                ))}
              </ul>
            </div>

            {selectedCategories.length === 1 && (
              <div>
                <label className="block text-caption font-medium text-[var(--color-text-secondary)] mb-1">
                  Type <span className="font-bold text-[var(--color-text-primary)]">"{selectedCategories[0].name}"</span> to confirm
                </label>
                <input
                  type="text"
                  value={deleteConfirmation}
                  onChange={(e) => {
                    setDeleteConfirmation(e.target.value);
                    setDeleteError(null);
                  }}
                  className="input w-full"
                  placeholder={selectedCategories[0].name}
                  disabled={deleting}
                  autoFocus
                />
              </div>
            )}

            {deleteError && (
              <p className="text-caption text-red-600 dark:text-red-400">{deleteError}</p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteConfirmation("");
                  setDeleteError(null);
                }}
                className="btn btn-secondary"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteCategories}
                className="btn btn-primary bg-red-600 hover:bg-red-700 focus:ring-red-500"
                disabled={deleting || (selectedCategories.length === 1 && deleteConfirmation !== selectedCategories[0].name)}
              >
                {deleting ? "Deleting..." : `Delete ${selectedCategories.length} ${selectedCategories.length === 1 ? 'Category' : 'Categories'}`}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

