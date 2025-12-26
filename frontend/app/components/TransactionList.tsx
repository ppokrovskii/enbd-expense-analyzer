"use client";

import { useEffect, useState } from "react";
import SkeletonLoader from "./ui/SkeletonLoader";
import EmptyState from "./ui/EmptyState";

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
  excludedCategories?: string[];
  availableCategories?: string[]; // All categories from chart
}

export default function TransactionList({ filters, excludedCategories = [], availableCategories = [] }: TransactionListProps) {
  const [data, setData] = useState<TransactionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Load page size from localStorage, default to 20
  const [pageSize, setPageSize] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('transactionPageSize');
      return saved ? parseInt(saved, 10) : 20;
    }
    return 20;
  });

  // Reset to page 1 when filters or excluded categories change
  useEffect(() => {
    setCurrentPage(1);
  }, [filters, excludedCategories]);

  useEffect(() => {
    fetchTransactions(currentPage, filters || {
      startDate: "",
      endDate: "",
      categories: [],
      accounts: [],
      merchant: ""
    });
  }, [currentPage, filters, excludedCategories, pageSize]);
  
  // Save page size to localStorage when it changes
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
    if (typeof window !== 'undefined') {
      localStorage.setItem('transactionPageSize', newSize.toString());
    }
  };

  const fetchTransactions = async (page: number, appliedFilters: FilterValues) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      if (appliedFilters.startDate) params.append("start_date", appliedFilters.startDate);
      if (appliedFilters.endDate) params.append("end_date", appliedFilters.endDate);
      if (appliedFilters.merchant) params.append("merchant", appliedFilters.merchant);
      
      // Handle categories:
      // If we have excluded categories from chart legend, convert to include filter
      if (excludedCategories.length > 0 && availableCategories.length > 0) {
        // Include only non-excluded categories
        const includedCategories = availableCategories.filter(
          cat => !excludedCategories.includes(cat)
        );
        includedCategories.forEach(cat => params.append("categories", cat));
      } 
      // Otherwise use explicit filter from filter panel
      else if (appliedFilters.categories && appliedFilters.categories.length > 0) {
        appliedFilters.categories.forEach(cat => params.append("categories", cat));
      }
      
      appliedFilters.accounts.forEach(acc => params.append("accounts", acc));

      const response = await fetch(
        `http://localhost:8000/api/transactions?${params.toString()}`
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

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      "Groceries": "bg-purple-500/20 text-purple-300 border border-purple-500/30",
      "Transport": "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30",
      "Food & Dining": "bg-pink-500/20 text-pink-300 border border-pink-500/30",
      "Shopping": "bg-amber-500/20 text-amber-300 border border-amber-500/30",
      "Entertainment": "bg-orange-500/20 text-orange-300 border border-orange-500/30",
      "Utilities": "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30",
      "Technology Subscriptions": "bg-red-500/20 text-red-300 border border-red-500/30",
      "Telecommunications": "bg-blue-500/20 text-blue-300 border border-blue-500/30",
      "Healthcare": "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
      "Salary": "bg-green-500/20 text-green-300 border border-green-500/30",
      "Incoming Transfer": "bg-green-500/20 text-green-300 border border-green-500/30",
      "Other": "bg-gray-500/20 text-gray-300 border border-gray-500/30",
    };
    return colors[category] || "bg-gray-500/20 text-gray-300 border border-gray-500/30";
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
  
  // Show empty state if all transactions are filtered out
  if (filteredTransactions.length === 0 && excludedCategories.length > 0) {
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

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--color-border-light)]">
            <thead className="bg-[var(--color-bg-secondary)]">
              <tr>
                <th className="px-6 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Date
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
                <th className="px-6 py-3 text-right text-label uppercase tracking-wider text-[var(--color-text-secondary)]">
                  Amount
                </th>
              </tr>
            </thead>
            <tbody className="bg-[var(--color-bg-primary)] divide-y divide-[var(--color-border)]">
              {filteredTransactions.map((transaction) => (
                <tr key={transaction.id} className="hover:bg-[var(--color-bg-secondary)] transition-apple">
                  <td className="px-6 py-4 whitespace-nowrap text-body text-[var(--color-text-primary)]">
                    {formatDate(transaction.date)}
                  </td>
                  <td className="px-6 py-4 text-body text-[var(--color-text-primary)]">
                    <div className="max-w-xs">
                      <p className="font-medium truncate" title={transaction.merchant}>
                        {transaction.merchant}
                      </p>
                      {transaction.description && (
                        <p className="text-caption text-[var(--color-text-secondary)] truncate" title={transaction.description}>
                          {transaction.description}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2.5 py-1 inline-flex text-label font-medium rounded-full ${getCategoryColor(transaction.category)}`}>
                      {transaction.category}
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

      {/* Pagination or Summary (when only 1 page) */}
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
                <div className="space-y-1">
                  <p className="text-body text-[var(--color-text-secondary)]">
                    Showing <span className="font-medium text-[var(--color-text-primary)]">{filteredTransactions.length}</span> of{" "}
                    <span className="font-medium text-[var(--color-text-primary)]">{data.total}</span> transactions
                    {excludedCategories.length > 0 && (
                      <span className="text-caption ml-2 text-[var(--color-text-tertiary)]">
                        ({excludedCategories.length} {excludedCategories.length === 1 ? 'category' : 'categories'} excluded)
                      </span>
                    )}
                  </p>
                  <p className="text-caption text-[var(--color-text-secondary)]">
                    Total: <span className="font-semibold text-[var(--color-text-primary)]">{formatCurrencyShort(filteredTotal)}</span>
                  </p>
                </div>
                
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
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
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
            <div className="space-y-1">
              <p className="text-body text-[var(--color-text-secondary)]">
                Showing <span className="font-medium text-[var(--color-text-primary)]">{filteredTransactions.length}</span> 
                {' '}{filteredTransactions.length === 1 ? 'transaction' : 'transactions'}
                {excludedCategories.length > 0 && (
                  <span className="text-caption ml-2 text-[var(--color-text-tertiary)]">
                    ({excludedCategories.length} {excludedCategories.length === 1 ? 'category' : 'categories'} excluded)
                  </span>
                )}
              </p>
              <p className="text-caption text-[var(--color-text-secondary)]">
                Total: <span className="font-semibold text-[var(--color-text-primary)]">{formatCurrencyShort(filteredTotal)}</span>
              </p>
            </div>
            
            {/* Page size selector for single page too */}
            <div className="flex items-center gap-2">
              <label className="text-caption text-[var(--color-text-secondary)] whitespace-nowrap">
                Per page:
              </label>
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
        </div>
      )}
    </div>
  );
}
