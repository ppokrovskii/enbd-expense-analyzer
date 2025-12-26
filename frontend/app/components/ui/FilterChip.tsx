"use client";

interface FilterChipProps {
  label: string;
  onRemove: () => void;
  color?: "blue" | "green" | "purple" | "orange" | "gray";
}

export default function FilterChip({ label, onRemove, color = "blue" }: FilterChipProps) {
  const colorClasses = {
    blue: "bg-blue-100 text-blue-800 hover:bg-blue-200",
    green: "bg-green-100 text-green-800 hover:bg-green-200",
    purple: "bg-purple-100 text-purple-800 hover:bg-purple-200",
    orange: "bg-orange-100 text-orange-800 hover:bg-orange-200",
    gray: "bg-gray-100 text-gray-800 hover:bg-gray-200",
  };

  return (
    <div
      className={`
        inline-flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-full
        text-caption font-medium transition-apple
        ${colorClasses[color]}
      `}
    >
      <span>{label}</span>
      <button
        onClick={onRemove}
        className="p-0.5 rounded-full hover:bg-black/10 transition-apple focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-current"
        aria-label={`Remove ${label} filter`}
      >
        <svg
          className="w-3.5 h-3.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}

