"use client";

import { useState, useRef, useEffect } from "react";

interface SegmentedControlOption {
  value: string;
  label: string;
}

interface SegmentedControlProps {
  options: SegmentedControlOption[];
  value: string;
  onChange: (value: string) => void;
  fullWidth?: boolean;
}

export default function SegmentedControl({
  options,
  value,
  onChange,
  fullWidth = false,
}: SegmentedControlProps) {
  const [indicatorStyle, setIndicatorStyle] = useState<{
    left: number;
    width: number;
  }>({ left: 0, width: 0 });
  
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    const activeIndex = options.findIndex((opt) => opt.value === value);
    const activeButton = buttonRefs.current[activeIndex];
    
    if (activeButton && containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const buttonRect = activeButton.getBoundingClientRect();
      
      setIndicatorStyle({
        left: buttonRect.left - containerRect.left,
        width: buttonRect.width,
      });
    }
  }, [value, options]);

  return (
    <div
      ref={containerRef}
      className={`
        relative inline-flex p-1 rounded-lg bg-[var(--color-bg-secondary)]
        ${fullWidth ? "w-full" : ""}
      `}
      role="tablist"
    >
      {/* Animated indicator */}
      <div
        className="absolute top-1 bottom-1 bg-[var(--color-bg-tertiary)] rounded-md shadow-apple-sm transition-all duration-apple-base ease-apple"
        style={{
          left: `${indicatorStyle.left}px`,
          width: `${indicatorStyle.width}px`,
        }}
      />
      
      {/* Options */}
      {options.map((option, index) => (
        <button
          key={option.value}
          ref={(el) => { buttonRefs.current[index] = el; }}
          onClick={() => onChange(option.value)}
          className={`
            relative z-10 px-4 py-1.5 text-caption font-medium rounded-md
            transition-colors duration-apple-fast
            ${fullWidth ? "flex-1" : ""}
            ${
              value === option.value
                ? "text-[var(--color-text-primary)]"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }
            focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-2
          `}
          role="tab"
          aria-selected={value === option.value}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

