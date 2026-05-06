"use client";

interface KPICardProps {
  title: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  className?: string;
}

export default function KPICard({
  title,
  value,
  delta,
  deltaLabel,
  icon,
  loading,
  className,
}: KPICardProps) {
  if (loading) {
    return (
      <div
        className={`rounded-xl border p-5 ${className ?? ""}`}
        style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
      >
        <div className="mb-3 h-4 w-24 animate-pulse rounded" style={{ backgroundColor: "#27272A" }} />
        <div className="mb-2 h-8 w-32 animate-pulse rounded" style={{ backgroundColor: "#27272A" }} />
        <div className="h-4 w-20 animate-pulse rounded" style={{ backgroundColor: "#27272A" }} />
      </div>
    );
  }

  const deltaPositive = delta != null && delta >= 0;
  const deltaColor = deltaPositive ? "#10B981" : "#DC2626";
  const deltaArrow = deltaPositive ? "↑" : "↓";

  return (
    <div
      className={`rounded-xl border p-5 ${className ?? ""}`}
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium" style={{ color: "#A1A1AA" }}>
          {title}
        </p>
        {icon != null && (
          <span style={{ color: "#A1A1AA" }}>{icon}</span>
        )}
      </div>
      <p
        className="mt-2 text-3xl font-bold tracking-tight"
        style={{ color: "#F4F4F5" }}
      >
        {value}
      </p>
      {delta != null && (
        <p className="mt-2 text-sm font-medium" style={{ color: deltaColor }}>
          {deltaArrow} {Math.abs(delta).toFixed(1)}%
          {deltaLabel != null && (
            <span className="ml-1 font-normal" style={{ color: "#A1A1AA" }}>
              {deltaLabel}
            </span>
          )}
        </p>
      )}
    </div>
  );
}
