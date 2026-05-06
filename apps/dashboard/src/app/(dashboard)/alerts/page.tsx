import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import AlertsList from "./AlertsList";

export const metadata: Metadata = { title: "Alerts — ColorForge AI" };

interface AlertData {
  id: string;
  severity: string;
  title: string;
  message: string;
  createdAt: Date;
  acknowledged: boolean;
}

async function getAlerts(): Promise<AlertData[]> {
  try {
    return await prisma.alert.findMany({
      where: { acknowledged: false },
      orderBy: { createdAt: "desc" },
      take: 50,
      select: {
        id: true,
        severity: true,
        title: true,
        message: true,
        createdAt: true,
        acknowledged: true,
      },
    });
  } catch {
    return [];
  }
}

export default async function AlertsPage() {
  const alerts = await getAlerts();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
          Alerts
        </h1>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{
            backgroundColor:
              alerts.length > 0
                ? "rgba(220,38,38,0.15)"
                : "rgba(16,185,129,0.15)",
            color: alerts.length > 0 ? "#FCA5A5" : "#6EE7B7",
          }}
        >
          {alerts.length}
        </span>
      </div>

      {alerts.length > 0 ? (
        <AlertsList alerts={alerts} />
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm font-medium" style={{ color: "#6EE7B7" }}>
            No active alerts — system nominal
          </p>
        </div>
      )}
    </div>
  );
}
