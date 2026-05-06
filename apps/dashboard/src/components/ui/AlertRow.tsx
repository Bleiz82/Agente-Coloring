"use client";

import { formatRelativeTime } from "@/lib/format";

interface Alert {
  id: string;
  severity: string;
  title: string;
  message: string;
  createdAt: string | Date;
  acknowledged: boolean;
}

interface AlertRowProps {
  alert: Alert;
  onAcknowledge?: (id: string) => void;
}

const SEVERITY_COLORS: Record<string, { dot: string; label: string; text: string }> = {
  P0: { dot: "#DC2626", label: "P0", text: "#FCA5A5" },
  P1: { dot: "#F97316", label: "P1", text: "#FDBA74" },
  P2: { dot: "#F59E0B", label: "P2", text: "#FCD34D" },
  INFO: { dot: "#0EA5E9", label: "INFO", text: "#7DD3FC" },
};

export default function AlertRow({ alert, onAcknowledge }: AlertRowProps) {
  const severity = SEVERITY_COLORS[alert.severity] ?? { dot: "#0EA5E9", label: "INFO", text: "#7DD3FC" };

  return (
    <div
      className="flex items-center gap-4 rounded-lg border px-4 py-3"
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      {/* Severity badge */}
      <span className="flex items-center gap-1.5 whitespace-nowrap">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: severity.dot }}
        />
        <span
          className="text-xs font-semibold"
          style={{ color: severity.text }}
        >
          {severity.label}
        </span>
      </span>

      {/* Title & message */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium" style={{ color: "#F4F4F5" }}>
          {alert.title}
        </p>
        <p className="truncate text-xs" style={{ color: "#A1A1AA" }}>
          {alert.message}
        </p>
      </div>

      {/* Time */}
      <span className="shrink-0 text-xs" style={{ color: "#71717A" }}>
        {formatRelativeTime(alert.createdAt)}
      </span>

      {/* Acknowledge */}
      {!alert.acknowledged && onAcknowledge != null && (
        <button
          type="button"
          onClick={() => onAcknowledge(alert.id)}
          className="shrink-0 rounded px-2.5 py-1 text-xs font-medium transition-colors hover:bg-white/10"
          style={{ color: "#A1A1AA", border: "1px solid #27272A" }}
        >
          Ack
        </button>
      )}
      {alert.acknowledged && (
        <span className="shrink-0 text-xs" style={{ color: "#52525B" }}>
          Acked
        </span>
      )}
    </div>
  );
}
