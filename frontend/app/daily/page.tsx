"use client";

import { useState, useMemo, useEffect } from "react";
import DailyHeatmap from "../components/DailyHeatmap";
import SegmentedControl from "../components/ui/SegmentedControl";

export default function DailyPage() {
  // View mode: weekly or monthly
  const [viewMode, setViewMode] = useState<"weekly" | "monthly">("weekly");
  
  // Daily spending limit
  const [dailyLimit, setDailyLimit] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('dailySpendingLimit');
      return saved ? parseInt(saved, 10) : 600;
    }
    return 600;
  });

  // Date range state
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // Calculate default dates based on view mode
  useEffect(() => {
    const today = new Date();
    
    if (viewMode === "weekly") {
      // Last 5 weeks starting from Monday 5 weeks back
      const currentDay = today.getDay();
      const daysToMonday = currentDay === 0 ? 6 : currentDay - 1;
      const thisMonday = new Date(today);
      thisMonday.setDate(today.getDate() - daysToMonday);
      
      // Go back 4 more weeks (total 5 weeks)
      const startMonday = new Date(thisMonday);
      startMonday.setDate(thisMonday.getDate() - 28);
      
      // End on Sunday of current week
      const endSunday = new Date(thisMonday);
      endSunday.setDate(thisMonday.getDate() + 6);
      
      setStartDate(startMonday.toISOString().split('T')[0]);
      setEndDate(endSunday.toISOString().split('T')[0]);
    } else {
      // Last 3 months
      const threeMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 2, 1);
      const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      
      setStartDate(threeMonthsAgo.toISOString().split('T')[0]);
      setEndDate(endOfMonth.toISOString().split('T')[0]);
    }
  }, [viewMode]);

  // Save daily limit to localStorage
  const handleLimitChange = (newLimit: number) => {
    setDailyLimit(newLimit);
    if (typeof window !== 'undefined') {
      localStorage.setItem('dailySpendingLimit', newLimit.toString());
    }
  };

  // Calculate period limit text
  const periodLimitText = useMemo(() => {
    if (viewMode === "weekly") {
      return `Weekly limit: AED ${(dailyLimit * 7).toLocaleString()}`;
    } else {
      return `Monthly limit: ~AED ${(dailyLimit * 30).toLocaleString()}`;
    }
  }, [viewMode, dailyLimit]);

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-title text-[var(--color-text-primary)]">Daily Spending</h1>
        <p className="text-body text-[var(--color-text-secondary)] mt-1">
          Track your daily expenses with a heatmap view
        </p>
      </div>

      {/* Controls Card */}
      <div className="card p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* View Mode Toggle */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              View Mode
            </label>
            <SegmentedControl
              options={[
                { value: "weekly", label: "Weekly" },
                { value: "monthly", label: "Monthly" },
              ]}
              value={viewMode}
              onChange={(value) => setViewMode(value as "weekly" | "monthly")}
              fullWidth
            />
          </div>

          {/* Date From */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              From Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="input"
            />
          </div>

          {/* Date To */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              To Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="input"
            />
          </div>

          {/* Daily Limit */}
          <div>
            <label className="block text-caption text-[var(--color-text-secondary)] mb-2">
              Daily Limit (AED)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={dailyLimit}
                onChange={(e) => handleLimitChange(parseInt(e.target.value, 10) || 0)}
                min={0}
                step={50}
                className="input"
              />
            </div>
          </div>
        </div>

        {/* Period Limit Info */}
        <div className="mt-4 pt-4 border-t border-[var(--color-border-light)]">
          <p className="text-caption text-[var(--color-text-secondary)]">
            <span className="font-medium text-[var(--color-text-primary)]">{periodLimitText}</span>
            {" "} • Days above limit shown in{" "}
            <span className="text-[var(--color-destructive)] font-medium">red</span>, below in{" "}
            <span className="text-[var(--color-success)] font-medium">green</span>
          </p>
        </div>
      </div>

      {/* Heatmap */}
      <DailyHeatmap
        viewMode={viewMode}
        startDate={startDate}
        endDate={endDate}
        dailyLimit={dailyLimit}
      />

      {/* Tips Card */}
      <div className="card p-4 bg-[var(--color-bg-secondary)]">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-[var(--color-primary)] flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-caption text-[var(--color-text-secondary)]">
            <p className="font-medium text-[var(--color-text-primary)] mb-1">Tips</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Click on any cell to see detailed transactions for that day</li>
              <li>Click the copy button to share a summary with emojis</li>
              <li>Excludes: Salary, Incoming Transfers, and Internal Transfers</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
