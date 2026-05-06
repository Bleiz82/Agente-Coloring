import type { Metadata } from "next";
import KPICard from "@/components/ui/KPICard";
import AlertRow from "@/components/ui/AlertRow";
import BookTable from "@/components/ui/BookTable";
import { prisma } from "@/lib/prisma";
import { OverviewBeacon } from "./OverviewClient";

export const metadata: Metadata = { title: "Overview — ColorForge AI" };

interface AlertData {
  id: string;
  severity: string;
  title: string;
  message: string;
  createdAt: Date;
  acknowledged: boolean;
}

interface BookData {
  id: string;
  asin: string | null;
  brandAuthor: string;
  state: string;
  pageCount: number | null;
  createdAt: Date;
  publishedAt: Date | null;
}

interface OverviewData {
  liveBooks: number;
  recentAlerts: AlertData[];
  recentBooks: BookData[];
}

async function getOverviewData(): Promise<OverviewData> {
  try {
    const [liveBooks, recentAlerts, recentBooks] = await Promise.all([
      prisma.book.count({ where: { state: "LIVE" } }),
      prisma.alert.findMany({
        where: { acknowledged: false },
        orderBy: { createdAt: "desc" },
        take: 5,
        select: {
          id: true,
          severity: true,
          title: true,
          message: true,
          createdAt: true,
          acknowledged: true,
        },
      }),
      prisma.book.findMany({
        orderBy: { createdAt: "desc" },
        take: 5,
        select: {
          id: true,
          asin: true,
          brandAuthor: true,
          state: true,
          pageCount: true,
          createdAt: true,
          publishedAt: true,
        },
      }),
    ]);

    return { liveBooks, recentAlerts, recentBooks };
  } catch {
    return {
      liveBooks: 0,
      recentAlerts: [],
      recentBooks: [],
    };
  }
}

export default async function OverviewPage() {
  const { liveBooks, recentAlerts, recentBooks } = await getOverviewData();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
        Overview
      </h1>

      {/* System Status */}
      <OverviewBeacon />

      {/* KPI Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard title="Live Books" value={liveBooks} />
        <KPICard title="Total Royalty (30d)" value="--" />
        <KPICard title="Hit Rate" value="--" />
        <KPICard title="Books Queued" value={0} />
      </div>

      {/* Recent Alerts */}
      <section>
        <h2
          className="mb-3 text-lg font-semibold"
          style={{ color: "#F4F4F5" }}
        >
          Recent Alerts
        </h2>
        {recentAlerts.length > 0 ? (
          <div className="space-y-2">
            {recentAlerts.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={{
                  id: alert.id,
                  severity: alert.severity,
                  title: alert.title,
                  message: alert.message,
                  createdAt: alert.createdAt,
                  acknowledged: alert.acknowledged,
                }}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm" style={{ color: "#71717A" }}>
            No alerts
          </p>
        )}
      </section>

      {/* Recent Books */}
      <section>
        <h2
          className="mb-3 text-lg font-semibold"
          style={{ color: "#F4F4F5" }}
        >
          Recent Books
        </h2>
        {recentBooks.length > 0 ? (
          <BookTable books={recentBooks} />
        ) : (
          <p className="text-sm" style={{ color: "#71717A" }}>
            No books yet
          </p>
        )}
      </section>
    </div>
  );
}
