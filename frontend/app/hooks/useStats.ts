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

  useEffect(() => {
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

    fetchStats();
  }, [options.startDate, options.endDate]);

  return { stats, loading, error };
}

