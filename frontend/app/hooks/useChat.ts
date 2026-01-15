import { useState, useCallback } from 'react';
import { API_URL } from '../utils/api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
}

interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
  context?: any;
}

interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export function useChat(sessionId: string) {
  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [hasContext, setHasContext] = useState(false);
  const [contextInfo, setContextInfo] = useState<any>(null);
  const [lastTokenUsage, setLastTokenUsage] = useState<TokenUsage | null>(null);

  const loadSession = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const response = await fetch(
        `${API_URL}/api/chat/sessions/${sessionId}`,
        {
          headers: {
            'X-User-Id': 'default_user',
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setSession(data);
        setMessages(data.messages || []);
        setHasContext(!!data.context?.transaction_count);
        setContextInfo(data.context);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!sessionId || !message.trim()) return;

      // Add user message optimistically
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      setSending(true);
      try {
        const response = await fetch(
          `${API_URL}/api/chat/sessions/${sessionId}/messages`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-User-Id': 'default_user',
            },
            body: JSON.stringify({ message }),
          }
        );

        if (response.ok) {
          const data = await response.json();
          
          // Track token usage
          if (data.token_usage) {
            setLastTokenUsage(data.token_usage);
          }

          // Update session title if it changed (first message)
          if (data.session_title && session && data.session_title !== session.title) {
            setSession({
              ...session,
              title: data.session_title
            });
          }

          // Reload session to get all messages including assistant response
          await loadSession();
        } else {
          const error = await response.json();
          // Add error message
          setMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              role: 'assistant',
              content: `Error: ${error.detail || 'Failed to send message'}`,
              created_at: new Date().toISOString(),
            },
          ]);
        }
      } catch (error) {
        console.error('Failed to send message:', error);
        // Add error message
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: 'Error: Failed to connect to the server',
            created_at: new Date().toISOString(),
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [sessionId, loadSession]
  );

  const addContext = useCallback(
    async (filters: any) => {
      if (!sessionId) return;

      try {
        const response = await fetch(
          `${API_URL}/api/chat/sessions/${sessionId}/context`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-User-Id': 'default_user',
            },
            body: JSON.stringify(filters),
          }
        );

        if (response.ok) {
          const data = await response.json();
          setHasContext(true);
          setContextInfo(data);
          return data;
        }
      } catch (error) {
        console.error('Failed to add context:', error);
      }
    },
    [sessionId]
  );

  const removeContext = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${API_URL}/api/chat/sessions/${sessionId}/context`,
        {
          method: 'DELETE',
          headers: {
            'X-User-Id': 'default_user',
          },
        }
      );

      if (response.ok) {
        setHasContext(false);
        setContextInfo(null);
      }
    } catch (error) {
      console.error('Failed to remove context:', error);
    }
  }, [sessionId]);

  return {
    session,
    messages,
    loading,
    sending,
    hasContext,
    contextInfo,
    lastTokenUsage,
    loadSession,
    sendMessage,
    addContext,
    removeContext,
  };
}

