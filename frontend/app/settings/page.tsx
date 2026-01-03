"use client";

import React, { useState, useEffect } from 'react';
import { useToast } from '../hooks/useToast';
import { ToastContainer } from '../components/Toast';
import { COLOR_PALETTE, COLOR_FAMILIES, getContrastColor } from '../constants/colors';

interface Account {
  id: number;
  account_name: string;
  account_number: string;
  bank: string;
  is_primary: boolean;
}

interface Category {
  id: number;
  name: string;
  color?: string;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'accounts' | 'categories'>('accounts');
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Account form - simplified to name + value only
  const [accountForm, setAccountForm] = useState({
    name: '',
    value: '',
    bank: 'ENBD',
  });
  
  // Category form - only name + color (no keywords)
  const [categoryForm, setCategoryForm] = useState<{ name: string; color: string }>({
    name: '',
    color: COLOR_PALETTE[0],
  });
  
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [showColorPicker, setShowColorPicker] = useState(false);
  
  const { toasts, showToast, removeToast } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [accountsRes, categoriesRes] = await Promise.all([
        fetch('/api/accounts/', {
          headers: { 'X-User-Id': 'default_user' },
        }),
        fetch('/api/categories/', {
          headers: { 'X-User-Id': 'default_user' },
        }),
      ]);

      if (accountsRes.ok) {
        setAccounts(await accountsRes.json());
      }
      if (categoriesRes.ok) {
        setCategories(await categoriesRes.json());
      }
    } catch (error) {
      console.error('Failed to load data:', error);
      showToast('Failed to load settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/accounts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify(accountForm),
      });

      if (response.ok) {
        showToast('Account added successfully', 'success');
        setAccountForm({
          name: '',
          value: '',
          bank: 'ENBD',
        });
        loadData();
      } else {
        const error = await response.json();
        showToast(error.detail || 'Failed to add account', 'error');
      }
    } catch (error) {
      console.error('Failed to add account:', error);
      showToast('Failed to add account', 'error');
    }
  };

  const handleDeleteAccount = async (accountId: number) => {
    if (!confirm('Are you sure you want to delete this account?')) {
      return;
    }

    try {
      const response = await fetch(`/api/accounts/${accountId}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': 'default_user' },
      });

      if (response.ok) {
        showToast('Account deleted successfully', 'success');
        loadData();
      } else {
        showToast('Failed to delete account', 'error');
      }
    } catch (error) {
      console.error('Failed to delete account:', error);
      showToast('Failed to delete account', 'error');
    }
  };

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const payload = {
      name: categoryForm.name,
      color: categoryForm.color,
    };

    try {
      const url = editingCategoryId 
        ? `/api/categories/${editingCategoryId}` 
        : '/api/categories/';
      
      const method = editingCategoryId ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        showToast(`Category ${editingCategoryId ? 'updated' : 'added'} successfully`, 'success');
        setCategoryForm({
          name: '',
          color: COLOR_PALETTE[categories.length % COLOR_PALETTE.length],
        });
        setEditingCategoryId(null);
        loadData();
      } else {
        const error = await response.json();
        showToast(error.detail || 'Failed to save category', 'error');
      }
    } catch (error) {
      console.error('Failed to save category:', error);
      showToast('Failed to save category', 'error');
    }
  };

  const handleEditCategory = (category: Category) => {
    setCategoryForm({
      name: category.name,
      color: category.color || COLOR_PALETTE[0],
    });
    setEditingCategoryId(category.id);
    setActiveTab('categories');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDeleteCategory = async (categoryId: number) => {
    if (!confirm('Are you sure you want to delete this category? All associated rules and transactions will be affected.')) {
      return;
    }

    try {
      const response = await fetch(`/api/categories/${categoryId}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': 'default_user' },
      });

      if (response.ok) {
        showToast('Category deleted successfully', 'success');
        loadData();
      } else {
        showToast('Failed to delete category', 'error');
      }
    } catch (error) {
      console.error('Failed to delete category:', error);
      showToast('Failed to delete category', 'error');
    }
  };

  const handleTriggerRecategorization = async () => {
    if (!confirm('This will re-categorize all transactions based on current rules. Continue?')) {
      return;
    }

    try {
      const response = await fetch('/api/jobs/recategorize', {
        method: 'POST',
        headers: { 'X-User-Id': 'default_user' },
      });

      if (response.ok) {
        const job = await response.json();
        showToast(`Recategorization job started (ID: ${job.id}). You'll receive a notification when complete.`, 'success');
      } else {
        showToast('Failed to start recategorization', 'error');
      }
    } catch (error) {
      console.error('Failed to start recategorization:', error);
      showToast('Failed to start recategorization', 'error');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-[var(--color-text-secondary)]">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-[var(--color-text-primary)]">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-[var(--color-border)]">
        <button
          onClick={() => setActiveTab('accounts')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'accounts'
              ? 'text-[var(--color-primary)] border-b-2 border-[var(--color-primary)]'
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
          }`}
        >
          Accounts
        </button>
        <button
          onClick={() => setActiveTab('categories')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'categories'
              ? 'text-[var(--color-primary)] border-b-2 border-[var(--color-primary)]'
              : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
          }`}
        >
          Categories
        </button>
      </div>

      {/* Accounts Tab */}
      {activeTab === 'accounts' && (
        <div>
          <div className="bg-[var(--color-bg-secondary)] p-6 rounded-lg mb-6">
            <h2 className="text-xl font-semibold mb-4 text-[var(--color-text-primary)]">Add New Account</h2>
            <form onSubmit={handleAddAccount} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1 text-[var(--color-text-primary)]">
                    Account Name
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., current account (auto-converts to current-account)"
                    value={accountForm.name}
                    onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })}
                    className="w-full px-3 py-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded text-[var(--color-text-primary)]"
                  />
                  <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                    Spaces will be replaced with dashes (e.g., "current account" → "current-account")
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1 text-[var(--color-text-primary)]">
                    Bank
                  </label>
                  <select
                    value={accountForm.bank}
                    onChange={(e) => setAccountForm({ ...accountForm, bank: e.target.value })}
                    className="w-full px-3 py-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded text-[var(--color-text-primary)]"
                  >
                    <option value="ENBD">ENBD</option>
                    <option value="FAB">FAB</option>
                    <option value="WIO">WIO</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1 text-[var(--color-text-primary)]">
                    Account Value
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., 1234567890 or ****7890"
                    value={accountForm.value}
                    onChange={(e) => setAccountForm({ ...accountForm, value: e.target.value })}
                    className="w-full px-3 py-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded text-[var(--color-text-primary)]"
                  />
                  <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                    Add two records: one with full number and one with masked (e.g., name="current-account" value="123456", then name="current-account-masked" value="****56")
                  </p>
                </div>
              </div>
              <button
                type="submit"
                className="px-4 py-2 bg-[var(--color-primary)] text-white rounded hover:opacity-90 transition-opacity"
              >
                Add Account
              </button>
            </form>
          </div>

          {/* Accounts List */}
          <div className="bg-[var(--color-bg-secondary)] p-6 rounded-lg">
            <h2 className="text-xl font-semibold mb-4 text-[var(--color-text-primary)]">Your Accounts</h2>
            {accounts.length === 0 ? (
              <p className="text-[var(--color-text-secondary)]">No accounts configured yet.</p>
            ) : (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <div
                    key={account.id}
                    className="flex items-center justify-between p-4 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded"
                  >
                    <div>
                      <div className="font-medium text-[var(--color-text-primary)]">
                        {account.account_name}
                        {account.is_primary && (
                          <span className="ml-2 px-2 py-1 text-xs bg-[var(--color-primary)] text-white rounded">
                            Primary
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-[var(--color-text-secondary)]">
                        {account.bank} • {account.account_number_masked}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteAccount(account.id)}
                      className="px-3 py-1 text-sm text-red-400 hover:text-red-300 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Categories Tab */}
      {activeTab === 'categories' && (
        <div>
          <div className="bg-[var(--color-bg-secondary)] p-6 rounded-lg mb-6">
            <h2 className="text-xl font-semibold mb-4 text-[var(--color-text-primary)]">
              {editingCategoryId ? 'Edit Category' : 'Add New Category'}
            </h2>
            <form onSubmit={handleCategorySubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1 text-[var(--color-text-primary)]">
                  Category Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Groceries"
                  value={categoryForm.name}
                  onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
                  className="w-full px-3 py-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded text-[var(--color-text-primary)]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 text-[var(--color-text-primary)]">
                  Color
                </label>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowColorPicker(!showColorPicker)}
                    className="flex items-center gap-2 px-3 py-2 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded"
                  >
                    <div
                      className="w-6 h-6 rounded border border-[var(--color-border)]"
                      style={{ backgroundColor: categoryForm.color }}
                    />
                    <span className="text-[var(--color-text-primary)]">{categoryForm.color}</span>
                  </button>
                  
                  {showColorPicker && (
                    <div className="absolute z-10 mt-2 p-4 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-lg shadow-lg">
                      <div className="grid grid-cols-8 gap-2 max-w-md">
                        {COLOR_PALETTE.map((color) => (
                          <button
                            key={color}
                            type="button"
                            onClick={() => {
                              setCategoryForm({ ...categoryForm, color });
                              setShowColorPicker(false);
                            }}
                            className="w-8 h-8 rounded border-2 hover:scale-110 transition-transform"
                            style={{
                              backgroundColor: color,
                              borderColor: categoryForm.color === color ? '#fff' : 'transparent',
                            }}
                            title={color}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                  Keywords and exclusion rules are managed separately via the Rules API
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  className="px-4 py-2 bg-[var(--color-primary)] text-white rounded hover:opacity-90 transition-opacity"
                >
                  {editingCategoryId ? 'Update Category' : 'Add Category'}
                </button>
                {editingCategoryId && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingCategoryId(null);
                      setCategoryForm({
                        name: '',
                        color: COLOR_PALETTE[categories.length % COLOR_PALETTE.length],
                      });
                    }}
                    className="px-4 py-2 bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] rounded hover:opacity-90 transition-opacity"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Categories List */}
          <div className="bg-[var(--color-bg-secondary)] p-6 rounded-lg mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Your Categories</h2>
              <button
                onClick={handleTriggerRecategorization}
                className="px-4 py-2 bg-[var(--color-accent)] text-white rounded hover:opacity-90 transition-opacity text-sm"
              >
                Re-categorize All Transactions
              </button>
            </div>
            {categories.length === 0 ? (
              <p className="text-[var(--color-text-secondary)]">No categories configured yet.</p>
            ) : (
              <div className="space-y-3">
                {categories.map((category) => (
                  <div
                    key={category.id}
                    className="flex items-start justify-between p-4 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <div
                          className="w-4 h-4 rounded"
                          style={{ backgroundColor: category.color || '#999' }}
                        />
                        <span className="font-medium text-[var(--color-text-primary)]">
                          {category.name}
                        </span>
                      </div>
                      <div className="text-sm text-[var(--color-text-secondary)]">
                        Color: {category.color || 'Not set'}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditCategory(category)}
                        className="px-3 py-1 text-sm text-[var(--color-primary)] hover:opacity-80 transition-opacity"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteCategory(category.id)}
                        className="px-3 py-1 text-sm text-red-400 hover:text-red-300 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

