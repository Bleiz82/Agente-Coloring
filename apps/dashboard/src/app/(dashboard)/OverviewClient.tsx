"use client";

import { SystemBeaconMini } from "@/components/ui/SystemBeaconMini";

export function OverviewBeacon() {
  return (
    <div
      className="flex items-center gap-3 rounded-xl border p-4"
      style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
    >
      <h3 className="text-sm font-medium" style={{ color: "#A1A1AA" }}>
        System Status
      </h3>
      <SystemBeaconMini />
    </div>
  );
}
