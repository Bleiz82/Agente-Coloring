"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { CHART_COLORS } from "@/lib/colors";
import { formatCurrency } from "@/lib/format";

interface RoyaltyDatum {
  yearMonth: string;
  totalRoyalty: number;
  totalUnits: number;
}

interface RoyaltyChartProps {
  data: RoyaltyDatum[];
  className?: string;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; dataKey: string }[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  const royalty = payload[0]?.value ?? 0;
  // Find matching datum from payload for units
  const entry = payload[0] as unknown as { payload: RoyaltyDatum };
  const units = entry.payload.totalUnits;
  return (
    <div
      className="rounded-lg border px-3 py-2 text-sm shadow-lg"
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      <p className="font-medium" style={{ color: "#F4F4F5" }}>
        {label}
      </p>
      <p style={{ color: CHART_COLORS.royaltyActual }}>
        Royalty: {formatCurrency(royalty)}
      </p>
      <p style={{ color: "#A1A1AA" }}>Units: {units}</p>
    </div>
  );
}

export default function RoyaltyChart({ data, className }: RoyaltyChartProps) {
  if (data.length === 0) {
    return (
      <div
        className={`flex h-[300px] items-center justify-center rounded-xl border ${className ?? ""}`}
        style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
      >
        <p className="text-sm" style={{ color: "#71717A" }}>
          No royalty data yet
        </p>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border p-4 ${className ?? ""}`}
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      <h3 className="mb-4 text-sm font-medium" style={{ color: "#A1A1AA" }}>
        Monthly Royalty
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <defs>
            <linearGradient id="royaltyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.royaltyActual} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS.royaltyActual} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
          <XAxis
            dataKey="yearMonth"
            tick={{ fill: "#71717A", fontSize: 12 }}
            axisLine={{ stroke: "#27272A" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#71717A", fontSize: 12 }}
            axisLine={{ stroke: "#27272A" }}
            tickLine={false}
            tickFormatter={(v: number) => formatCurrency(v)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="totalRoyalty"
            stroke={CHART_COLORS.royaltyActual}
            strokeWidth={2}
            fill="url(#royaltyGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
