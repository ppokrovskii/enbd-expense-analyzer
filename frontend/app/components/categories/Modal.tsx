"use client";

/**
 * Simple modal container for category management
 * TODO: Implement full modal functionality for:
 * - Change Category (with create new option)
 * - AI Recategorize Preview
 * - Edit Rule (with pattern validation)
 * - Delete Category (with confirmation)
 */

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export default function Modal({ isOpen, onClose, title, children }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-[var(--color-bg-primary)] rounded-xl shadow-apple-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-[var(--color-bg-primary)] border-b border-[var(--color-border)] px-6 py-4 flex items-center justify-between">
          <h2 className="text-heading text-[var(--color-text-primary)]">{title}</h2>
          <button
            onClick={onClose}
            className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-apple"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

