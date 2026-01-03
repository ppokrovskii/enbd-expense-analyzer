"use client";

import { useState, useEffect } from "react";
import { getApiHeaders } from "../utils/api";

interface Report {
  id: string;
  title: string;
  report_type: string;
  report_format: string;
  status: string;
  period_start: string;
  period_end: string;
  file_size: number | null;
  created_at: string;
  completed_at: string | null;
}

interface ReportType {
  value: string;
  label: string;
}

interface ReportFormat {
  value: string;
  label: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Form state
  const [reportType, setReportType] = useState("monthly_summary");
  const [reportFormat, setReportFormat] = useState("pdf");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [customTitle, setCustomTitle] = useState("");
  
  // Available options
  const [reportTypes, setReportTypes] = useState<ReportType[]>([]);
  const [reportFormats, setReportFormats] = useState<ReportFormat[]>([]);

  // Listen for person changes
  useEffect(() => {
    const handlePersonChange = () => {
      fetchReports();
    };
    
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, []);

  useEffect(() => {
    fetchReports();
    fetchAvailableTypes();
    setDefaultDates();
  }, []);

  const setDefaultDates = () => {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    
    setPeriodStart(firstDay.toISOString().split('T')[0]);
    setPeriodEnd(lastDay.toISOString().split('T')[0]);
  };

  const fetchReports = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/reports/', {
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error('Failed to fetch reports');
      
      const data = await response.json();
      setReports(data.reports || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableTypes = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/reports/types/available', {
        headers: getApiHeaders(),
      });
      
      if (!response.ok) throw new Error('Failed to fetch report types');
      
      const data = await response.json();
      setReportTypes(data.report_types || []);
      setReportFormats(data.report_formats || []);
    } catch (err) {
      console.error('Failed to fetch report types:', err);
    }
  };

  const generateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setGenerating(true);

    try {
      const response = await fetch('http://localhost:8000/api/reports/generate', {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({
          report_type: reportType,
          report_format: reportFormat,
          period_start: periodStart,
          period_end: periodEnd,
          title: customTitle || undefined,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to generate report');
      }

      const report = await response.json();
      setSuccess(`Report "${report.title}" generated successfully!`);
      fetchReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const downloadReport = async (reportId: string, title: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/reports/${reportId}/download`, {
        headers: getApiHeaders(),
      });

      if (!response.ok) throw new Error('Failed to download report');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.replace(/\s+/g, '_')}.${getExtension(response.headers.get('content-type'))}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download report');
    }
  };

  const deleteReport = async (reportId: string) => {
    if (!confirm('Are you sure you want to delete this report?')) return;

    try {
      const response = await fetch(`http://localhost:8000/api/reports/${reportId}`, {
        method: 'DELETE',
        headers: getApiHeaders(),
      });

      if (!response.ok) throw new Error('Failed to delete report');

      setSuccess('Report deleted successfully');
      fetchReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete report');
    }
  };

  const getExtension = (contentType: string | null): string => {
    if (!contentType) return 'pdf';
    if (contentType.includes('pdf')) return 'pdf';
    if (contentType.includes('spreadsheet') || contentType.includes('excel')) return 'xlsx';
    if (contentType.includes('json')) return 'json';
    if (contentType.includes('csv')) return 'csv';
    return 'pdf';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusBadge = (status: string) => {
    const statusStyles: Record<string, string> = {
      completed: 'bg-green-500/20 text-green-400 border-green-500/30',
      generating: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    
    return (
      <span className={`px-2 py-0.5 text-xs rounded-full border ${statusStyles[status] || 'bg-gray-500/20 text-gray-400'}`}>
        {status}
      </span>
    );
  };

  const getFormatIcon = (format: string) => {
    switch (format.toLowerCase()) {
      case 'pdf':
        return (
          <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 18h12V6h-4V2H4v16zm8-16l4 4h-4V2zM2 0h12l4 4v16H2V0z"/>
          </svg>
        );
      case 'excel':
        return (
          <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 18h12V6h-4V2H4v16zm8-16l4 4h-4V2zM2 0h12l4 4v16H2V0z"/>
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M4 18h12V6h-4V2H4v16zm8-16l4 4h-4V2zM2 0h12l4 4v16H2V0z"/>
          </svg>
        );
    }
  };

  // Quick generate buttons
  const generateMonthlyReport = async (monthsAgo: number = 0) => {
    const today = new Date();
    const targetDate = new Date(today.getFullYear(), today.getMonth() - monthsAgo, 1);
    const month = targetDate.getMonth() + 1;
    const year = targetDate.getFullYear();

    setGenerating(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/generate/monthly?month=${month}&year=${year}&report_format=pdf`,
        {
          method: 'POST',
          headers: getApiHeaders(),
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to generate report');
      }

      const report = await response.json();
      setSuccess(`Report "${report.title}" generated successfully!`);
      fetchReports();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)] p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)] mb-2">
            Financial Reports
          </h1>
          <p className="text-[var(--color-text-secondary)]">
            Generate PDF or Excel reports for your transactions
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/30 text-green-400">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Generate Report Form */}
          <div className="lg:col-span-1">
            <div className="bg-[var(--color-bg-secondary)] rounded-2xl border border-white/5 p-6">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">
                Generate New Report
              </h2>

              {/* Quick Actions */}
              <div className="mb-6 space-y-2">
                <p className="text-sm text-[var(--color-text-secondary)] mb-2">Quick Generate:</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => generateMonthlyReport(0)}
                    disabled={generating}
                    className="px-3 py-1.5 text-sm rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20 transition-apple disabled:opacity-50"
                  >
                    This Month
                  </button>
                  <button
                    onClick={() => generateMonthlyReport(1)}
                    disabled={generating}
                    className="px-3 py-1.5 text-sm rounded-lg bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]/80 transition-apple disabled:opacity-50"
                  >
                    Last Month
                  </button>
                </div>
              </div>

              <div className="border-t border-white/5 pt-4">
                <p className="text-sm text-[var(--color-text-secondary)] mb-4">Or customize:</p>
                
                <form onSubmit={generateReport} className="space-y-4">
                  {/* Report Type */}
                  <div>
                    <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                      Report Type
                    </label>
                    <select
                      value={reportType}
                      onChange={(e) => setReportType(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-white/5 text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]/50"
                    >
                      {reportTypes.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Format */}
                  <div>
                    <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                      Format
                    </label>
                    <div className="flex gap-2">
                      {reportFormats.map((format) => (
                        <button
                          key={format.value}
                          type="button"
                          onClick={() => setReportFormat(format.value)}
                          className={`flex-1 px-3 py-2 rounded-lg border transition-apple ${
                            reportFormat === format.value
                              ? 'bg-[var(--color-primary)]/10 border-[var(--color-primary)]/50 text-[var(--color-primary)]'
                              : 'bg-[var(--color-bg-tertiary)] border-white/5 text-[var(--color-text-secondary)] hover:border-white/10'
                          }`}
                        >
                          {format.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Date Range */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                        From
                      </label>
                      <input
                        type="date"
                        value={periodStart}
                        onChange={(e) => setPeriodStart(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-white/5 text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]/50"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                        To
                      </label>
                      <input
                        type="date"
                        value={periodEnd}
                        onChange={(e) => setPeriodEnd(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-white/5 text-[var(--color-text-primary)] focus:outline-none focus:border-[var(--color-primary)]/50"
                        required
                      />
                    </div>
                  </div>

                  {/* Custom Title */}
                  <div>
                    <label className="block text-sm text-[var(--color-text-secondary)] mb-1">
                      Custom Title (optional)
                    </label>
                    <input
                      type="text"
                      value={customTitle}
                      onChange={(e) => setCustomTitle(e.target.value)}
                      placeholder="e.g., January 2026 Summary"
                      className="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-white/5 text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:border-[var(--color-primary)]/50"
                    />
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={generating}
                    className="w-full py-3 rounded-xl bg-[var(--color-primary)] text-white font-medium hover:bg-[var(--color-primary-dark)] disabled:opacity-50 disabled:cursor-not-allowed transition-apple flex items-center justify-center gap-2"
                  >
                    {generating ? (
                      <>
                        <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                        </svg>
                        Generating...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Generate Report
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Reports List */}
          <div className="lg:col-span-2">
            <div className="bg-[var(--color-bg-secondary)] rounded-2xl border border-white/5 p-6">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">
                Generated Reports
              </h2>

              {loading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 rounded-xl bg-[var(--color-bg-tertiary)] animate-pulse" />
                  ))}
                </div>
              ) : reports.length === 0 ? (
                <div className="text-center py-12">
                  <svg className="w-16 h-16 mx-auto text-[var(--color-text-tertiary)] mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-[var(--color-text-secondary)]">No reports generated yet</p>
                  <p className="text-sm text-[var(--color-text-tertiary)] mt-1">
                    Use the form to generate your first report
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {reports.map((report) => (
                    <div
                      key={report.id}
                      className="flex items-center justify-between p-4 rounded-xl bg-[var(--color-bg-tertiary)]/50 hover:bg-[var(--color-bg-tertiary)] transition-apple group"
                    >
                      <div className="flex items-center gap-4">
                        {getFormatIcon(report.report_format)}
                        <div>
                          <h3 className="font-medium text-[var(--color-text-primary)]">
                            {report.title}
                          </h3>
                          <div className="flex items-center gap-3 text-sm text-[var(--color-text-tertiary)]">
                            <span>{formatDate(report.period_start)} - {formatDate(report.period_end)}</span>
                            <span>•</span>
                            <span>{formatFileSize(report.file_size)}</span>
                            <span>•</span>
                            {getStatusBadge(report.status)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-apple">
                        {report.status === 'completed' && (
                          <button
                            onClick={() => downloadReport(report.id, report.title)}
                            className="p-2 rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/20 transition-apple"
                            title="Download"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </button>
                        )}
                        <button
                          onClick={() => deleteReport(report.id)}
                          className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-apple"
                          title="Delete"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

