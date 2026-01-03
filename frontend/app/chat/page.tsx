'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ChatInput from '@/app/components/chat/ChatInput';

interface ChatSession {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export default function ChatPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const isProcessingRef = useRef(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/chat/sessions', {
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNewChat = async () => {
    // Just navigate to /chat (this page), which already shows the empty state
    // A new session will be created when user sends first message
    router.push('/chat');
  };

  const handleSendMessage = async (message: string, contextFilters?: {
    start_date?: string;
    end_date?: string;
  }) => {
    // Use ref for immediate synchronous check to prevent double-clicks
    if (isProcessingRef.current || sending) return;
    
    isProcessingRef.current = true;
    setSending(true);
    
    try {
      // Create a new chat session
      const sessionResponse = await fetch('http://localhost:8000/api/chat/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify({ title: message.substring(0, 50) }), // Use first 50 chars as title
      });

      if (sessionResponse.ok) {
        const newSession = await sessionResponse.json();
        
        // If context filters provided, attach them before sending message
        if (contextFilters) {
          try {
            await fetch(`http://localhost:8000/api/chat/sessions/${newSession.id}/context`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-User-Id': 'default_user',
              },
              body: JSON.stringify({
                start_date: contextFilters.start_date,
                end_date: contextFilters.end_date,
              }),
            });
          } catch (error) {
            console.error('Failed to attach context:', error);
          }
        }
        
        // Navigate to the new session with the message (it will be sent there)
        router.push(`/chat/${newSession.id}?message=${encodeURIComponent(message)}`);
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setSending(false);
      isProcessingRef.current = false;
    }
  };

  const handleExampleClick = async (message: string, contextFilters?: {
    start_date?: string;
    end_date?: string;
  }) => {
    // Use the same flow as sending a message with optional context
    await handleSendMessage(message, contextFilters);
  };

  const handleAttachContext = async () => {
    // Can't attach context without a chat session
    // User needs to send a message first to create a session
    alert('Please send a message first to start a chat, then you can attach context.');
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm('Delete this chat session?')) return;

    try {
      const response = await fetch(`http://localhost:8000/api/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': 'default_user' },
      });

      if (response.ok) {
        setSessions(sessions.filter(s => s.id !== sessionId));
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-[var(--color-bg-secondary)]">
        <div className="flex items-center justify-center flex-1">
          <div className="text-[var(--color-text-tertiary)]">Loading...</div>
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
          {loading ? (
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
                    className="block px-3 py-2 rounded-lg text-sm transition-all text-white/70 hover:bg-white/5"
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
                    onClick={(e) => handleDeleteSession(s.id, e)}
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

      {/* Right Side - Empty State */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Empty/Welcome State */}
        <div className="flex-1 flex items-center justify-center overflow-y-auto min-h-0">
          <div className="max-w-3xl mx-auto px-4 py-6">
            <div className="flex flex-col items-center justify-center text-center">
              {/* ChatGPT-style simple empty state */}
              <h1 className="text-[32px] font-semibold text-[var(--color-text-primary)] mb-12 tracking-tight">
                Expense Analyzer
              </h1>
              
              {/* Dynamic example prompts with date ranges */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                {(() => {
                  const today = new Date();
                  const currentMonth = today.toLocaleString('en-US', { month: 'long' });
                  const currentYear = today.getFullYear();
                  
                  // Calculate date ranges
                  const getLast30Days = () => {
                    const end = new Date();
                    const start = new Date();
                    start.setDate(start.getDate() - 30);
                    return {
                      start_date: start.toISOString().split('T')[0],
                      end_date: end.toISOString().split('T')[0]
                    };
                  };
                  
                  const getLast90Days = () => {
                    const end = new Date();
                    const start = new Date();
                    start.setDate(start.getDate() - 90);
                    return {
                      start_date: start.toISOString().split('T')[0],
                      end_date: end.toISOString().split('T')[0]
                    };
                  };
                  
                  const getCurrentMonth = () => {
                    const start = new Date(currentYear, today.getMonth(), 1);
                    const end = new Date();
                    return {
                      start_date: start.toISOString().split('T')[0],
                      end_date: end.toISOString().split('T')[0]
                    };
                  };
                  
                  const getCurrentYear = () => {
                    const start = new Date(currentYear, 0, 1);
                    const end = new Date();
                    return {
                      start_date: start.toISOString().split('T')[0],
                      end_date: end.toISOString().split('T')[0]
                    };
                  };
                  
                  const examples = [
                    { 
                      icon: "📅", 
                      text: `Show me my largest expenses in ${currentMonth}`,
                      context: getCurrentMonth()
                    },
                    { 
                      icon: "📊", 
                      text: "What are my top spending categories (last 30 days)?",
                      context: getLast30Days()
                    },
                    { 
                      icon: "📈", 
                      text: "Analyze my spending patterns (last 90 days)",
                      context: getLast90Days()
                    },
                    { 
                      icon: "🎯", 
                      text: `How much did I spend in ${currentYear}?`,
                      context: getCurrentYear()
                    },
                  ];
                  
                  return examples.map((example, i) => (
                    <button
                      key={i}
                      onClick={() => handleExampleClick(example.text, example.context)}
                      disabled={sending}
                      className="text-left p-4 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] border border-[var(--color-border)] hover:border-[var(--color-border-medium)] rounded-xl transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="text-2xl mb-2">{example.icon}</div>
                      <div className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]">
                        {example.text}
                      </div>
                    </button>
                  ));
                })()}
              </div>
            </div>
          </div>
        </div>

        {/* Input Area - Fixed at bottom */}
        <div className="flex-shrink-0">
          <ChatInput 
            onSend={handleSendMessage} 
            disabled={sending}
            onAttachContext={handleAttachContext}
            hasContext={false}
          />
        </div>
      </div>
    </div>
  );
}

