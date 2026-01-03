"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import PersonSwitcher from "./PersonSwitcher";

export default function Navigation() {
  const pathname = usePathname();
  
  const isActive = (path: string) => {
    if (path === "/" && pathname === "/") return true;
    if (path !== "/" && pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <nav className="bg-[var(--color-bg-primary)]/95 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
      <div className="max-w-container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-4">
            <Link 
              href="/" 
              className="text-heading font-semibold text-[var(--color-text-primary)] hover:text-[var(--color-primary)] transition-apple"
            >
              Expense Analyzer
            </Link>
            <PersonSwitcher />
          </div>
          <div className="flex items-center gap-1">
            <Link 
              href="/" 
              className={`
                px-4 py-2 rounded-lg text-body font-medium transition-apple
                ${isActive("/") && pathname === "/"
                  ? "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]/50"
                }
              `}
            >
              Upload
            </Link>
            <Link 
              href="/transactions" 
              className={`
                px-4 py-2 rounded-lg text-body font-medium transition-apple
                ${isActive("/transactions")
                  ? "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]/50"
                }
              `}
            >
              Transactions
            </Link>
            <Link 
              href="/categories" 
              className={`
                px-4 py-2 rounded-lg text-body font-medium transition-apple
                ${isActive("/categories")
                  ? "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]/50"
                }
              `}
            >
              Categories
            </Link>
            <Link 
              href="/chat" 
              className={`
                px-4 py-2 rounded-lg text-body font-medium transition-apple flex items-center
                ${isActive("/chat")
                  ? "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]/50"
                }
              `}
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
              AI Chat
            </Link>
            <Link 
              href="/settings" 
              className={`
                px-4 py-2 rounded-lg text-body font-medium transition-apple flex items-center
                ${isActive("/settings")
                  ? "bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]/50"
                }
              `}
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              Settings
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

