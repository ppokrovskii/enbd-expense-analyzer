"use client";

import { useEffect, useState } from "react";
import SkeletonLoader from "./ui/SkeletonLoader";
import EmptyState from "./ui/EmptyState";
import { getApiHeaders, API_URL } from "../utils/api";

interface Transaction {
  id: number;
  date: string;
  account: string;
  merchant: string;
  category: string;
  amount: number;
  amount_signed: number;
  description: string;
}

interface TransactionListResponse {
  transactions: Transaction[];
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

interface TransactionListProps {
  filters?: FilterValues;
  filterMode?: 'none' | 'whitelist' | 'blacklist';
  filteredCategories?: string[];
  availableCategories?: string[]; // All categories from chart
}

export default function TransactionList({ 
  filters, 
  filterMode = 'none', 
  filteredCategories = [], 
  availableCategories = []
}: TransactionListProps) {
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState<'date' | 'amount'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [categoryColors, setCategoryColors] = useState<Record<string, string>>({});
  const [selectedMerchants, setSelectedMerchants] = useState<Set<string>>(new Set());
  
  // Load page size from localStorage, default to 20
  const [pageSize, setPageSize] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('transactionPageSize');
      return saved ? parseInt(saved, 10) : 20;
    }
    return 20;
  });

  // Fetch category colors on mount
  useEffect(() => {
    const fetchCategoryColors = async () => {
      try {
        const response = await fetch(`${API_URL}/api/categories/`, {
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

  useEffect(() => {
    fetchTransactions(currentPage, filters || {
      startDate: "",
      endDate: "",
      categories: [],
      accounts: [],
      merchant: ""
    });
  }, [currentPage, filters, filterMode, filteredCategories, pageSize, sortBy, sortOrder, personVersion]);
  
  // Save page size to localStorage when it changes
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
    if (typeof window !== 'undefined') {
      localStorage.setItem('transactionPageSize', newSize.toString());
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

  const handleSelectAllOnPage = () => {
    if (!data) return;
    
    const merchantsOnPage = new Set(data.transactions.map(t => t.merchant));
    const allSelected = Array.from(merchantsOnPage).every(m => selectedMerchants.has(m));
    
    if (allSelected) {
      // Deselect all merchants on current page
      setSelectedMerchants(prev => {
        const newSet = new Set(prev);
        merchantsOnPage.forEach(m => newSet.delete(m));
        return newSet;
      });
    } else {
      // Select all merchants on current page
      setSelectedMerchants(prev => {
        const newSet = new Set(prev);
        merchantsOnPage.forEach(m => newSet.add(m));
        return newSet;
      });
    }
  };

  const handleAICategorizeSelected = () => {
    if (selectedMerchants.size === 0) return;
    
    // Store merchants in sessionStorage for Rules Manager
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('rules_ai_merchants', JSON.stringify(Array.from(selectedMerchants)));
      sessionStorage.setItem('rules_ai_referrer', 'transactions');
      sessionStorage.setItem('rules_ai_return_url', window.location.href);
    }
    
    // Navigate to Rules Manager page with AI suggestions mode
    window.location.href = '/rules?mode=ai-suggest';
  };

  const fetchTransactions = async (page: number, appliedFilters: FilterValues) => {
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
        // Whitelist mode: only show selected categories
        filteredCategories.forEach((cat) => params.append("categories", cat));
      } else if (filterMode === 'blacklist' && filteredCategories.length > 0 && availableCategories.length > 0) {
        // Blacklist mode: show all except selected categories
        const includedCategories = availableCategories.filter(cat => !filteredCategories.includes(cat));
        includedCategories.forEach(cat => params.append("categories", cat));
      } else if (appliedFilters.categories && appliedFilters.categories.length > 0) {
        // Explicit filter from filter panel
        appliedFilters.categories.forEach(cat => params.append("categories", cat));
      }
      // If filterMode is 'none' and no explicit filter, don't send categories filter at all (show everything)
      
      appliedFilters.accounts.forEach(acc => params.append("accounts", acc));

      const response = await fetch(
        `${API_URL}/api/transactions?${params.toString()}`,
        { headers: getApiHeaders() }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
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
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Math.abs(amount));
  };

  const getCategoryBadgeClass = (category: string) => {
    // Only truly uncategorized (null/empty) gets uncategorized style
    // "Other" is a real category with its own style
    if (!category) {
      return "category-badge category-badge-uncategorized";
    }
    return "category-badge";
  };
  
  const getCategoryStyle = (category: string): React.CSSProperties | undefined => {
    if (!category) {
      return undefined; // Uncategorized uses CSS class styling
    }
    // "Other" gets a neutral gray style
    if (category === 'Other') {
      return {
        backgroundColor: '#6b728040',
        color: '#9ca3af',
      };
    }
    const color = categoryColors[category];
    if (color) {
      // Use 25% opacity background for better visibility
      return {
        backgroundColor: `${color}40`,
        color: color,
      };
    }
    return undefined;
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

  if (!data || data.transactions.length === 0) {
    return (
      <div className="card">
        <EmptyState
          title="No transactions found"
          description="Try adjusting your filters or upload some ENBD files to get started"
          icon={
            <svg className="w-16 h-16 text-[var(--color-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          }
        />
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / pageSize);
  
  // No need for client-side filtering - API returns filtered data
  const filteredTransactions = data.transactions;
  
  // Calculate pagination range
  const getPageNumbers = () => {
    const maxPagesToShow = 5;
    const pages: number[] = [];
    
    if (totalPages <= maxPagesToShow) {
      // Show all pages if total is less than max
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Calculate start and end around current page
      let start = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
      let end = Math.min(totalPages, start + maxPagesToShow - 1);
      
      // Adjust start if we're near the end
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
  
  // Use total_amount from API (all filtered transactions)
  // NOT calculated from current page
  const filteredTotal = data.total_amount || 0;
  
  const formatCurrencyShort = (amount: number) => {
    return new Intl.NumberFormat("en-AE", {
      style: "currency",
      currency: "AED",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };
  
  const handleSort = (field: 'date' | 'amount') => {
    if (sortBy === field) {
      // Toggle order if clicking the same field
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // Default to desc for new field
      setSortBy(field);
      setSortOrder('desc');
    }
  };
  
  const SortIcon = ({ field }: { field: 'date' | 'amount' }) => {
    if (sortBy !== field) {
      // Show neutral icon when not sorted by this field
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
  
  // Show empty state if all transactions are filtered out
  if (filteredTransactions.length === 0 && (filterMode === 'whitelist' || filterMode === 'blacklist')) {
    return (
      <div className="card">
        <EmptyState
          title="All transactions filtered out"
          description="The selected category filters have hidden all transactions. Click on categories in the chart legend to show them again."
          icon={
            <svg className="w-16 h-16 text-[var(--color-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          }
        />
      </div>
    );
  }

  // Determine if all merchants on current page are selected
  const merchantsOnPage = data ? new Set(data.transactions.map(t => t.merchant)) : new Set();
  const allOnPageSelected = merchantsOnPage.size > 0 && Array.from(merchantsOnPage).every(m => selectedMerchants.has(m));

  return (
    <div className="space-y-4">
      {/* Combined Toolbar: Selection + Pagination */}
      <div className={`card px-4 py-3 ${selectedMerchants.size > 0 ? 'bg-[var(--color-primary)]/5 border border-[var(--color-primary)]/20' : ''}`}>
        <div className="flex items-center justify-between gap-4">
          {/* Left side: Info + Selection */}
          <div className="flex items-center gap-4">
            <p className="text-body text-[var(--color-text-secondary)]">
              {totalPages > 1 ? (
                <>Showing <span className="font-medium text-[var(--color-text-primary)]">{filteredTransactions.length}</span> of{" "}
                <span className="font-medium text-[var(--color-text-primary)]">{data.total}</span></>
              ) : (
                <><span className="font-medium text-[var(--color-text-primary)]">{filteredTransactions.length}</span></>
              )}
              {' '}{filteredTransactions.length === 1 ? 'transaction' : 'transactions'}
            </p>
            
            {selectedMerchants.size > 0 && (
              <>
                <span className="text-[var(--color-border-medium)]">•</span>
                <span className="text-body font-medium text-[var(--color-primary)]">
                  {selectedMerchants.size} selected
                </span>
                <button
                  onClick={() => setSelectedMerchants(new Set())}
                  className="text-caption text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
                >
                  Clear
                </button>
              </>
            )}
            
            {/* Page size selector */}
            <div className="hidden sm:flex items-center gap-2">
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(parseInt(e.target.value, 10))}
                className="input py-1 px-2 text-body"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>
          
          {/* Right side: AI Button + Pagination */}
          <div className="flex items-center gap-3">
            {selectedMerchants.size > 0 && (
              <button
                onClick={handleAICategorizeSelected}
                className="px-3 py-1.5 text-sm text-white rounded-lg transition-all flex items-center gap-1.5 font-medium shadow-md hover:shadow-lg hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)',
                }}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                AI Categorize
              </button>
            )}
            
            {totalPages > 1 && (
              <nav className="hidden sm:inline-flex relative z-0 rounded-lg shadow-apple-sm -space-x-px">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-2.5 py-1.5 rounded-l-lg border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-body font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple"
                >
                  ←
                </button>
                {pageNumbers.map((pageNum) => (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`relative inline-flex items-center px-3 py-1.5 border text-body font-medium transition-apple ${
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
                  className="relative inline-flex items-center px-2.5 py-1.5 rounded-r-lg border border-[var(--color-border)] bg-[var(--color-bg-tertiary)] text-body font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple"
                >
                  →
                </button>
              </nav>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--color-border-light)]">
            <thead className="bg-[var(--color-bg-secondary)]">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={allOnPageSelected}
                    onChange={handleSelectAllOnPage}
                    className="checkbox"
                    title="Select all merchants on this page"
                  />
                </th>
                <th 
                  onClick={() => handleSort('date')}
                  className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors select-none"
                >
                  <div className="flex items-center gap-2">
                    Date
                    <SortIcon field="date" />
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Merchant
                </th>
                <th className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Account
                </th>
                <th 
                  onClick={() => handleSort('amount')}
                  className="px-6 py-3 text-right text-label uppercase tracking-wider text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)] transition-colors select-none"
                >
                  <div className="flex items-center justify-end gap-2">
                    Amount
                    <SortIcon field="amount" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="bg-[var(--color-bg-primary)] divide-y divide-[var(--color-border)]">
              {filteredTransactions.map((transaction) => (
                <tr 
                  key={transaction.id} 
                  onClick={() => handleSelectMerchant(transaction.merchant)}
                  className={`group hover:bg-[var(--color-bg-secondary)] transition-apple cursor-pointer ${
                    selectedMerchants.has(transaction.merchant) ? 'bg-[var(--color-primary)]/5' : ''
                  }`}
                >
                  <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedMerchants.has(transaction.merchant)}
                      onChange={() => handleSelectMerchant(transaction.merchant)}
                      className="checkbox"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-body text-[var(--color-text-primary)]">
                    {formatDate(transaction.date)}
                  </td>
                  <td className="px-6 py-4 text-body text-[var(--color-text-primary)]">
                    <div className="max-w-md">
                      <p className="font-medium break-words" title={transaction.merchant}>
                        {transaction.merchant}
                      </p>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span 
                      className={getCategoryBadgeClass(transaction.category)}
                      style={getCategoryStyle(transaction.category)}
                    >
                      {transaction.category || 'Uncategorized'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-body text-[var(--color-text-secondary)]">
                    {transaction.account}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-body text-right">
                    <span className={`font-semibold ${transaction.amount_signed < 0 ? "text-apple-red" : "text-apple-green"}`}>
                      {transaction.amount_signed < 0 ? "-" : "+"}{formatAmount(transaction.amount_signed)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
