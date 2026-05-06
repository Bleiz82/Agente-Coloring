import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import { formatCurrency } from "@/lib/format";

export const metadata: Metadata = { title: "Ledger — ColorForge AI" };

interface SnapshotRow {
  yearMonth: string;
  totalRoyalty: unknown;
  totalUnits: number;
  bookCount: number;
  hitRate: number;
}

async function getSnapshots(): Promise<SnapshotRow[]> {
  try {
    return await prisma.royaltySnapshot.findMany({
      orderBy: { yearMonth: "desc" },
      take: 24,
      select: {
        yearMonth: true,
        totalRoyalty: true,
        totalUnits: true,
        bookCount: true,
        hitRate: true,
      },
    });
  } catch {
    return [];
  }
}

async function getAiCost30d() {
  try {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const result = await prisma.agentRun.aggregate({
      where: { startedAt: { gte: thirtyDaysAgo } },
      _sum: { costUsd: true },
      _count: { _all: true },
    });
    return {
      totalCost: Number(result._sum.costUsd ?? 0),
      runCount: result._count._all,
    };
  } catch {
    return { totalCost: 0, runCount: 0 };
  }
}

async function getRoyalty30d() {
  try {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const result = await prisma.salesDaily.aggregate({
      where: { date: { gte: thirtyDaysAgo } },
      _sum: { royalty: true },
    });
    return Number(result._sum.royalty ?? 0);
  } catch {
    return 0;
  }
}

export default async function LedgerPage() {
  const [snapshots, aiCost, royalty30d] = await Promise.all([
    getSnapshots(),
    getAiCost30d(),
    getRoyalty30d(),
  ]);

  const totals = snapshots.reduce(
    (acc: { royalty: number; units: number; books: number }, s: SnapshotRow) => ({
      royalty: acc.royalty + Number(s.totalRoyalty),
      units: acc.units + s.totalUnits,
      books: acc.books + s.bookCount,
    }),
    { royalty: 0, units: 0, books: 0 },
  );

  const netEstimate = royalty30d - aiCost.totalCost;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
        Ledger
      </h1>

      {/* Cost summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div
          className="rounded-xl border p-5"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm font-medium" style={{ color: "#A1A1AA" }}>
            Total AI Cost (30d)
          </p>
          <p className="mt-2 text-2xl font-bold" style={{ color: "#F4F4F5" }}>
            {formatCurrency(aiCost.totalCost, "USD")}
          </p>
          <p className="mt-1 text-xs" style={{ color: "#71717A" }}>
            {aiCost.runCount} agent runs
          </p>
        </div>
        <div
          className="rounded-xl border p-5"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm font-medium" style={{ color: "#A1A1AA" }}>
            Royalty (30d)
          </p>
          <p className="mt-2 text-2xl font-bold" style={{ color: "#F4F4F5" }}>
            {formatCurrency(royalty30d)}
          </p>
        </div>
        <div
          className="rounded-xl border p-5"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm font-medium" style={{ color: "#A1A1AA" }}>
            Net Estimate (30d)
          </p>
          <p
            className="mt-2 text-2xl font-bold"
            style={{ color: netEstimate >= 0 ? "#10B981" : "#DC2626" }}
          >
            {formatCurrency(netEstimate)}
          </p>
          <p className="mt-1 text-xs" style={{ color: "#71717A" }}>
            royalty - AI cost (rough margin)
          </p>
        </div>
      </div>

      {/* Royalty snapshots table */}
      {snapshots.length > 0 ? (
        <div
          className="overflow-x-auto rounded-xl border"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid #27272A" }}>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Month
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Total Royalty (EUR)
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Units
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Books
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Hit Rate
                </th>
              </tr>
            </thead>
            <tbody>
              {snapshots.map((s: SnapshotRow) => (
                <tr
                  key={s.yearMonth}
                  className="transition-colors hover:bg-white/5"
                  style={{ borderBottom: "1px solid #27272A" }}
                >
                  <td className="px-4 py-3 font-medium" style={{ color: "#F4F4F5" }}>
                    {s.yearMonth}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#FBBF24" }}>
                    {formatCurrency(Number(s.totalRoyalty))}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {s.totalUnits.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {s.bookCount}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {s.hitRate.toFixed(1)}%
                  </td>
                </tr>
              ))}
              {/* Footer totals */}
              <tr style={{ borderTop: "2px solid #3F3F46" }}>
                <td className="px-4 py-3 font-bold" style={{ color: "#F4F4F5" }}>
                  Total
                </td>
                <td className="px-4 py-3 text-right font-bold" style={{ color: "#FBBF24" }}>
                  {formatCurrency(totals.royalty)}
                </td>
                <td className="px-4 py-3 text-right font-bold" style={{ color: "#F4F4F5" }}>
                  {totals.units.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right font-bold" style={{ color: "#F4F4F5" }}>
                  {totals.books}
                </td>
                <td className="px-4 py-3 text-right" style={{ color: "#71717A" }}>
                  &mdash;
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm" style={{ color: "#71717A" }}>
            No royalty snapshots yet.
          </p>
        </div>
      )}
    </div>
  );
}
