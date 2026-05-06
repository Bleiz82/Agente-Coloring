import type { Metadata } from "next";
import Link from "next/link";
import { prisma } from "@/lib/prisma";

export const metadata: Metadata = { title: "Research — ColorForge AI" };

async function getTopNiches() {
  try {
    return await prisma.niche.findMany({
      orderBy: { profitabilityScore: "desc" },
      take: 20,
      select: {
        id: true,
        primaryKeyword: true,
        categoryPath: true,
        profitabilityScore: true,
        battleCard: { select: { id: true } },
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

function scoreBgColor(score: number): string {
  if (score >= 70) return "rgba(16,185,129,0.15)";
  if (score >= 50) return "rgba(245,158,11,0.15)";
  return "rgba(220,38,38,0.15)";
}

export default async function ResearchPage() {
  const niches = await getTopNiches();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
        Research
      </h1>

      {niches.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {niches.map((niche: typeof niches[number]) => (
            <Link
              key={niche.id}
              href={`/research/${niche.id}`}
              className="block rounded-xl border p-5 transition-colors hover:border-zinc-600"
              style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium" style={{ color: "#F4F4F5" }}>
                  {niche.primaryKeyword}
                </h3>
                <span
                  className="shrink-0 rounded-full px-2 py-0.5 text-xs font-bold"
                  style={{
                    color: scoreColor(niche.profitabilityScore),
                    backgroundColor: scoreBgColor(niche.profitabilityScore),
                  }}
                >
                  {niche.profitabilityScore.toFixed(0)}
                </span>
              </div>
              <p className="mt-1 text-xs" style={{ color: "#71717A" }}>
                {niche.categoryPath.join(" > ")}
              </p>
              <div className="mt-3">
                {/* Score bar */}
                <div
                  className="h-1.5 w-full overflow-hidden rounded-full"
                  style={{ backgroundColor: "#27272A" }}
                >
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(niche.profitabilityScore, 100)}%`,
                      backgroundColor: scoreColor(niche.profitabilityScore),
                    }}
                  />
                </div>
              </div>
              <div className="mt-3">
                {niche.battleCard ? (
                  <span
                    className="rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" }}
                  >
                    Battle Card Ready
                  </span>
                ) : (
                  <span
                    className="rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{ backgroundColor: "rgba(113,113,122,0.15)", color: "#71717A" }}
                  >
                    Pending
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm" style={{ color: "#71717A" }}>
            No niche research yet.
          </p>
        </div>
      )}
    </div>
  );
}
