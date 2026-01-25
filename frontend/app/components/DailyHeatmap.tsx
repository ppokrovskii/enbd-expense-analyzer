"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { API_URL, getApiHeaders } from "../utils/api";
import SkeletonLoader from "./ui/SkeletonLoader";
import EmptyState from "./ui/EmptyState";

interface DailySpendingData {
  date: string;
  amount: number;
}

interface DailyHeatmapProps {
  viewMode: "weekly" | "monthly";
  startDate: string;
  endDate: string;
  dailyLimit: number;
}

// Day names for weekly view
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const FULL_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function DailyHeatmap({
  viewMode,
  startDate,
  endDate,
  dailyLimit,
}: DailyHeatmapProps) {
  const router = useRouter();
  const [data, setData] = useState<DailySpendingData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedRow, setCopiedRow] = useState<string | null>(null);

  // Listen for workspace changes
  const [workspaceVersion, setWorkspaceVersion] = useState(0);
  useEffect(() => {
    const handleWorkspaceChange = () => setWorkspaceVersion((v) => v + 1);
    window.addEventListener("workspaceChanged", handleWorkspaceChange);
    return () => window.removeEventListener("workspaceChanged", handleWorkspaceChange);
  }, []);

  // Fetch daily spending data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);

        const response = await fetch(
          `${API_URL}/api/chart/daily?${params.toString()}`,
          { headers: getApiHeaders() }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.statusText}`);
        }

        const result = await response.json();
        setData(result.data || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [startDate, endDate, workspaceVersion]);

  // Create a map of date -> amount for quick lookup
  const dataMap = useMemo(() => {
    const map = new Map<string, number>();
    data.forEach((d) => map.set(d.date, d.amount));
    return map;
  }, [data]);

  // Generate rows based on view mode
  const rows = useMemo(() => {
    if (!startDate || !endDate) return [];

    const start = new Date(startDate);
    const end = new Date(endDate);

    if (viewMode === "weekly") {
      // Group by weeks (Monday to Sunday)
      const weeks: { key: string; label: string; startDate: Date; days: (Date | null)[] }[] = [];
      
      // Find the Monday of the start week
      const currentDate = new Date(start);
      const dayOfWeek = currentDate.getDay();
      const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
      currentDate.setDate(currentDate.getDate() + mondayOffset);

      while (currentDate <= end) {
        const weekStart = new Date(currentDate);
        const days: (Date | null)[] = [];

        for (let i = 0; i < 7; i++) {
          const day = new Date(weekStart);
          day.setDate(weekStart.getDate() + i);
          // Only include days within our range
          if (day >= start && day <= end) {
            days.push(day);
          } else {
            days.push(null);
          }
        }

        weeks.push({
          key: weekStart.toISOString().split("T")[0],
          label: formatWeekLabel(weekStart),
          startDate: weekStart,
          days,
        });

        currentDate.setDate(currentDate.getDate() + 7);
      }

      return weeks;
    } else {
      // Group by months
      const months: { key: string; label: string; startDate: Date; days: (Date | null)[] }[] = [];
      
      const currentMonth = new Date(start.getFullYear(), start.getMonth(), 1);
      const endMonth = new Date(end.getFullYear(), end.getMonth() + 1, 0);

      while (currentMonth <= endMonth) {
        const daysInMonth = new Date(
          currentMonth.getFullYear(),
          currentMonth.getMonth() + 1,
          0
        ).getDate();
        
        const days: (Date | null)[] = [];
        for (let d = 1; d <= 31; d++) {
          if (d <= daysInMonth) {
            const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), d);
            if (date >= start && date <= end) {
              days.push(date);
            } else {
              days.push(null);
            }
          } else {
            days.push(null);
          }
        }

        months.push({
          key: `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, "0")}`,
          label: formatMonthLabel(currentMonth),
          startDate: new Date(currentMonth),
          days,
        });

        currentMonth.setMonth(currentMonth.getMonth() + 1);
      }

      return months;
    }
  }, [viewMode, startDate, endDate]);

  // Format functions
  function formatWeekLabel(date: Date): string {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function formatMonthLabel(date: Date): string {
    return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }

  function formatAmount(amount: number): string {
    if (amount === 0) return "-";
    return new Intl.NumberFormat("en-AE", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }

  function getAmountForDate(date: Date | null): number {
    if (!date) return 0;
    const dateStr = date.toISOString().split("T")[0];
    return dataMap.get(dateStr) || 0;
  }

  function getRowTotal(days: (Date | null)[]): number {
    return days.reduce((sum, day) => sum + getAmountForDate(day), 0);
  }

  // Determine color based on amount and limit
  function getCellStyle(amount: number): React.CSSProperties {
    if (amount === 0) {
      return { color: "var(--color-text-tertiary)" };
    }
    if (amount > dailyLimit) {
      return { color: "var(--color-destructive)", fontWeight: 600 };
    }
    return { color: "var(--color-success)", fontWeight: 500 };
  }

  function getTotalStyle(total: number, daysCount: number): React.CSSProperties {
    const limit = dailyLimit * daysCount;
    if (total > limit) {
      return { color: "var(--color-destructive)", fontWeight: 700 };
    }
    return { color: "var(--color-success)", fontWeight: 700 };
  }

  // Handle cell click - navigate to transactions page
  function handleCellClick(date: Date | null) {
    if (!date) return;
    const dateStr = date.toISOString().split("T")[0];
    router.push(`/transactions?startDate=${dateStr}&endDate=${dateStr}&groupBy=week`);
  }

  // Copy row to clipboard
  async function handleCopyRow(row: { key: string; label: string; days: (Date | null)[] }) {
    const daysCount = row.days.filter(d => d !== null).length;
    const periodLimit = dailyLimit * daysCount;
    const total = getRowTotal(row.days);
    const difference = Math.abs(total - periodLimit);
    const isOverLimit = total > periodLimit;

    let lines: string[] = [];

    if (viewMode === "weekly") {
      row.days.forEach((day, index) => {
        const amount = getAmountForDate(day);
        const emoji = day ? (amount > dailyLimit ? "⚠️" : "✅") : "";
        if (day) {
          lines.push(`${FULL_DAY_NAMES[index]}: AED ${formatAmount(amount)} ${emoji}`);
        }
      });
    } else {
      row.days.forEach((day, index) => {
        if (day) {
          const amount = getAmountForDate(day);
          const emoji = amount > dailyLimit ? "⚠️" : "✅";
          lines.push(`${index + 1}: AED ${formatAmount(amount)} ${emoji}`);
        }
      });
    }

    const periodName = viewMode === "weekly" ? "weekly" : "monthly";
    const limitStatus = isOverLimit
      ? `(${formatAmount(difference)} AED above ${periodName} limit of ${formatAmount(periodLimit)})`
      : `(${formatAmount(difference)} AED below ${periodName} limit of ${formatAmount(periodLimit)})`;

    lines.push(`\nTotal spent: AED ${formatAmount(total)} ${limitStatus}`);

    const text = lines.join("\n");

    try {
      await navigator.clipboard.writeText(text);
      setCopiedRow(row.key);
      setTimeout(() => setCopiedRow(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }

  if (loading) {
    return <SkeletonLoader variant="table" count={5} />;
  }

  if (error) {
    return (
      <div className="card p-4 bg-red-50 border border-red-200">
        <p className="text-body text-red-800">{error}</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="card">
        <EmptyState
          title="No spending data"
          description="Select a date range to view your daily spending"
          icon={
            <svg className="w-16 h-16 text-[var(--color-text-tertiary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
      </div>
    );
  }

  // Column headers
  const columns = viewMode === "weekly" ? DAY_NAMES : Array.from({ length: 31 }, (_, i) => i + 1);

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[var(--color-border-light)]">
          <thead className="bg-[var(--color-bg-secondary)]">
            <tr>
              <th className="px-4 py-3 text-left text-label uppercase tracking-wider text-[var(--color-text-secondary)] sticky left-0 bg-[var(--color-bg-secondary)] z-10">
                {viewMode === "weekly" ? "Week" : "Month"}
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-2 py-3 text-center text-label uppercase tracking-wider text-[var(--color-text-secondary)] min-w-[60px]"
                >
                  {col}
                </th>
              ))}
              <th className="px-4 py-3 text-right text-label uppercase tracking-wider text-[var(--color-text-secondary)] min-w-[100px]">
                Total
              </th>
              <th className="px-2 py-3 text-center text-label uppercase tracking-wider text-[var(--color-text-secondary)] w-12">
                {/* Copy button column */}
              </th>
            </tr>
          </thead>
          <tbody className="bg-[var(--color-bg-primary)] divide-y divide-[var(--color-border)]">
            {rows.map((row) => {
              const total = getRowTotal(row.days);
              const validDaysCount = row.days.filter(d => d !== null).length;
              
              return (
                <tr key={row.key} className="group hover:bg-[var(--color-bg-secondary)] transition-apple">
                  <td className="px-4 py-3 whitespace-nowrap text-body font-medium text-[var(--color-text-primary)] sticky left-0 bg-[var(--color-bg-primary)] group-hover:bg-[var(--color-bg-secondary)] transition-apple z-10">
                    {row.label}
                  </td>
                  {row.days.map((day, index) => {
                    const amount = getAmountForDate(day);
                    return (
                      <td
                        key={index}
                        onClick={() => handleCellClick(day)}
                        className={`px-2 py-3 text-center text-body cursor-pointer hover:bg-[var(--color-primary)]/10 transition-apple ${
                          !day ? "text-[var(--color-text-tertiary)]" : ""
                        }`}
                        style={day ? getCellStyle(amount) : undefined}
                        title={day ? `${day.toLocaleDateString()}: AED ${formatAmount(amount)}` : ""}
                      >
                        {day ? formatAmount(amount) : "-"}
                      </td>
                    );
                  })}
                  <td
                    className="px-4 py-3 text-right text-body whitespace-nowrap"
                    style={getTotalStyle(total, validDaysCount)}
                  >
                    {formatAmount(total)}
                  </td>
                  <td className="px-2 py-3 text-center">
                    <button
                      onClick={() => handleCopyRow(row)}
                      className="p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
                      title="Copy to clipboard"
                    >
                      {copiedRow === row.key ? (
                        <svg className="w-4 h-4 text-[var(--color-success)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* Legend */}
      <div className="px-4 py-3 border-t border-[var(--color-border-light)] bg-[var(--color-bg-secondary)]">
        <div className="flex items-center gap-6 text-caption text-[var(--color-text-secondary)]">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[var(--color-success)]"></span>
            <span>Below AED {dailyLimit}/day</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[var(--color-destructive)]"></span>
            <span>Above AED {dailyLimit}/day</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-text-tertiary)]">-</span>
            <span>No expenses</span>
          </div>
        </div>
      </div>
    </div>
  );
}
