"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getApiHeaders, API_URL } from "../utils/api";
import SkeletonLoader from "../components/ui/SkeletonLoader";

interface ReportListItem {
  id: string;
  name: string;
  person_id: number | null;
  person_name: string | null;
  section_count: number;
  created_at: string;
  updated_at: string;
}

interface Person {
  id: number;
  name: string;
  is_active: boolean;
}

export default function ReportsListPage() {
  const router = useRouter();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterPersonId, setFilterPersonId] = useState<string>("all");
  const [creating, setCreating] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  useEffect(() => {
    fetchReports();
    fetchPersons();
  }, [filterPersonId]);

  useEffect(() => {
    const handlePersonChange = () => {
      fetchReports();
    };
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, [filterPersonId]);

  const fetchPersons = async () => {
    try {
      const response = await fetch(`${API_URL}/api/persons/`, {
        headers: getApiHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        // API returns array directly, not { persons: [...] }
        setPersons(Array.isArray(data) ? data : data.persons || []);
      }
    } catch (err) {
      console.error('Failed to fetch persons:', err);
    }
  };

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterPersonId !== "all") {
        params.set('person_id', filterPersonId);
      }
      
      const response = await fetch(
        `${API_URL}/api/reports/?${params.toString()}`,
        { headers: getApiHeaders() }
      );
      
      if (!response.ok) throw new Error('Failed to fetch reports');
      
      const data = await response.json();
      setReports(data.reports || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const createReport = async () => {
    setCreating(true);
    try {
      const response = await fetch(`${API_URL}/api/reports/`, {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({}),
      });
      
      if (!response.ok) throw new Error('Failed to create report');
      
      const report = await response.json();
      router.push(`/reports/${report.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create report');
    } finally {
      setCreating(false);
    }
  };

  const deleteReport = async (reportId: string) => {
    if (!confirm('Are you sure you want to delete this report?')) return;
    
    try {
      const response = await fetch(`${API_URL}/api/reports/${reportId}`, {
        method: 'DELETE',
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error('Failed to delete report');
      
      setReports(reports.filter(r => r.id !== reportId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete report');
    }
  };

  const duplicateReport = async (reportId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/reports/${reportId}/duplicate`, {
        method: 'POST',
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error('Failed to duplicate report');
      
      await fetchReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate report');
    }
  };

  const startRename = (report: ReportListItem) => {
    setRenamingId(report.id);
    setRenameValue(report.name);
  };

  const cancelRename = () => {
    setRenamingId(null);
    setRenameValue("");
  };

  const saveRename = async (reportId: string) => {
    if (!renameValue.trim()) {
      cancelRename();
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/api/reports/${reportId}`, {
        method: 'PUT',
        headers: getApiHeaders(),
        body: JSON.stringify({ name: renameValue.trim() }),
      });
      
      if (!response.ok) throw new Error('Failed to rename report');
      
      setReports(reports.map(r => 
        r.id === reportId ? { ...r, name: renameValue.trim() } : r
      ));
      cancelRename();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename report');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Group reports by person
  const groupedReports = reports.reduce((acc, report) => {
    const key = report.person_name || 'No Person';
    if (!acc[key]) acc[key] = [];
    acc[key].push(report);
    return acc;
  }, {} as Record<string, ReportListItem[]>);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-title text-[var(--color-text-primary)]">Reports</h1>
          <p className="text-body text-[var(--color-text-secondary)] mt-1">
            Create and manage financial reports across all persons
          </p>
        </div>
        <button
          onClick={createReport}
          disabled={creating}
          className="btn btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {creating ? (
            <>
              <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Creating...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Report
            </>
          )}
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="card p-4 bg-red-50 border border-red-200">
          <p className="text-body text-red-800">{error}</p>
          <button 
            onClick={() => setError(null)}
            className="mt-2 text-caption text-red-600 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <label className="text-body text-[var(--color-text-secondary)]">
            Filter by Person:
          </label>
          <select
            value={filterPersonId}
            onChange={(e) => setFilterPersonId(e.target.value)}
            className="input w-auto"
          >
            <option value="all">All Persons</option>
            {persons.map((person) => (
              <option key={person.id} value={person.id}>
                {person.name} {person.is_active ? '(Active)' : ''}
              </option>
            ))}
          </select>
          <span className="text-caption text-[var(--color-text-tertiary)]">
            {reports.length} report{reports.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Reports List */}
      {loading ? (
        <SkeletonLoader variant="list" count={3} />
      ) : reports.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-16 h-16 mx-auto text-[var(--color-text-tertiary)] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-heading text-[var(--color-text-primary)] mb-2">
            No reports yet
          </h3>
          <p className="text-body text-[var(--color-text-secondary)] mb-6">
            Create your first financial report to get started.
          </p>
          <button
            onClick={createReport}
            disabled={creating}
            className="btn btn-primary"
          >
            Create Your First Report
          </button>
        </div>
      ) : filterPersonId === "all" ? (
        // Grouped view
        <div className="space-y-6">
          {Object.entries(groupedReports).map(([personName, personReports]) => (
            <div key={personName}>
              <h2 className="text-heading text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
                <svg className="w-5 h-5 text-[var(--color-primary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                {personName}
              </h2>
              <div className="space-y-3">
                {personReports.map((report) => (
                  <ReportCard
                    key={report.id}
                    report={report}
                    isRenaming={renamingId === report.id}
                    renameValue={renameValue}
                    onRenameValueChange={setRenameValue}
                    onStartRename={() => startRename(report)}
                    onCancelRename={cancelRename}
                    onSaveRename={() => saveRename(report.id)}
                    onOpen={() => router.push(`/reports/${report.id}`)}
                    onDuplicate={() => duplicateReport(report.id)}
                    onDelete={() => deleteReport(report.id)}
                    formatDate={formatDate}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        // Flat view
        <div className="space-y-3">
          {reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              isRenaming={renamingId === report.id}
              renameValue={renameValue}
              onRenameValueChange={setRenameValue}
              onStartRename={() => startRename(report)}
              onCancelRename={cancelRename}
              onSaveRename={() => saveRename(report.id)}
              onOpen={() => router.push(`/reports/${report.id}`)}
              onDuplicate={() => duplicateReport(report.id)}
              onDelete={() => deleteReport(report.id)}
              formatDate={formatDate}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ReportCardProps {
  report: ReportListItem;
  isRenaming: boolean;
  renameValue: string;
  onRenameValueChange: (value: string) => void;
  onStartRename: () => void;
  onCancelRename: () => void;
  onSaveRename: () => void;
  onOpen: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  formatDate: (date: string) => string;
}

function ReportCard({
  report,
  isRenaming,
  renameValue,
  onRenameValueChange,
  onStartRename,
  onCancelRename,
  onSaveRename,
  onOpen,
  onDuplicate,
  onDelete,
  formatDate,
}: ReportCardProps) {
  return (
    <div 
      className="card p-4 hover:shadow-md transition-shadow cursor-pointer group"
      onClick={() => !isRenaming && onOpen()}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          {isRenaming ? (
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={renameValue}
                onChange={(e) => onRenameValueChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onSaveRename();
                  if (e.key === 'Escape') onCancelRename();
                }}
                className="input py-1 px-2 text-body"
                autoFocus
              />
              <button
                onClick={onSaveRename}
                className="p-1 text-green-600 hover:bg-green-50 rounded"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </button>
              <button
                onClick={onCancelRename}
                className="p-1 text-gray-600 hover:bg-gray-50 rounded"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ) : (
            <>
              <h3 className="text-body font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-primary)] transition-colors truncate">
                {report.name}
              </h3>
            </>
          )}
          <p className="text-caption text-[var(--color-text-tertiary)] mt-1">
            Updated {formatDate(report.updated_at)}
          </p>
        </div>
        
        <div className="flex items-center gap-1 ml-4" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onStartRename}
            className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors"
            title="Rename"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            onClick={onDuplicate}
            className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors"
            title="Duplicate"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-[var(--color-text-secondary)] hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
