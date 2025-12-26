"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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
          <Link 
            href="/" 
            className="text-heading font-semibold text-[var(--color-text-primary)] hover:text-[var(--color-primary)] transition-apple"
          >
            Expense Analyzer
          </Link>
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
          </div>
        </div>
      </div>
    </nav>
  );
}

