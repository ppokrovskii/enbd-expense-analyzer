"use client";

interface SparkleIconProps {
  className?: string;
  size?: number;
}

/**
 * Modern AI sparkle icon similar to GitHub Copilot style.
 * Features a subtle pulse animation on hover.
 */
export default function SparkleIcon({ className = "", size = 16 }: SparkleIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`sparkle-icon ${className}`}
      style={{ display: 'inline-block', verticalAlign: 'middle' }}
    >
      <style jsx>{`
        .sparkle-icon {
          transition: all 0.3s ease;
        }
        .sparkle-icon:hover {
          animation: sparkle-pulse 1.5s ease-in-out infinite;
        }
        @keyframes sparkle-pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.7;
            transform: scale(1.1);
          }
        }
      `}</style>
      
      {/* Main star in center */}
      <path
        d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z"
        fill="currentColor"
        opacity="0.9"
      />
      
      {/* Small star top-right */}
      <path
        d="M18 4L18.5 5.5L20 6L18.5 6.5L18 8L17.5 6.5L16 6L17.5 5.5L18 4Z"
        fill="currentColor"
        opacity="0.7"
      />
      
      {/* Small star bottom-left */}
      <path
        d="M6 16L6.5 17.5L8 18L6.5 18.5L6 20L5.5 18.5L4 18L5.5 17.5L6 16Z"
        fill="currentColor"
        opacity="0.7"
      />
      
      {/* Tiny sparkle top-left */}
      <circle cx="7" cy="5" r="1" fill="currentColor" opacity="0.5" />
      
      {/* Tiny sparkle bottom-right */}
      <circle cx="19" cy="15" r="1" fill="currentColor" opacity="0.5" />
    </svg>
  );
}

