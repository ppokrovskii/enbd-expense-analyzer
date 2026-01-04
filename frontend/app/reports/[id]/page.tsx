"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { getApiHeaders } from "../../utils/api";
import SkeletonLoader from "../../components/ui/SkeletonLoader";
import FilterPopup from "../../components/report/FilterPopup";
import SummarySection from "../../components/report/SummarySection";
import ExpenseOverviewSection from "../../components/report/ExpenseOverviewSection";
import TopCategoriesSection from "../../components/report/TopCategoriesSection";
import RecurringSection from "../../components/report/RecurringSection";
import TrendsSection from "../../components/report/TrendsSection";
import InsightsSection from "../../components/report/InsightsSection";

interface SectionFilters {
  start_date?: string;
  end_date?: string;
  group_by?: string;
}

interface SectionContent {
  takeaway?: string;
  bullets?: string[];
}

interface ReportSection {
  id: number;
  section_type: string;
  position: number;
  custom_title: string | null;
  display_title: string;
  filters: SectionFilters | null;
  content: SectionContent | null;
  created_at: string;
  updated_at: string;
}

interface Report {
  id: string;
  name: string;
  person_id: number | null;
  person_name: string | null;
  sections: ReportSection[];
  created_at: string;
  updated_at: string;
}

interface SectionType {
  value: string;
  label: string;
  has_ai_generate: boolean;
  has_grouping: boolean;
}

export default function ReportEditorPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id as string;

  const [report, setReport] = useState<Report | null>(null);
  const [sectionTypes, setSectionTypes] = useState<SectionType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Editing states
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const [editingSectionTitle, setEditingSectionTitle] = useState<number | null>(null);
  const [sectionTitleValue, setSectionTitleValue] = useState("");

  // Add section dropdown
  const [showAddSection, setShowAddSection] = useState(false);

  // Filter popup
  const [filterSectionId, setFilterSectionId] = useState<number | null>(null);

  useEffect(() => {
    fetchReport();
    fetchSectionTypes();
  }, [reportId]);

  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}`,
        { headers: getApiHeaders() }
      );
      
      if (!response.ok) {
        if (response.status === 404) {
          router.push('/reports');
          return;
        }
        throw new Error('Failed to fetch report');
      }
      
      const data = await response.json();
      setReport(data);
      setNameValue(data.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const fetchSectionTypes = async () => {
    try {
      const response = await fetch(
        'http://localhost:8000/api/reports/section-types',
        { headers: getApiHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setSectionTypes(data.section_types || []);
      }
    } catch (err) {
      console.error('Failed to fetch section types:', err);
    }
  };

  const saveReportName = async () => {
    if (!nameValue.trim() || !report) return;
    
    setSaving(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}`,
        {
          method: 'PUT',
          headers: getApiHeaders(),
          body: JSON.stringify({ name: nameValue.trim() }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to save');
      
      const updated = await response.json();
      setReport(updated);
      setEditingName(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const saveSectionTitle = async (sectionId: number) => {
    if (!report) return;
    
    setSaving(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}/sections/${sectionId}`,
        {
          method: 'PUT',
          headers: getApiHeaders(),
          body: JSON.stringify({ 
            custom_title: sectionTitleValue.trim() || null 
          }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to save');
      
      await fetchReport();
      setEditingSectionTitle(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const addSection = async (sectionType: string) => {
    setSaving(true);
    setShowAddSection(false);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}/sections`,
        {
          method: 'POST',
          headers: getApiHeaders(),
          body: JSON.stringify({ section_type: sectionType }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to add section');
      
      await fetchReport();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add section');
    } finally {
      setSaving(false);
    }
  };

  const deleteSection = async (sectionId: number) => {
    if (!confirm('Are you sure you want to remove this section?')) return;
    
    setSaving(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}/sections/${sectionId}`,
        {
          method: 'DELETE',
          headers: getApiHeaders(),
        }
      );
      
      if (!response.ok) throw new Error('Failed to delete section');
      
      await fetchReport();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete section');
    } finally {
      setSaving(false);
    }
  };

  const moveSection = async (sectionId: number, direction: 'up' | 'down') => {
    setSaving(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}/sections/${sectionId}/move`,
        {
          method: 'PUT',
          headers: getApiHeaders(),
          body: JSON.stringify({ direction }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to move section');
      
      const updated = await response.json();
      setReport(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to move section');
    } finally {
      setSaving(false);
    }
  };

  const updateSectionFilters = async (sectionId: number, filters: SectionFilters) => {
    setSaving(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}/sections/${sectionId}`,
        {
          method: 'PUT',
          headers: getApiHeaders(),
          body: JSON.stringify({ filters }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to save filters');
      
      await fetchReport();
      setFilterSectionId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save filters');
    } finally {
      setSaving(false);
    }
  };

  const updateSectionContent = useCallback(async (sectionId: number, content: SectionContent) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/reports/${reportId}/sections/${sectionId}`,
        {
          method: 'PUT',
          headers: getApiHeaders(),
          body: JSON.stringify({ content }),
        }
      );
      
      if (!response.ok) throw new Error('Failed to save content');
    } catch (err) {
      console.error('Failed to save section content:', err);
    }
  }, [reportId]);

  const exportPDF = async () => {
    // Client-side PDF generation using html2pdf.js
    try {
      const html2pdf = (await import('html2pdf.js')).default;
      const element = document.getElementById('report-content');
      if (!element) return;
      
      const opt = {
        margin: [10, 10, 10, 10],
        filename: `${report?.name || 'report'}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      };
      
      html2pdf().set(opt).from(element).save();
    } catch (err) {
      setError('Failed to generate PDF. Please try again.');
    }
  };

  const renderSection = (section: ReportSection) => {
    const sectionTypeInfo = sectionTypes.find(t => t.value === section.section_type);
    const isFirst = section.position === 0;
    const isLast = report ? section.position === report.sections.length - 1 : true;
    
    const commonProps = {
      filters: section.filters || {},
      content: section.content || {},
      onContentChange: (content: SectionContent) => updateSectionContent(section.id, content),
    };

    let sectionContent;
    switch (section.section_type) {
      case 'summary':
        sectionContent = <SummarySection {...commonProps} />;
        break;
      case 'expense_overview':
        sectionContent = <ExpenseOverviewSection {...commonProps} />;
        break;
      case 'top_categories':
        sectionContent = <TopCategoriesSection {...commonProps} />;
        break;
      case 'recurring':
        sectionContent = <RecurringSection {...commonProps} />;
        break;
      case 'trends':
        sectionContent = <TrendsSection {...commonProps} />;
        break;
      case 'insights':
        sectionContent = <InsightsSection {...commonProps} />;
        break;
      default:
        sectionContent = (
          <div className="text-center py-8 text-[var(--color-text-tertiary)]">
            Unknown section type: {section.section_type}
          </div>
        );
    }

    return (
      <div key={section.id} className="card overflow-hidden print:shadow-none print:border">
        {/* Section Header */}
        <div className="flex items-center justify-between p-4 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border-light)] no-print">
          <div className="flex-1 min-w-0">
            {editingSectionTitle === section.id ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={sectionTitleValue}
                  onChange={(e) => setSectionTitleValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveSectionTitle(section.id);
                    if (e.key === 'Escape') setEditingSectionTitle(null);
                  }}
                  placeholder={section.display_title}
                  className="input py-1 px-2 text-body flex-1"
                  autoFocus
                />
                <button
                  onClick={() => saveSectionTitle(section.id)}
                  className="p-1 text-green-600 hover:bg-green-50 rounded"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </button>
                <button
                  onClick={() => setEditingSectionTitle(null)}
                  className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  setEditingSectionTitle(section.id);
                  setSectionTitleValue(section.custom_title || '');
                }}
                className="text-left group"
              >
                <h3 className="text-body font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-primary)] transition-colors">
                  {section.display_title}
                </h3>
              </button>
            )}
          </div>
          
          <div className="flex items-center gap-1 ml-4">
            {/* Filters button */}
            <button
              onClick={() => setFilterSectionId(section.id)}
              className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors"
              title="Filters"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
            </button>
            
            {/* Move up */}
            {!isFirst && section.section_type !== 'summary' && (
              <button
                onClick={() => moveSection(section.id, 'up')}
                disabled={saving || section.position === 1}
                className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                title="Move Up"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
              </button>
            )}
            
            {/* Move down */}
            {!isLast && section.section_type !== 'summary' && (
              <button
                onClick={() => moveSection(section.id, 'down')}
                disabled={saving}
                className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                title="Move Down"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            )}
            
            {/* Delete (not for Summary) */}
            {section.section_type !== 'summary' && (
              <button
                onClick={() => deleteSection(section.id)}
                disabled={saving}
                className="p-2 text-[var(--color-text-secondary)] hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-30"
                title="Remove Section"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        </div>
        
        {/* Print-only title */}
        <div className="hidden print:block p-4 border-b border-[var(--color-border-light)]">
          <h3 className="text-body font-semibold text-[var(--color-text-primary)]">
            {section.display_title}
          </h3>
        </div>
        
        {/* Section Content */}
        <div className="p-6">
          {sectionContent}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader variant="text" />
        <SkeletonLoader variant="card" count={3} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="text-center py-12">
        <p className="text-[var(--color-text-secondary)]">Report not found</p>
        <button
          onClick={() => router.push('/reports')}
          className="btn btn-primary mt-4"
        >
          Back to Reports
        </button>
      </div>
    );
  }

  const currentFilterSection = report.sections.find(s => s.id === filterSectionId);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between no-print">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/reports')}
            className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-bg-tertiary)] rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <div>
            {editingName ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveReportName();
                    if (e.key === 'Escape') {
                      setEditingName(false);
                      setNameValue(report.name);
                    }
                  }}
                  className="input py-1 px-3 text-title"
                  autoFocus
                />
                <button
                  onClick={saveReportName}
                  disabled={saving}
                  className="p-1 text-green-600 hover:bg-green-50 rounded"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </button>
                <button
                  onClick={() => {
                    setEditingName(false);
                    setNameValue(report.name);
                  }}
                  className="p-1 text-gray-600 hover:bg-gray-50 rounded"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <button
                onClick={() => setEditingName(true)}
                className="text-left group"
              >
                <h1 className="text-title text-[var(--color-text-primary)] group-hover:text-[var(--color-primary)] transition-colors">
                  {report.name}
                </h1>
              </button>
            )}
            {report.person_name && (
              <p className="text-caption text-[var(--color-text-tertiary)] mt-0.5">
                {report.person_name}
              </p>
            )}
          </div>
        </div>
        
        <button
          onClick={exportPDF}
          className="btn btn-primary flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          Export PDF
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="card p-4 bg-red-50 border border-red-200 no-print">
          <p className="text-body text-red-800">{error}</p>
          <button 
            onClick={() => setError(null)}
            className="mt-2 text-caption text-red-600 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Report Content (for PDF export) */}
      <div id="report-content" className="space-y-6">
        {/* Print header */}
        <div className="hidden print:block mb-8">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{report.name}</h1>
          {report.person_name && (
            <p className="text-[var(--color-text-secondary)]">{report.person_name}</p>
          )}
        </div>
        
        {/* Sections */}
        {report.sections
          .sort((a, b) => a.position - b.position)
          .map(section => renderSection(section))}
      </div>

      {/* Add Section Button */}
      <div className="relative no-print">
        <button
          onClick={() => setShowAddSection(!showAddSection)}
          disabled={saving}
          className="w-full py-4 border-2 border-dashed border-[var(--color-border)] rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] hover:border-[var(--color-primary)] transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Section
        </button>
        
        {showAddSection && (
          <div className="absolute top-full left-0 right-0 mt-2 card p-2 shadow-lg z-10">
            <div className="space-y-1">
              {sectionTypes.map((type) => (
                <button
                  key={type.value}
                  onClick={() => addSection(type.value)}
                  className="w-full text-left px-4 py-3 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors"
                >
                  <div className="font-medium text-[var(--color-text-primary)]">
                    {type.label}
                  </div>
                  <div className="text-caption text-[var(--color-text-tertiary)] flex items-center gap-2 mt-0.5">
                    {type.has_ai_generate && (
                      <span className="inline-flex items-center gap-1">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        AI Generate
                      </span>
                    )}
                    {type.has_grouping && (
                      <span>Weekly/Monthly</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filter Popup */}
      {filterSectionId !== null && currentFilterSection && (
        <FilterPopup
          isOpen={true}
          onClose={() => setFilterSectionId(null)}
          filters={currentFilterSection.filters || {}}
          onSave={(filters) => updateSectionFilters(filterSectionId, filters)}
          showGroupBy={currentFilterSection.section_type === 'expense_overview'}
        />
      )}
    </div>
  );
}

