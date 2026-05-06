"use client";

import { formatRelativeTime } from "@/lib/format";

interface Policy {
  id: string;
  ruleText: string;
  appliesTo: string[];
  status: string;
  confidenceScore: number;
  proposedAt: string | Date;
}

interface PolicyCardProps {
  policy: Policy;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  PROPOSED: { bg: "rgba(245,158,11,0.15)", text: "#FCD34D" },
  APPROVED: { bg: "rgba(16,185,129,0.15)", text: "#6EE7B7" },
  REJECTED: { bg: "rgba(220,38,38,0.15)", text: "#FCA5A5" },
  RETIRED: { bg: "rgba(113,113,122,0.15)", text: "#A1A1AA" },
};

function confidenceColor(score: number): string {
  if (score < 50) return "#DC2626";
  if (score < 75) return "#F59E0B";
  return "#10B981";
}

export default function PolicyCard({ policy, onApprove, onReject }: PolicyCardProps) {
  const statusStyle = STATUS_STYLES[policy.status] ?? { bg: "rgba(113,113,122,0.15)", text: "#A1A1AA" };

  return (
    <div
      className="rounded-xl border p-5"
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ backgroundColor: statusStyle.bg, color: statusStyle.text }}
        >
          {policy.status}
        </span>
        <span className="text-xs" style={{ color: "#71717A" }}>
          {formatRelativeTime(policy.proposedAt)}
        </span>
      </div>

      {/* Rule text */}
      <p className="mb-3 text-sm" style={{ color: "#F4F4F5" }}>
        {policy.ruleText}
      </p>

      {/* Applies to chips */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {policy.appliesTo.map((tag) => (
          <span
            key={tag}
            className="rounded px-2 py-0.5 text-xs"
            style={{ backgroundColor: "#27272A", color: "#A1A1AA" }}
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Confidence bar */}
      <div className="mb-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs" style={{ color: "#A1A1AA" }}>
            Confidence
          </span>
          <span className="text-xs font-medium" style={{ color: "#F4F4F5" }}>
            {policy.confidenceScore}%
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full" style={{ backgroundColor: "#27272A" }}>
          <div
            className="h-1.5 rounded-full transition-all"
            style={{
              width: `${Math.min(100, Math.max(0, policy.confidenceScore))}%`,
              backgroundColor: confidenceColor(policy.confidenceScore),
            }}
          />
        </div>
      </div>

      {/* Actions */}
      {policy.status === "PROPOSED" && (
        <div className="flex gap-2">
          {onApprove != null && (
            <button
              type="button"
              onClick={() => onApprove(policy.id)}
              className="flex-1 rounded-md px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-80"
              style={{ backgroundColor: "#10B981" }}
            >
              Approve
            </button>
          )}
          {onReject != null && (
            <button
              type="button"
              onClick={() => onReject(policy.id)}
              className="flex-1 rounded-md px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-80"
              style={{ backgroundColor: "#DC2626" }}
            >
              Reject
            </button>
          )}
        </div>
      )}
    </div>
  );
}
