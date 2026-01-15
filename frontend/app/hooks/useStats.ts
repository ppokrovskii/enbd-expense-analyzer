"use client";

import { useState, useEffect } from "react";
import { getApiHeaders, API_URL } from "../utils/api";

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

  // Listen for person changes
  useEffect(() => {
    const handlePersonChange = () => {
      setRefreshTrigger(prev => prev + 1);
    };
    
    window.addEventListener('personChanged', handlePersonChange);
    return () => window.removeEventListener('personChanged', handlePersonChange);
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (options.startDate) params.append("start_date", options.startDate);
      if (options.endDate) params.append("end_date", options.endDate);

      const response = await fetch(
        `${API_URL}/api/stats/summary${params.toString() ? `?${params.toString()}` : ""}`,
        { headers: getApiHeaders() }
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.startDate, options.endDate, refreshTrigger]);

  const refresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return { stats, loading, error, refresh };
}

