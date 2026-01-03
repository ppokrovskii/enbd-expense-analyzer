"use client";

import React, { useState, useCallback } from 'react';
import { useWebSocket, JobProgressMessage, JobCompleteMessage, JobFailedMessage } from '../hooks/useWebSocket';
import { useToast } from '../hooks/useToast';

interface JobNotification {
  id: string;
  type: string;
  message: string;
  progress?: number;
  status: 'progress' | 'complete' | 'failed';
  timestamp: number;
}

export function NotificationManager({ userId }: { userId: string }) {
  const [notifications, setNotifications] = useState<JobNotification[]>([]);
  const { showToast } = useToast();

  const handleJobProgress = useCallback((message: JobProgressMessage) => {
    setNotifications((prev) => {
      const existing = prev.find((n) => n.id === message.job_id);
      if (existing) {
        return prev.map((n) =>
          n.id === message.job_id
            ? {
                ...n,
                message: `${message.job_type}: ${message.processed}/${message.total} (${message.progress}%)`,
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
          type: message.job_type,
          message: `${message.job_type}: ${message.processed}/${message.total} (${message.progress}%)`,
          progress: message.progress,
          status: 'progress' as const,
          timestamp: Date.now(),
        },
      ];
    });
  }, []);

  const handleJobComplete = useCallback((message: JobCompleteMessage) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === message.job_id
          ? {
              ...n,
              message: `${message.job_type} completed successfully!`,
              progress: 100,
              status: 'complete' as const,
              timestamp: Date.now(),
            }
          : n
      )
    );
    
    // Show toast notification
    showToast(`${message.job_type} completed successfully!`, 'success');
    
    // Remove notification after 5 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== message.job_id));
    }, 5000);
  }, [showToast]);

  const handleJobFailed = useCallback((message: JobFailedMessage) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === message.job_id
          ? {
              ...n,
              message: `${message.job_type} failed: ${message.error}`,
              status: 'failed' as const,
              timestamp: Date.now(),
            }
          : n
      )
    );
    
    // Show toast notification
    showToast(`${message.job_type} failed: ${message.error}`, 'error');
    
    // Remove notification after 10 seconds
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== message.job_id));
    }, 10000);
  }, [showToast]);

  const { isConnected } = useWebSocket({
    userId,
    onJobProgress: handleJobProgress,
    onJobComplete: handleJobComplete,
    onJobFailed: handleJobFailed,
  });

  const dismissNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-md">
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
  );
}

