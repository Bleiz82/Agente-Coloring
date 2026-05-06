import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import { formatRomeDate } from "@/lib/format";

export const metadata: Metadata = { title: "Niches — ColorForge AI" };

async function getNiches() {
  try {
    return await prisma.niche.findMany({
      orderBy: { scanDate: "desc" },
      take: 50,
      select: {
        id: true,
        primaryKeyword: true,
        categoryPath: true,
        profitabilityScore: true,
        scanDate: true,
        brief: { select: { id: true } },
      },
    });
  } catch {
    return [];
  }
}

function scoreColor(score: number): string {
  if (score >= 70) return "#10B981";
  if (score >= 50) return "#F59E0B";
  return "#DC2626";
}

export default async function NichesPage() {
  const niches = await getNiches();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
          Niches
        </h1>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ backgroundColor: "rgba(139,92,246,0.15)", color: "#A78BFA" }}
        >
          {niches.length}
        </span>
      </div>

      {niches.length > 0 ? (
        <div
          className="overflow-x-auto rounded-xl border"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid #27272A" }}>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Primary Keyword
                </th>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Category
                </th>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Profitability
                </th>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Scan Date
                </th>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Brief
                </th>
              </tr>
            </thead>
            <tbody>
              {niches.map((niche: typeof niches[number]) => (
                <tr
                  key={niche.id}
                  className="transition-colors hover:bg-white/5"
                  style={{ borderBottom: "1px solid #27272A" }}
                >
                  <td className="px-4 py-3 font-medium" style={{ color: "#F4F4F5" }}>
                    {niche.primaryKeyword}
                  </td>
                  <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                    {niche.categoryPath.join(" > ")}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="font-semibold"
                      style={{ color: scoreColor(niche.profitabilityScore) }}
                    >
                      {niche.profitabilityScore.toFixed(0)}
                    </span>
                  </td>
                  <td className="px-4 py-3" style={{ color: "#A1A1AA" }}>
                    {formatRomeDate(niche.scanDate)}
                  </td>
                  <td className="px-4 py-3">
                    {niche.brief ? (
                      <span style={{ color: "#10B981" }}>Ready</span>
                    ) : (
                      <span style={{ color: "#71717A" }}>&mdash;</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm" style={{ color: "#71717A" }}>
            No niches scanned yet &mdash; run the researcher agent.
          </p>
        </div>
      )}
    </div>
  );
}
