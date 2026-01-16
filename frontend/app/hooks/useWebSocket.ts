"use client";

import { useEffect, useRef, useState, useCallback } from 'react';

export interface JobProgressMessage {
  type: 'job_progress';
  job_id: string;
  job_type: string;
  progress: number;
  processed: number;
  total: number;
}

export interface JobCompleteMessage {
  type: 'job_complete';
  job_id: string;
  job_type: string;
  result: Record<string, unknown>;
}

export interface JobFailedMessage {
  type: 'job_failed';
  job_id: string;
  job_type: string;
  error: string;
}

export interface RulesAppliedMessage {
  type: 'rules_applied';
  job_id: string;
  transactions_updated: number;
  total_amount: number;
  by_category: Record<string, number>;
  toast_message: string;
}

export type WebSocketMessage = JobProgressMessage | JobCompleteMessage | JobFailedMessage | RulesAppliedMessage;

interface UseWebSocketOptions {
  userId: string;
  onMessage?: (message: WebSocketMessage) => void;
  onJobProgress?: (message: JobProgressMessage) => void;
  onJobComplete?: (message: JobCompleteMessage) => void;
  onJobFailed?: (message: JobFailedMessage) => void;
  onRulesApplied?: (message: RulesAppliedMessage) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
}

export function useWebSocket({
  userId,
  onMessage,
  onJobProgress,
  onJobComplete,
  onJobFailed,
  onRulesApplied,
  autoReconnect = true,
  reconnectInterval = 3000,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const port = process.env.NEXT_PUBLIC_WS_PORT || '8000';
      // Backend expects user_id as query parameter: /ws?user_id=xxx
      const wsUrl = `${protocol}//${host}:${port}/ws?user_id=${encodeURIComponent(userId)}`;
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        
        // Clear any pending reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
          
          // Call generic message handler
          onMessage?.(message);
          
          // Call specific handlers based on message type
          switch (message.type) {
            case 'job_progress':
              onJobProgress?.(message);
              break;
            case 'job_complete':
              onJobComplete?.(message);
              break;
            case 'job_failed':
              onJobFailed?.(message);
              break;
            case 'rules_applied':
              onRulesApplied?.(message);
              break;
          }
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };
      
      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        setIsConnected(false);
        wsRef.current = null;
        
        // Attempt to reconnect if enabled and not manually closed
        if (autoReconnect && shouldReconnectRef.current) {
          console.log(`[WebSocket] Reconnecting in ${reconnectInterval}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      setIsConnected(false);
    }
  }, [userId, autoReconnect, reconnectInterval, onMessage, onJobProgress, onJobComplete, onJobFailed, onRulesApplied]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('[WebSocket] Cannot send message - not connected');
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect: connect,
    disconnect,
  };
}

