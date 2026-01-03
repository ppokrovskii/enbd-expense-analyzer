import type { Metadata } from "next";
import Navigation from "./components/Navigation";
import { NotificationManager } from "./components/NotificationManager";
import "./globals.css";

export const metadata: Metadata = {
  title: "ENBD Expense Analyzer",
  description: "Analyze your ENBD bank transactions with AI-powered categorization",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-[var(--color-bg-secondary)] relative">
        {/* Subtle mesh gradient background */}
        <div className="fixed inset-0 pointer-events-none opacity-40" style={{ background: 'var(--gradient-mesh)' }} />
        
        <div className="relative z-10">
          <Navigation />
          <main className="max-w-container mx-auto px-6 py-8">
            {children}
          </main>
          <footer className="mt-16 py-6 text-center text-caption text-[var(--color-text-tertiary)] border-t border-white/5">
            <p>ENBD Expense Analyzer - Powered by AI</p>
          </footer>
        </div>
        
        {/* WebSocket-powered notification manager */}
        <NotificationManager userId="default_user" />
      </body>
    </html>
  );
}

