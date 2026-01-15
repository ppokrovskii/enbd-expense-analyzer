'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import ChatWindow from '@/app/components/chat/ChatWindow';
import ChatInput from '@/app/components/chat/ChatInput';
import ContextModal from '@/app/components/chat/ContextModal';
import { useChat } from '@/app/hooks/useChat';
import { API_URL } from '@/app/utils/api';

export default function ChatSessionPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = params.id as string;
  const initialMessage = searchParams.get('message');
  
  const {
    session,
    messages,
    loading,
    sending,
    loadSession,
    sendMessage,
    hasContext,
    contextInfo,
  } = useChat(sessionId);

  const [showContextModal, setShowContextModal] = useState(false);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [messageSent, setMessageSent] = useState(false);

  // Load all sessions for sidebar
  useEffect(() => {
    loadAllSessions();
  }, []);

  useEffect(() => {
    if (sessionId) {
      loadSession();
      loadAllSessions(); // Refresh sidebar when session changes
    }
  }, [sessionId]);

  // Send initial message if provided in query params
  useEffect(() => {
    if (initialMessage && !messageSent && !loading && session) {
      setMessageSent(true);
      sendMessage(initialMessage);
      // Clean up URL
      router.replace(`/chat/${sessionId}`);
    }
  }, [initialMessage, messageSent, loading, session, sessionId]);

  const loadAllSessions = async () => {
    try {
      const response = await fetch(`${API_URL}/api/chat/sessions`, {
        headers: { 'X-User-Id': 'default_user' }
      });
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoadingSessions(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    await sendMessage(message);
    // Refresh sidebar after sending message to show updated title/message count
    loadAllSessions();
  };

  const handleExampleClick = (example: string) => {
    handleSendMessage(example);
  };

  const handleDeleteSession = async () => {
    if (!confirm('Delete this chat session?')) return;

    try {
      const response = await fetch(`${API_URL}/api/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': 'default_user' },
      });

      if (response.ok) {
        router.push('/chat');
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleCreateNewChat = async () => {
    // Navigate to /chat empty state
    // A new session will be created when user sends first message
    router.push('/chat');
  };

  const handleDeleteSessionFromSidebar = async (sessionIdToDelete: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm('Delete this chat session?')) return;

    try {
      const response = await fetch(`${API_URL}/api/chat/sessions/${sessionIdToDelete}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': 'default_user' },
      });

      if (response.ok) {
        setSessions(sessions.filter(s => s.id !== sessionIdToDelete));
        
        // If deleting the current session, navigate to chat home
        if (sessionIdToDelete === sessionId) {
          router.push('/chat');
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  // Don't show loading screen when switching between chats - just keep the layout
  // This prevents blinking/flashing
  const showFullLoadingScreen = loading && !session && sessions.length === 0;
  
  if (showFullLoadingScreen) {
    return (
      <div className="flex overflow-hidden fixed left-0 right-0 bottom-0" style={{ top: '64px', backgroundColor: '#000' }}>
        <div className="flex items-center justify-center flex-1">
          <div className="text-white/40">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex overflow-hidden fixed left-0 right-0 bottom-0" style={{ top: '64px', backgroundColor: '#000' }}>
      {/* Left Sidebar - Chat History */}
      <div className="w-64 flex flex-col flex-shrink-0" style={{ backgroundColor: '#000', minWidth: '256px', borderRight: '1px solid rgba(255,255,255,0.1)' }}>
        {/* New Chat Button */}
        <div style={{ padding: '12px', borderBottom: '1px solid rgba(255,255,255,0.1)', flexShrink: 0, backgroundColor: '#000' }}>
          <button
            onClick={handleCreateNewChat}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 16px',
              backgroundColor: '#1a1a1a',
              border: '1px solid rgba(255,255,255,0.2)',
              color: '#fff',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#1a1a1a';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)';
            }}
          >
            <svg style={{ width: '16px', height: '16px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            <span>New Chat</span>
          </button>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {loadingSessions ? (
            <div className="p-4 text-center text-white/40 text-sm">
              Loading chats...
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-white/40 text-sm">
              No chats yet
            </div>
          ) : (
            <div className="py-2">
              {sessions.map((s) => (
                <div key={s.id} className="relative group mx-2 mb-1">
                  <Link
                    href={`/chat/${s.id}`}
                    className={`block px-3 py-2 rounded-lg text-sm transition-all ${
                      s.id === sessionId
                        ? 'bg-white/10 text-white'
                        : 'text-white/70 hover:bg-white/5'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      <span className="truncate flex-1">{s.title}</span>
                    </div>
                  </Link>
                  {/* Delete button - always show */}
                  <button
                    onClick={(e) => handleDeleteSessionFromSidebar(s.id, e)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 transition-opacity bg-black hover:bg-red-500 rounded text-white/40 hover:text-white"
                    title="Delete chat"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Side - Chat Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[var(--color-border)] bg-[var(--color-bg-primary)]">
          <div className="flex items-center justify-between px-6 py-4">
            <h1 className="text-[var(--color-text-primary)] text-lg font-medium truncate flex-1">
              {session?.title || 'New Chat'}
            </h1>

            <div className="flex items-center gap-2">
              {session && (
                <>
                  <button
                    onClick={() => setShowContextModal(true)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] border border-[var(--color-border)] text-[var(--color-text-primary)] text-sm transition-all"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    {hasContext ? `Context (${contextInfo?.transaction_count})` : 'Add Context'}
                  </button>
                  <button
                    onClick={handleDeleteSession}
                    className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:text-[var(--color-destructive)] hover:bg-[var(--color-bg-tertiary)] transition-all"
                    title="Delete chat"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {/* Context Info Banner - shows when context is attached */}
          {hasContext && contextInfo && (
            <div className="bg-[var(--color-bg-tertiary)] border-b border-[var(--color-border)] px-6 py-3">
              <div className="max-w-3xl mx-auto flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <svg className="w-5 h-5 text-[var(--color-primary)]" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">
                      Context: {contextInfo.transaction_count} transactions
                    </span>
                    {contextInfo.transaction_filters?.date_range && (
                      <span className="text-xs text-[var(--color-text-secondary)]">
                        • {new Date(contextInfo.transaction_filters.date_range.from).toLocaleDateString()} 
                        {' '} - {' '}
                        {new Date(contextInfo.transaction_filters.date_range.to).toLocaleDateString()}
                      </span>
                    )}
                    {contextInfo.transaction_filters?.categories?.length > 0 && (
                      <span className="text-xs text-[var(--color-text-secondary)]">
                        • {contextInfo.transaction_filters.categories.length} {contextInfo.transaction_filters.categories.length === 1 ? 'category' : 'categories'}
                      </span>
                    )}
                    {contextInfo.transaction_filters?.accounts?.length > 0 && (
                      <span className="text-xs text-[var(--color-text-secondary)]">
                        • {contextInfo.transaction_filters.accounts.length} {contextInfo.transaction_filters.accounts.length === 1 ? 'account' : 'accounts'}
                      </span>
                    )}
                    {contextInfo.transaction_filters?.merchant && (
                      <span className="text-xs text-[var(--color-text-secondary)]">
                        • Merchant: {contextInfo.transaction_filters.merchant}
                      </span>
                    )}
                  </div>
                  {contextInfo.summary && (
                    <div className="flex items-center gap-4 mt-1 text-xs text-[var(--color-text-tertiary)]">
                      {contextInfo.summary.total_expenses > 0 && (
                        <span>Expenses: AED {contextInfo.summary.total_expenses.toLocaleString()}</span>
                      )}
                      {contextInfo.summary.total_income > 0 && (
                        <span>Income: AED {contextInfo.summary.total_income.toLocaleString()}</span>
                      )}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setShowContextModal(true)}
                  className="flex-shrink-0 text-xs text-[var(--color-primary)] hover:text-[var(--color-primary-hover)] font-medium"
                >
                  Edit
                </button>
              </div>
            </div>
          )}
          
          <ChatWindow 
            messages={messages} 
            loading={sending} 
            onExampleClick={handleExampleClick}
            hasContext={hasContext}
            onAddContext={() => setShowContextModal(true)}
          />
        </div>

        {/* Input */}
        <div className="flex-shrink-0">
          <ChatInput 
            onSend={handleSendMessage} 
            disabled={sending}
            onAttachContext={() => setShowContextModal(true)}
            hasContext={hasContext}
          />
        </div>

        {/* Context Modal */}
        {showContextModal && (
          <ContextModal
            sessionId={sessionId}
            onClose={() => setShowContextModal(false)}
            onContextAdded={() => {
              setShowContextModal(false);
              loadSession();
            }}
            currentContext={contextInfo}
          />
        )}
      </div>
    </div>
  );
}

