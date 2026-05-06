"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface BookStateChartProps {
  byState: Record<string, number>;
  className?: string;
}

const STATE_COLORS: Record<string, string> = {
  LIVE: "#10B981",
  PUBLISHING: "#0EA5E9",
  KILLED: "#DC2626",
  GENERATING: "#8B5CF6",
  VALIDATING: "#F59E0B",
  LISTING: "#F97316",
  PLANNED: "#71717A",
  PAUSED: "#A1A1AA",
};

function getStateColor(state: string): string {
  return STATE_COLORS[state] ?? "#71717A";
}

export default function BookStateChart({ byState, className }: BookStateChartProps) {
  const entries = Object.entries(byState)
    .map(([state, count]) => ({ state, count }))
    .sort((a, b) => b.count - a.count);

  if (entries.length === 0) {
    return (
      <div
        className={`flex h-[200px] items-center justify-center rounded-xl border ${className ?? ""}`}
        style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
      >
        <p className="text-sm" style={{ color: "#71717A" }}>
          No books yet
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
        Books by State
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={entries} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 80 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272A" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: "#71717A", fontSize: 12 }}
            axisLine={{ stroke: "#27272A" }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="state"
            tick={{ fill: "#A1A1AA", fontSize: 12 }}
            axisLine={{ stroke: "#27272A" }}
            tickLine={false}
            width={75}
          />
          <Tooltip
            contentStyle={{ backgroundColor: "#18181B", border: "1px solid #27272A", borderRadius: "8px" }}
            labelStyle={{ color: "#F4F4F5" }}
            itemStyle={{ color: "#A1A1AA" }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {entries.map((entry) => (
              <Cell key={entry.state} fill={getStateColor(entry.state)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
