"use client";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeType?: "increase" | "decrease";
  format?: "currency" | "number" | "percentage";
  gradient?: boolean;
  gradientType?: "income" | "expense" | "primary";
  icon?: React.ReactNode;
}

export default function MetricCard({
  title,
  value,
  change,
  changeType,
  format = "currency",
  gradient = false,
  gradientType = "primary",
  icon,
}: MetricCardProps) {
  const formatValue = (val: string | number): string => {
    if (typeof val === "string") return val;
    
    if (format === "currency") {
      return new Intl.NumberFormat("en-AE", {
        style: "currency",
        currency: "AED",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(val);
    }
    
    if (format === "percentage") {
      return `${val.toFixed(1)}%`;
    }
    
    return val.toLocaleString();
  };

  const getTrendColor = () => {
    if (!change || !changeType) return "";
    if (changeType === "increase") return "text-apple-green";
    return "text-apple-red";
  };

  const getTrendSymbol = () => {
    if (!change || !changeType) return null;
    return changeType === "increase" ? "↑" : "↓";
  };
  
  const getGradientClass = () => {
    if (!gradient) return "";
    switch (gradientType) {
      case "income":
        return "gradient-income";
      case "expense":
        return "gradient-expense";
      default:
        return "gradient-primary";
    }
  };

  return (
    <div
      className={`
        card p-6 transition-all duration-300 hover:shadow-apple-lg hover:scale-[1.02]
        ${gradient ? getGradientClass() : ""}
      `}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <p className={`text-caption font-medium ${gradient ? "text-white/80" : "text-[var(--color-text-secondary)]"}`}>
            {title}
          </p>
        </div>
        {icon && (
          <div className={gradient ? "text-white/60" : "text-[var(--color-text-tertiary)]"}>
            {icon}
          </div>
        )}
      </div>
      
      <div className="space-y-2">
        <p className={`text-3xl font-bold tracking-tight ${gradient ? "text-white" : "text-[var(--color-text-primary)]"}`}>
          {formatValue(value)}
        </p>
        
        {change !== undefined && changeType && (
          <div className="flex items-center gap-1">
            <span className={`text-label font-semibold ${gradient ? "text-white/90" : getTrendColor()}`}>
              {getTrendSymbol()} {Math.abs(change).toFixed(1)}%
            </span>
            <span className={`text-label ${gradient ? "text-white/60" : "text-[var(--color-text-tertiary)]"}`}>
              vs last period
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

