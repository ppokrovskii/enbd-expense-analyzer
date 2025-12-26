"use client";

interface SkeletonLoaderProps {
  variant?: "card" | "table" | "chart" | "text" | "metric";
  count?: number;
  className?: string;
}

export default function SkeletonLoader({
  variant = "card",
  count = 1,
  className = "",
}: SkeletonLoaderProps) {
  if (variant === "metric") {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="card p-6 space-y-3">
            <div className="h-4 w-24 bg-[var(--color-bg-tertiary)] rounded shimmer" />
            <div className="h-9 w-32 bg-[var(--color-bg-tertiary)] rounded shimmer" />
            <div className="h-3 w-20 bg-[var(--color-bg-tertiary)] rounded shimmer" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div className={`space-y-4 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="card p-6 space-y-4">
            <div className="h-5 w-1/3 bg-[var(--color-bg-tertiary)] rounded shimmer" />
            <div className="space-y-2">
              <div className="h-4 w-full bg-[var(--color-bg-tertiary)] rounded shimmer" />
              <div className="h-4 w-5/6 bg-[var(--color-bg-tertiary)] rounded shimmer" />
              <div className="h-4 w-4/6 bg-[var(--color-bg-tertiary)] rounded shimmer" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className="card overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-5 gap-4 p-4 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border-light)]">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-3 bg-[var(--color-bg-tertiary)] rounded shimmer"
            />
          ))}
        </div>
        
        {/* Table rows */}
        {Array.from({ length: count }).map((_, rowIndex) => (
          <div
            key={rowIndex}
            className="grid grid-cols-5 gap-4 p-4 border-b border-[var(--color-border-light)] last:border-0"
          >
            {Array.from({ length: 5 }).map((_, colIndex) => (
              <div
                key={colIndex}
                className="h-4 bg-[var(--color-bg-tertiary)] rounded shimmer"
              />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className="card p-6 space-y-4">
        {/* Chart area */}
        <div className="h-64 bg-[var(--color-bg-tertiary)] rounded-lg shimmer" />
        
        {/* Legend */}
        <div className="flex flex-wrap gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="w-4 h-4 bg-[var(--color-bg-tertiary)] rounded shimmer" />
              <div className="h-3 w-16 bg-[var(--color-bg-tertiary)] rounded shimmer" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (variant === "text") {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="h-4 bg-[var(--color-bg-tertiary)] rounded shimmer"
            style={{ width: `${Math.random() * 30 + 60}%` }}
          />
        ))}
      </div>
    );
  }

  return null;
}

