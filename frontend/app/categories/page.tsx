"use client";

import { useState, useEffect } from "react";

interface Category {
  id: number;
  name: string;
  keywords: string[];
  created_at: string;
  updated_at: string;
}

interface CategoryStats {
  category: string;
  transaction_count: number;
  total_amount: number;
}

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [stats, setStats] = useState<CategoryStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  
  const [newCategory, setNewCategory] = useState({
    name: "",
    keywords: ""
  });

  useEffect(() => {
    fetchCategories();
    fetchStats();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/categories");
      if (!response.ok) throw new Error("Failed to fetch categories");
      const data = await response.json();
      setCategories(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load categories");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/categories/stats");
      if (!response.ok) throw new Error("Failed to fetch stats");
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  const handleAddCategory = async () => {
    if (!newCategory.name.trim()) {
      alert("Category name is required");
      return;
    }

    try {
      const keywords = newCategory.keywords
        .split("\n")
        .map(r => r.trim())
        .filter(r => r.length > 0);

      const response = await fetch("http://localhost:8000/api/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newCategory.name,
          keywords: keywords
        })
      });

      if (!response.ok) throw new Error("Failed to create category");
      
      setShowAddModal(false);
      setNewCategory({ name: "", keywords: "" });
      fetchCategories();
      fetchStats();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create category");
    }
  };

  const handleUpdateCategory = async () => {
    if (!editingCategory) return;

    try {
      const keywords = newCategory.keywords
        .split("\n")
        .map(r => r.trim())
        .filter(r => r.length > 0);

      const response = await fetch(`http://localhost:8000/api/categories/${editingCategory.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newCategory.name,
          keywords: keywords
        })
      });

      if (!response.ok) throw new Error("Failed to update category");
      
      setShowEditModal(false);
      setEditingCategory(null);
      setNewCategory({ name: "", keywords: "" });
      fetchCategories();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update category");
    }
  };

  const handleDeleteCategory = async (id: number) => {
    if (!confirm("Are you sure you want to delete this category?")) return;

    try {
      const response = await fetch(`http://localhost:8000/api/categories/${id}`, {
        method: "DELETE"
      });

      if (!response.ok) throw new Error("Failed to delete category");
      
      fetchCategories();
      fetchStats();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete category");
    }
  };

  const handleApplyRules = async () => {
    if (!confirm("This will recategorize all transactions based on current rules. Continue?")) return;

    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/api/categories/apply-rules", {
        method: "POST"
      });

      if (!response.ok) throw new Error("Failed to apply rules");
      
      const result = await response.json();
      alert(`Recategorized ${result.updated_count} transactions`);
      fetchStats();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to apply rules");
    } finally {
      setLoading(false);
    }
  };

  const handleAIRecategorize = async () => {
    if (!confirm("This will use AI to categorize 'Other' transactions. This may take a while and will use OpenAI API tokens. Continue?")) return;

    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/api/categories/ai-recategorize", {
        method: "POST"
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to run AI categorization");
      }
      
      const result = await response.json();
      alert(`AI categorized ${result.categorized_count} transactions\nCached: ${result.cached_count}\nFailed: ${result.failed_count}`);
      fetchCategories();
      fetchStats();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to run AI categorization");
    } finally {
      setLoading(false);
    }
  };

  const openEditModal = (category: Category) => {
    setEditingCategory(category);
    setNewCategory({
      name: category.name,
      keywords: category.keywords.join("\n")
    });
    setShowEditModal(true);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getCategoryStats = (categoryName: string) => {
    return stats.find(s => s.category === categoryName);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">❌ {error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">📂 Category Management</h1>
        <div className="space-x-2">
          <button
            onClick={handleApplyRules}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
          >
            🔄 Apply Rules to All
          </button>
          <button
            onClick={handleAIRecategorize}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          >
            🤖 AI Categorize
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            + Add Category
          </button>
        </div>
      </div>

      {/* Category List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {categories.map((category) => {
          const catStats = getCategoryStats(category.name);
          return (
            <div key={category.id} className="bg-white p-4 rounded-lg shadow border border-gray-200">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-lg text-gray-800">{category.name}</h3>
                <div className="space-x-2">
                  <button
                    onClick={() => openEditModal(category)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => handleDeleteCategory(category.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>

              {/* Stats */}
              {catStats && (
                <div className="text-sm text-gray-600 mb-3">
                  <p>{catStats.transaction_count} transactions • {formatCurrency(catStats.total_amount)}</p>
                </div>
              )}

              {/* Rules */}
              <div className="text-sm">
                <p className="font-medium text-gray-700 mb-1">Keywords ({category.keywords.length}):</p>
                {category.keywords.length > 0 ? (
                  <ul className="list-disc list-inside text-gray-600 space-y-1">
                    {category.keywords.slice(0, 3).map((keyword, idx) => (
                      <li key={idx} className="truncate">{keyword}</li>
                    ))}
                    {category.keywords.length > 3 && (
                      <li className="text-gray-500">...and {category.keywords.length - 3} more</li>
                    )}
                  </ul>
                ) : (
                  <p className="text-gray-500 italic">No keywords defined</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Add New Category</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category Name *
                </label>
                <input
                  type="text"
                  value={newCategory.name}
                  onChange={(e) => setNewCategory({...newCategory, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., Entertainment"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Keywords (one per line)
                </label>
                <textarea
                  value={newCategory.keywords}
                  onChange={(e) => setNewCategory({...newCategory, keywords: e.target.value})}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="netflix&#10;spotify&#10;youtube premium"
                />
                <p className="text-xs text-gray-500 mt-1">Each keyword is a substring to match in merchant names (case-insensitive)</p>
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleAddCategory}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add Category
              </button>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewCategory({ name: "", keywords: "" });
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingCategory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Edit Category</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category Name *
                </label>
                <input
                  type="text"
                  value={newCategory.name}
                  onChange={(e) => setNewCategory({...newCategory, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Keywords (one per line)
                </label>
                <textarea
                  value={newCategory.keywords}
                  onChange={(e) => setNewCategory({...newCategory, keywords: e.target.value})}
                  rows={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleUpdateCategory}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Save Changes
              </button>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingCategory(null);
                  setNewCategory({ name: "", keywords: "" });
                }}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

