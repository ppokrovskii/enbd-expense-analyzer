"use client";

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket, JobProgressMessage, JobCompleteMessage, JobFailedMessage, RulesAppliedMessage } from '../hooks/useWebSocket';
import { useToast } from '../hooks/useToast';
import { ToastContainer } from './Toast';

interface JobNotification {
  id: string;
  type: string;
  message: string;
  progress?: number;
  status: 'progress' | 'complete' | 'failed';
  timestamp: number;
}

// Accumulator for rapid-fire rules_applied messages (for "Apply All")
interface RulesAppliedAccumulator {
  totalTransactions: number;
  totalAmount: number;
  ruleCount: number;
  categories: Set<string>;
}

export function NotificationManager({ userId }: { userId: string }) {
  const [notifications, setNotifications] = useState<JobNotification[]>([]);
  const { toasts, showToast, removeToast } = useToast();
  
  // Debounce for consolidating rapid-fire rules_applied messages
  const rulesAccumulator = useRef<RulesAppliedAccumulator>({
    totalTransactions: 0,
    totalAmount: 0,
    ruleCount: 0,
    categories: new Set(),
  });
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, []);

  const handleJobProgress = useCallback((message: JobProgressMessage) => {
    const jobType = message.job_type || 'Processing';
    setNotifications((prev) => {
      const existing = prev.find((n) => n.id === message.job_id);
      if (existing) {
        return prev.map((n) =>
          n.id === message.job_id
            ? {
                ...n,
                message: `${jobType}: ${message.processed}/${message.total} (${message.progress}%)`,
                progress: message.progress,
                timestamp: Date.now(),
              }
            : n
        );
      }
      return [
        ...prev,
        {
          id: message.job_id,
          type: jobType,
          message: `${jobType}: ${message.processed}/${message.total} (${message.progress}%)`,
          progress: message.progress,
          status: 'progress' as const,
          timestamp: Date.now(),
        },
      ];
    });
  }, []);

  const handleJobComplete = useCallback((message: JobCompleteMessage) => {
    // For rule_apply jobs, don't show toast here - rules_applied message handles it
    // This prevents duplicate toasts
    if (message.job_type === 'rule_apply') {
      // Just update the notification state, no toast
      setNotifications((prev) => prev.filter((n) => n.id !== message.job_id));
      return;
    }
    
    // Build a user-friendly message based on result data
    let toastMessage = `${message.job_type || 'Job'} completed`;
    const result = message.result || {};
    
    if ('transactions_changed' in result && typeof result.transactions_changed === 'number') {
      toastMessage = `Recategorized ${result.transactions_changed} transactions`;
    } else if ('transactions_updated' in result && typeof result.transactions_updated === 'number') {
      toastMessage = `Updated ${result.transactions_updated} transactions`;
    }
    
    setNotifications((prev) => {
      const existing = prev.find((n) => n.id === message.job_id);
      if (existing) {
        return prev.map((n) =>
          n.id === message.job_id
            ? {
                ...n,
                message: toastMessage,
                progress: 100,
                status: 'complete' as const,
                timestamp: Date.now(),
              }
            : n
        );
      }
      // Add a new notification if no progress was tracked
      return [
        ...prev,
        {
          id: message.job_id,
          type: message.job_type || 'Job',
          message: toastMessage,
          progress: 100,
          status: 'complete' as const,
          timestamp: Date.now(),
        },
      ];
    });
    
    // Show toast notification
    showToast(toastMessage, 'success');
    
    // Remove notification after 5 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== message.job_id));
    }, 5000);
  }, [showToast]);

  const handleJobFailed = useCallback((message: JobFailedMessage) => {
    const jobType = message.job_type || 'Job';
    const errorMessage = `${jobType} failed: ${message.error}`;
    
    setNotifications((prev) => {
      const existing = prev.find((n) => n.id === message.job_id);
      if (existing) {
        return prev.map((n) =>
          n.id === message.job_id
            ? {
                ...n,
                message: errorMessage,
                status: 'failed' as const,
                timestamp: Date.now(),
              }
            : n
        );
      }
      return [
        ...prev,
        {
          id: message.job_id,
          type: jobType,
          message: errorMessage,
          status: 'failed' as const,
          timestamp: Date.now(),
        },
      ];
    });
    
    // Show toast notification
    showToast(errorMessage, 'error');
    
    // Remove notification after 10 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== message.job_id));
    }, 10000);
  }, [showToast]);

  const handleRulesApplied = useCallback((message: RulesAppliedMessage) => {
    // Remove any progress notification for this job
    setNotifications((prev) => prev.filter((n) => n.id !== message.job_id));
    
    // Accumulate for potential "Apply All" scenario
    rulesAccumulator.current.ruleCount += 1;
    rulesAccumulator.current.totalTransactions += message.transactions_updated;
    rulesAccumulator.current.totalAmount += message.total_amount || 0;
    if (message.by_category) {
      Object.keys(message.by_category).forEach(cat => rulesAccumulator.current.categories.add(cat));
    }
    
    // Clear existing timer
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    
    // Wait 400ms for more messages before showing toast
    debounceTimer.current = setTimeout(() => {
      const acc = rulesAccumulator.current;
      
      let toastMessage: string;
      if (acc.ruleCount === 1) {
        // Single rule - use original message
        toastMessage = message.toast_message;
      } else {
        // Multiple rules - consolidated message
        const amountStr = acc.totalAmount > 0 
          ? ` totaling AED ${acc.totalAmount.toLocaleString('en-AE', { maximumFractionDigits: 0 })}`
          : '';
        toastMessage = `✓ ${acc.ruleCount} rules applied → ${acc.totalTransactions} transactions${amountStr}`;
      }
      
      showToast(toastMessage, acc.totalTransactions > 0 ? 'success' : 'info');
      
      // Reset accumulator
      rulesAccumulator.current = {
        totalTransactions: 0,
        totalAmount: 0,
        ruleCount: 0,
        categories: new Set(),
      };
    }, 400);
  }, [showToast]);

  const { isConnected } = useWebSocket({
    userId,
    onJobProgress: handleJobProgress,
    onJobComplete: handleJobComplete,
    onJobFailed: handleJobFailed,
    onRulesApplied: handleRulesApplied,
  });

  const dismissNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  return (
    <>
      {/* Toast notifications - always rendered */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      
      {/* Job progress notifications */}
      {notifications.length > 0 && (
        <div className="fixed bottom-4 right-4 z-40 space-y-2 max-w-md">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`p-4 rounded-lg shadow-lg border ${
                notification.status === 'complete'
                  ? 'bg-green-900/90 border-green-700'
                  : notification.status === 'failed'
                  ? 'bg-red-900/90 border-red-700'
                  : 'bg-[var(--color-bg-secondary)] border-[var(--color-border)]'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="text-sm font-medium text-[var(--color-text-primary)]">
                  {notification.type}
                </div>
                <button
                  onClick={() => dismissNotification(notification.id)}
                  className="text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors"
                >
                  ✕
                </button>
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] mb-2">
                {notification.message}
              </div>
              {notification.status === 'progress' && notification.progress !== undefined && (
                <div className="w-full bg-[var(--color-bg-tertiary)] rounded-full h-2">
                  <div
                    className="bg-[var(--color-primary)] h-2 rounded-full transition-all duration-300"
                    style={{ width: `${notification.progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

