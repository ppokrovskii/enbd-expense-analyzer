"use client";

import { useState, useEffect, useMemo } from "react";

interface SummaryStats {
  total_income: number;
  total_expenses: number;
  net: number;
  transaction_count: number;
}

interface UseStatsOptions {
  startDate?: string;
  endDate?: string;
}

export function useStats(options: UseStatsOptions = {}) {
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (options.startDate) params.append("start_date", options.startDate);
      if (options.endDate) params.append("end_date", options.endDate);

      const response = await fetch(
        `http://localhost:8000/api/stats/summary${params.toString() ? `?${params.toString()}` : ""}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch stats: ${response.statusText}`);
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load statistics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [options.startDate, options.endDate, refreshTrigger]);

  const refresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return { stats, loading, error, refresh };
}

