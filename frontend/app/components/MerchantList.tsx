"use client";

import { useEffect, useState, useCallback } from "react";
import SkeletonLoader from "./ui/SkeletonLoader";
import EmptyState from "./ui/EmptyState";
import { getApiHeaders } from "../utils/api";

interface MerchantSummary {
  merchant: string;
  category: string | null;
  transaction_count: number;
  total_amount: number;
  first_date: string;
  last_date: string;
}

interface MerchantListResponse {
  merchants: MerchantSummary[];
  total: number;
  total_amount: number;
  page: number;
  page_size: number;
}

interface FilterValues {
  startDate: string;
  endDate: string;
  categories: string[];
  accounts: string[];
  merchant: string;
}

interface MerchantListProps {
  filters?: FilterValues;
  filterMode?: 'none' | 'whitelist' | 'blacklist';
  filteredCategories?: string[];
  availableCategories?: string[];
}

export default function MerchantList({ 
  filters, 
  filterMode = 'none', 
  filteredCategories = [], 
  availableCategories = []
}: MerchantListProps) {
  const [data, setData] = useState<MerchantListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<'total_amount' | 'transaction_count' | 'merchant' | 'last_date'>('total_amount');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [categoryColors, setCategoryColors] = useState<Record<string, string>>({});
  const [selectedMerchants, setSelectedMerchants] = useState<Set<string>>(new Set());
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  
  // Load page size from localStorage, default to 50
  const [pageSize, setPageSize] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('merchantPageSize');
      return saved ? parseInt(saved, 10) : 50;
    }
    return 50;
  });

  // Fetch category colors on mount
  useEffect(() => {
    const fetchCategoryColors = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/categories/', {
          headers: getApiHeaders(),
        });
        if (response.ok) {
          const categories = await response.json();
          const colorMap: Record<string, string> = {};
          categories.forEach((cat: { name: string; color?: string }) => {
            if (cat.color) {
              colorMap[cat.name] = cat.color;
            }
          });
          setCategoryColors(colorMap);
        }
      } catch (error) {
        console.error('Failed to fetch category colors:', error);
      }
    };
    fetchCategoryColors();
  }, []);

  // Track person changes to trigger re-fetch
  const [personVersion, setPersonVersion] = useState(0);
  
  // Listen for person changes
  useEffect(() => {
    const handlePersonChange = () => {
      setPersonVersion(v => v + 1);
      setCurrentPage(1);
      setSelectedMerchants(new Set());
    };
    
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, []);

  // Reset to page 1 when filters, selected categories, or sorting changes
  useEffect(() => {
    setCurrentPage(1);
    setSelectedMerchants(new Set());
  }, [filters, filterMode, filteredCategories, sortBy, sortOrder]);

  const fetchMerchants = useCallback(async (page: number, appliedFilters: FilterValues) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      params.append("sort_by", sortBy);
      params.append("sort_order", sortOrder);
      
      if (appliedFilters.startDate) params.append("start_date", appliedFilters.startDate);
      if (appliedFilters.endDate) params.append("end_date", appliedFilters.endDate);
      if (appliedFilters.merchant) params.append("merchant", appliedFilters.merchant);
      
      // Smart filter: whitelist or blacklist mode
      if (filterMode === 'whitelist' && filteredCategories.length > 0) {
        filteredCategories.forEach((cat) => params.append("categories", cat));
      } else if (filterMode === 'blacklist' && filteredCategories.length > 0 && availableCategories.length > 0) {
        const includedCategories = availableCategories.filter(cat => !filteredCategories.includes(cat));
        includedCategories.forEach(cat => params.append("categories", cat));
      } else if (appliedFilters.categories && appliedFilters.categories.length > 0) {
        appliedFilters.categories.forEach(cat => params.append("categories", cat));
      }
      
      appliedFilters.accounts.forEach(acc => params.append("accounts", acc));

      const response = await fetch(
        `http://localhost:8000/api/merchants?${params.toString()}`,
        { headers: getApiHeaders() }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load merchants");
    } finally {
      setLoading(false);
    }
  }, [pageSize, sortBy, sortOrder, filterMode, filteredCategories, availableCategories]);

  useEffect(() => {
    fetchMerchants(currentPage, filters || {
      startDate: "",
      endDate: "",
      categories: [],
      accounts: [],
      merchant: ""
    });
  }, [currentPage, filters, pageSize, sortBy, sortOrder, personVersion, fetchMerchants]);
  
  // Save page size to localStorage when it changes
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
    if (typeof window !== 'undefined') {
      localStorage.setItem('merchantPageSize', newSize.toString());
    }
  };

  const handleSelectMerchant = (merchant: string) => {
    setSelectedMerchants(prev => {
      const newSet = new Set(prev);
      if (newSet.has(merchant)) {
        newSet.delete(merchant);
      } else {
        newSet.add(merchant);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (!data) return;
    
    if (selectedMerchants.size === data.merchants.length) {
      // Deselect all
      setSelectedMerchants(new Set());
    } else {
      // Select all on current page
      setSelectedMerchants(new Set(data.merchants.map(m => m.merchant)));
    }
  };

  const handleAICategorize = () => {
    if (selectedMerchants.size === 0) return;
    
    // Store merchants in sessionStorage
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('ai_categorize_merchants', JSON.stringify(Array.from(selectedMerchants)));
      sessionStorage.setItem('ai_categorize_days', '90');
      sessionStorage.setItem('ai_categorize_referrer', 'merchants');
      sessionStorage.setItem('ai_categorize_return_url', window.location.href);
    }
    
    // Navigate to AI suggestions page
    window.location.href = '/categories/ai-suggestions';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Math.abs(amount));
  };

  const getCategoryColor = (category: string | null) => {
    if (!category) return "bg-gray-500/20 text-gray-300 border border-gray-500/30";
    const color = categoryColors[category];
    if (color) {
      return `px-2.5 py-1 inline-flex text-label font-medium rounded-full border`;
    }
    return "bg-gray-500/20 text-gray-300 border border-gray-500/30";
  };
  
  const getCategoryStyle = (category: string | null): React.CSSProperties | undefined => {
    if (!category) return undefined;
    const color = categoryColors[category];
    if (color) {
      return {
        backgroundColor: `${color}33`,
        color: color,
        borderColor: `${color}66`,
      };
    }
    return undefined;
  };

  const handleSort = (field: 'total_amount' | 'transaction_count' | 'merchant' | 'last_date') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };
  
  const SortIcon = ({ field }: { field: 'total_amount' | 'transaction_count' | 'merchant' | 'last_date' }) => {
    if (sortBy !== field) {
      return (
        <svg className="w-4 h-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    if (sortOrder === 'asc') {
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
        </svg>
      );
    }
    return (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  if (loading && !data) {
    return <SkeletonLoader variant="table" count={5} />;
  }

  if (error) {
    return (
      <div className="card p-4 bg-red-50 border border-red-200">
        <p className="text-body text-red-800">{error}</p>
      </div>
    );
  }

  if (!data || data.merchants.length === 0) {
    return (
      <div className="card">
        <EmptyState
          title="No merchants found"
          description="Try adjusting your filters or upload some transactions to get started"
          icon={
            <svg className="w-16 h-16 text-[var(--color-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          }
        />
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);
  
  const getPageNumbers = () => {
    const maxPagesToShow = 5;
    const pages: number[] = [];
    
    if (totalPages <= maxPagesToShow) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      let start = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
      let end = Math.min(totalPages, start + maxPagesToShow - 1);
      
      if (end === totalPages) {
        start = Math.max(1, end - maxPagesToShow + 1);
      }
      
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
    }
    
    return pages;
  };
  
  const pageNumbers = getPageNumbers();

  return (
    <div className="space-y-4">
      {/* Action Bar */}
      {selectedMerchants.size > 0 && (
        <div className="card px-4 py-3 bg-[var(--color-primary)]/5 border border-[var(--color-primary)]/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-body font-medium text-[var(--color-primary)]">
                {selectedMerchants.size} merchant{selectedMerchants.size !== 1 ? 's' : ''} selected
              </span>
              <button
                onClick={() => setSelectedMerchants(new Set())}
                className="text-caption text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
              >
                Clear selection
              </button>
            </div>
            <button
              onClick={handleAICategorize}
              disabled={isAiProcessing}
              className="px-4 py-2 text-sm text-white rounded-lg transition-all flex items-center gap-2 font-medium shadow-md hover:shadow-lg hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)',
              }}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
              AI Categorize Selected
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--color-border-light)]">
            <thead className="bg-[var(--color-bg-secondary)]">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={data.merchants.length > 0 && selectedMerchants.size === data.merchants.length}
                    onChange={handleSelectAll}
                    className="w-4 h-4 rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)] cursor-pointer"
                  />
                </th>
                <th 
                  onClick={() => handleSort('merchant')}
                  className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors select-none"
                >
                  <div className="flex items-center gap-2">
                    Merchant
                    <SortIcon field="merchant" />
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Category
                </th>
                <th 
                  onClick={() => handleSort('transaction_count')}
                  className="px-6 py-3 text-center text-label uppercase tracking-wider text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors select-none"
                >
                  <div className="flex items-center justify-center gap-2">
                    Transactions
                    <SortIcon field="transaction_count" />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('total_amount')}
                  className="px-6 py-3 text-right text-label uppercase tracking-wider text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors select-none"
                >
                  <div className="flex items-center justify-end gap-2">
                    Total Amount
                    <SortIcon field="total_amount" />
                  </div>
                </th>
                <th 
                  onClick={() => handleSort('last_date')}
                  className="px-6 py-3 text-right text-label uppercase tracking-wider text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors select-none"
                >
                  <div className="flex items-center justify-end gap-2">
                    Last Transaction
                    <SortIcon field="last_date" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="bg-[var(--color-bg-primary)] divide-y divide-[var(--color-border)]">
              {data.merchants.map((merchant) => (
                <tr 
                  key={merchant.merchant} 
                  className={`group hover:bg-[var(--color-bg-secondary)] transition-apple ${
                    selectedMerchants.has(merchant.merchant) ? 'bg-[var(--color-primary)]/5' : ''
                  }`}
                >
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selectedMerchants.has(merchant.merchant)}
                      onChange={() => handleSelectMerchant(merchant.merchant)}
                      className="w-4 h-4 rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)] cursor-pointer"
                    />
                  </td>
                  <td className="px-6 py-4 text-body text-[var(--color-text-primary)]">
                    <div className="max-w-md">
                      <p className="font-medium break-words" title={merchant.merchant}>
                        {merchant.merchant}
                      </p>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span 
                      className={getCategoryColor(merchant.category)}
                      style={getCategoryStyle(merchant.category)}
                    >
                      {merchant.category || 'Uncategorized'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-body text-center text-[var(--color-text-secondary)]">
                    {merchant.transaction_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-body text-right">
                    <span className="font-semibold text-[var(--color-text-primary)]">
                      {formatAmount(merchant.total_amount)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-body text-right text-[var(--color-text-secondary)]">
                    {formatDate(merchant.last_date)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 ? (
        <div className="card px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            {/* Mobile pagination */}
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            
            {/* Desktop pagination */}
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between sm:gap-6">
              {/* Info section */}
              <div className="flex items-center gap-4">
                <p className="text-body text-[var(--color-text-secondary)]">
                  <span className="font-medium text-[var(--color-text-primary)]">{data.total}</span> merchants • Total: {' '}
                  <span className="font-medium text-[var(--color-text-primary)]">{formatAmount(data.total_amount)}</span>
                </p>
                
                {/* Page size selector */}
                <div className="flex items-center gap-2">
                  <label className="text-caption text-[var(--color-text-secondary)] whitespace-nowrap">
                    Per page:
                  </label>
                  <select
                    value={pageSize}
                    onChange={(e) => handlePageSizeChange(parseInt(e.target.value, 10))}
                    className="input py-1 px-2 text-body"
                  >
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={200}>200</option>
                  </select>
                </div>
              </div>
              
              {/* Page navigation */}
              <div>
                <nav className="relative z-0 inline-flex rounded-lg shadow-apple-sm -space-x-px">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center px-3 py-2 rounded-l-lg border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-body font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple"
                  >
                    ←
                  </button>
                  {pageNumbers.map((pageNum) => (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`relative inline-flex items-center px-4 py-2 border text-body font-medium transition-apple ${
                        currentPage === pageNum
                          ? "z-10 bg-[var(--color-primary)] border-[var(--color-primary)] text-white"
                          : "bg-[var(--color-bg-tertiary)] border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]"
                      }`}
                    >
                      {pageNum}
                    </button>
                  ))}
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center px-3 py-2 rounded-r-lg border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-body font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple"
                  >
                    →
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Summary when only 1 page */
        <div className="card px-4 py-3">
          <div className="flex items-center justify-between">
            <p className="text-body text-[var(--color-text-secondary)]">
              <span className="font-medium text-[var(--color-text-primary)]">{data.total}</span> 
              {' '}{data.total === 1 ? 'merchant' : 'merchants'} • Total: {' '}
              <span className="font-medium text-[var(--color-text-primary)]">{formatAmount(data.total_amount)}</span>
            </p>
            
            <div className="flex items-center gap-2">
              <label className="text-caption text-[var(--color-text-secondary)] whitespace-nowrap">
                Per page:
              </label>
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(parseInt(e.target.value, 10))}
                className="input py-1 px-2 text-body"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

