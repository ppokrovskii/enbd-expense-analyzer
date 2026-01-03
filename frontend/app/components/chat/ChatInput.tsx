'use client';

import { useState, useRef, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  onAttachContext?: () => void;
  hasContext?: boolean;
}

export default function ChatInput({ onSend, disabled = false, onAttachContext, hasContext = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-4">
      <div className="max-w-3xl mx-auto">
        <div className="relative bg-[var(--color-bg-tertiary)] rounded-lg border border-[var(--color-border)] shadow-xl">
          {/* Attach Context Button */}
          {onAttachContext && (
            <button
              onClick={onAttachContext}
              disabled={disabled}
              className={`absolute left-2 bottom-2 p-2 rounded-md transition-all ${
                hasContext
                  ? 'bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)]'
                  : 'bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] text-[var(--color-text-secondary)] disabled:text-[var(--color-text-tertiary)]'
              } disabled:cursor-not-allowed`}
              title={hasContext ? 'Context attached' : 'Attach transaction data'}
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                />
              </svg>
            </button>
          )}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Send a message..."
            rows={1}
            maxLength={2000}
            className={`w-full bg-transparent text-[var(--color-text-primary)] text-[15px] rounded-lg py-3 focus:outline-none resize-none disabled:opacity-40 disabled:cursor-not-allowed placeholder:text-[var(--color-text-tertiary)] ${
              onAttachContext ? 'pl-14 pr-12' : 'pl-4 pr-12'
            }`}
            style={{ maxHeight: '200px', lineHeight: '1.5' }}
          />
          <button
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            className="absolute right-2 bottom-2 p-2 bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-border)] disabled:bg-transparent disabled:cursor-not-allowed text-[var(--color-text-secondary)] disabled:text-[var(--color-text-tertiary)] rounded-md transition-all"
            title="Send"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
        <p className="text-[11px] text-[var(--color-text-tertiary)] text-center mt-2">
          AI can make mistakes. Check important info.
        </p>
      </div>
    </div>
  );
}

