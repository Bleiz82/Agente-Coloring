import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import { formatCurrency } from "@/lib/format";
import KPICard from "@/components/ui/KPICard";
import RoyaltyChart from "@/components/charts/RoyaltyChart";
import BookStateChart from "@/components/charts/BookStateChart";

export const metadata: Metadata = { title: "Performance — ColorForge AI" };

async function getRoyaltySnapshots() {
  try {
    const rows = await prisma.royaltySnapshot.findMany({
      orderBy: { yearMonth: "asc" },
      take: 12,
      select: {
        yearMonth: true,
        totalRoyalty: true,
        totalUnits: true,
      },
    });
    return rows.map((r: { yearMonth: string; totalRoyalty: unknown; totalUnits: number }) => ({
      yearMonth: r.yearMonth,
      totalRoyalty: Number(r.totalRoyalty),
      totalUnits: r.totalUnits,
    }));
  } catch {
    return [];
  }
}

async function getSales30d() {
  try {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const result = await prisma.salesDaily.aggregate({
      where: { date: { gte: thirtyDaysAgo } },
      _sum: { unitsSold: true, royalty: true },
    });
    return {
      units: result._sum.unitsSold ?? 0,
      royalty: Number(result._sum.royalty ?? 0),
    };
  } catch {
    return { units: 0, royalty: 0 };
  }
}

async function getBookStats() {
  try {
    const groups = await prisma.book.groupBy({
      by: ["state"],
      _count: { _all: true },
    });
    const byState: Record<string, number> = {};
    let liveCount = 0;
    let totalNonPlanned = 0;
    for (const g of groups) {
      byState[g.state] = g._count._all;
      if (g.state === "LIVE") liveCount = g._count._all;
      if (g.state !== "PLANNED") totalNonPlanned += g._count._all;
    }
    const hitRate = totalNonPlanned > 0
      ? Math.round((liveCount / totalNonPlanned) * 1000) / 10
      : 0;
    return { byState, liveCount, hitRate };
  } catch {
    return { byState: {}, liveCount: 0, hitRate: 0 };
  }
}

export default async function PerformancePage() {
  const [snapshots, sales, bookStats] = await Promise.all([
    getRoyaltySnapshots(),
    getSales30d(),
    getBookStats(),
  ]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
        Performance
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Royalty (30d)"
          value={formatCurrency(sales.royalty)}
        />
        <KPICard
          title="Units Sold (30d)"
          value={sales.units.toLocaleString()}
        />
        <KPICard
          title="Active Books"
          value={bookStats.liveCount}
        />
        <KPICard
          title="Hit Rate"
          value={`${bookStats.hitRate.toFixed(1)}%`}
        />
      </div>

      <RoyaltyChart data={snapshots} />

      <BookStateChart byState={bookStats.byState} />
    </div>
  );
}
