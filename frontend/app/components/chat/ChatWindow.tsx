'use client';

import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
  tool_calls?: any[];
}

interface ChatWindowProps {
  messages: Message[];
  loading: boolean;
  onExampleClick?: (example: string) => void;
  hasContext?: boolean;
  onAddContext?: () => void;
}

export default function ChatWindow({ messages, loading, onExampleClick, hasContext, onAddContext }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-6 min-h-full">
        {messages.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            {/* ChatGPT-style simple empty state */}
            <h1 className="text-[32px] font-semibold text-[var(--color-text-primary)] mb-12 tracking-tight">
              Expense Analyzer
            </h1>
            
            {/* Compact context hint (only if no context) */}
            {!hasContext && (
              <button
                onClick={onAddContext}
                className="mb-8 px-4 py-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] border border-[var(--color-border)] rounded-lg text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all"
              >
                <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Add transaction data
              </button>
            )}
            
            {/* Simple example prompts - ChatGPT style */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
              {[
                { icon: "💰", text: "How much did I spend last month?" },
                { icon: "📊", text: "What are my top spending categories?" },
                { icon: "📈", text: "Show me my largest expenses" },
                { icon: "🎯", text: "Analyze my spending patterns" },
              ].map((example, i) => (
                <button
                  key={i}
                  onClick={() => onExampleClick?.(example.text)}
                  className="text-left p-4 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] border border-[var(--color-border)] hover:border-[var(--color-border-medium)] rounded-xl transition-all group"
                >
                  <div className="text-2xl mb-2">{example.icon}</div>
                  <div className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]">
                    {example.text}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages
              .filter((m) => m.role !== 'system' && m.role !== 'tool')
              .map((message, index) => (
                <div
                  key={message.id}
                  className={`flex mb-6 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {/* Message bubble */}
                  <div className="group/message max-w-[80%]">
                    <div
                      className={`${
                        message.role === 'user'
                          ? 'bg-[var(--color-primary)] text-white rounded-[18px] px-4 py-3'
                          : 'text-[var(--color-text-primary)] px-4 py-3'
                      }`}
                    >
                      {/* Message Content with Markdown */}
                      {message.role === 'assistant' ? (
                        <div className="prose-custom">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              // Paragraphs
                              p: ({children, ...props}) => (
                                <p className="text-[15px] text-[var(--color-text-primary)] leading-[1.7] mb-3 last:mb-0">
                                  {children}
                                </p>
                              ),
                              // Bold text
                              strong: ({children, ...props}) => (
                                <strong className="font-semibold text-[var(--color-text-primary)]">
                                  {children}
                                </strong>
                              ),
                              // Emphasis/italic
                              em: ({children, ...props}) => (
                                <em className="italic text-[var(--color-text-primary)]">
                                  {children}
                                </em>
                              ),
                              // Ordered lists
                              ol: ({children, ...props}) => (
                                <ol className="list-decimal list-outside ml-5 mb-3 space-y-1 text-[15px] text-[var(--color-text-primary)] leading-[1.7]">
                                  {children}
                                </ol>
                              ),
                              // Unordered lists
                              ul: ({children, ...props}) => (
                                <ul className="list-disc list-outside ml-5 mb-3 space-y-1 text-[15px] text-[var(--color-text-primary)] leading-[1.7]">
                                  {children}
                                </ul>
                              ),
                              // List items
                              li: ({children, ...props}) => (
                                <li className="pl-1">
                                  {children}
                                </li>
                              ),
                              // Code blocks
                              code: ({inline, children, ...props}: any) => (
                                inline ? (
                                  <code className="bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] px-1.5 py-0.5 rounded text-[13px] font-mono">
                                    {children}
                                  </code>
                                ) : (
                                  <code className="block bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] p-3 rounded-lg text-[13px] font-mono overflow-x-auto mb-3">
                                    {children}
                                  </code>
                                )
                              ),
                              // Headings
                              h1: ({children, ...props}) => (
                                <h1 className="text-[18px] font-semibold text-[var(--color-text-primary)] mb-2 mt-4 first:mt-0">
                                  {children}
                                </h1>
                              ),
                              h2: ({children, ...props}) => (
                                <h2 className="text-[17px] font-semibold text-[var(--color-text-primary)] mb-2 mt-3 first:mt-0">
                                  {children}
                                </h2>
                              ),
                              h3: ({children, ...props}) => (
                                <h3 className="text-[16px] font-semibold text-[var(--color-text-primary)] mb-2 mt-3 first:mt-0">
                                  {children}
                                </h3>
                              ),
                              // Blockquotes
                              blockquote: ({children, ...props}) => (
                                <blockquote className="border-l-3 border-[var(--color-border)] pl-3 italic text-[var(--color-text-secondary)] my-3">
                                  {children}
                                </blockquote>
                              ),
                              // Horizontal rules
                              hr: (props) => (
                                <hr className="border-[var(--color-border)] my-4" />
                              ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="text-[15px] leading-[1.6] whitespace-pre-wrap">
                          {message.content}
                        </p>
                      )}
                      
                      {/* Tool calls indicator */}
                      {message.tool_calls && message.tool_calls.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-[var(--color-border)] text-[12px] text-[var(--color-text-tertiary)] flex items-center gap-1.5">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                          </svg>
                          <span>Used: {message.tool_calls.map((tc: any) => tc.function?.name || 'unknown').join(', ')}</span>
                        </div>
                      )}
                    </div>

                    {/* Copy Button - Only for AI messages */}
                    {message.role === 'assistant' && (
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(message.content);
                            // Optional: Show a toast notification
                            const btn = event?.currentTarget as HTMLButtonElement;
                            if (btn) {
                              const originalText = btn.innerHTML;
                              btn.innerHTML = '<svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>';
                              setTimeout(() => {
                                btn.innerHTML = originalText;
                              }, 2000);
                            }
                          }}
                          className="flex items-center gap-1.5 px-2 py-1 text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)] rounded transition-all"
                          title="Copy message"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                          <span>Copy</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}

            {loading && (
              <div className="flex justify-start mb-6">
                <div className="px-4 py-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-[var(--color-text-tertiary)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-[var(--color-text-tertiary)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-[var(--color-text-tertiary)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>
    </div>
  );
}

