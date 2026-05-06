import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { prisma } from "@/lib/prisma";
import { formatCurrency } from "@/lib/format";

interface PageProps {
  params: Promise<{ nicheId: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { nicheId } = await params;
  return { title: `Research: ${nicheId}` };
}

async function getNicheDetail(nicheId: string) {
  try {
    return await prisma.niche.findUnique({
      where: { id: nicheId },
      include: {
        brief: true,
        battleCard: true,
        competitorSnapshots: {
          orderBy: { capturedAt: "desc" },
          take: 10,
        },
      },
    });
  } catch {
    return null;
  }
}

function scoreColor(score: number): string {
  if (score >= 70) return "#10B981";
  if (score >= 50) return "#F59E0B";
  return "#DC2626";
}

export default async function NicheDetailPage({ params }: PageProps) {
  const { nicheId } = await params;
  const niche = await getNicheDetail(nicheId);

  if (!niche) {
    notFound();
  }

  const brief = niche.brief;
  const battleCard = niche.battleCard;
  const competitors = niche.competitorSnapshots;

  // Parse JSON fields safely
  const painPoints = brief?.painPoints as string[] | undefined;
  const styleClassif = brief?.styleClassif as string[] | undefined;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
          {niche.primaryKeyword}
        </h1>
        <div className="mt-2 flex items-center gap-4">
          <span
            className="text-lg font-bold"
            style={{ color: scoreColor(niche.profitabilityScore) }}
          >
            Score: {niche.profitabilityScore.toFixed(0)}
          </span>
          <span className="text-sm" style={{ color: "#71717A" }}>
            {niche.categoryPath.join(" > ")}
          </span>
        </div>
      </div>

      {/* Brief section */}
      {brief && (
        <section
          className="rounded-xl border p-6"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <h2 className="mb-4 text-lg font-semibold" style={{ color: "#F4F4F5" }}>
            Niche Brief
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: "#A1A1AA" }}>
            {brief.visionSummary}
          </p>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Pain Points
              </h4>
              <p className="mt-1 text-sm font-semibold" style={{ color: "#F4F4F5" }}>
                {Array.isArray(painPoints) ? painPoints.length : 0} identified
              </p>
            </div>
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Style Classifications
              </h4>
              <p className="mt-1 text-sm font-semibold" style={{ color: "#F4F4F5" }}>
                {Array.isArray(styleClassif) ? styleClassif.length : 0} styles
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Battle Card section */}
      {battleCard && (
        <section
          className="rounded-xl border p-6"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <h2 className="mb-4 text-lg font-semibold" style={{ color: "#F4F4F5" }}>
            Battle Card
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Avg Price
              </h4>
              <p className="mt-1 text-sm font-semibold" style={{ color: "#F4F4F5" }}>
                {formatCurrency(battleCard.avgPriceCents / 100)}
              </p>
            </div>
            <div>
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Avg Page Count
              </h4>
              <p className="mt-1 text-sm font-semibold" style={{ color: "#F4F4F5" }}>
                {battleCard.avgPageCount}
              </p>
            </div>
            {battleCard.recommendedTrimSize && (
              <div>
                <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                  Recommended Trim Size
                </h4>
                <p className="mt-1 text-sm font-semibold" style={{ color: "#F4F4F5" }}>
                  {battleCard.recommendedTrimSize}
                </p>
              </div>
            )}
            <div className="sm:col-span-2 lg:col-span-3">
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Must-Have Features
              </h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {battleCard.mustHaveFeatures.map((f: string) => (
                  <span
                    key={f}
                    className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                    style={{ backgroundColor: "rgba(16,185,129,0.15)", color: "#10B981" }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Gap Features
              </h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {battleCard.gapFeatures.map((f: string) => (
                  <span
                    key={f}
                    className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                    style={{ backgroundColor: "rgba(245,158,11,0.15)", color: "#F59E0B" }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <h4 className="text-xs font-medium uppercase tracking-wider" style={{ color: "#71717A" }}>
                Top Keyword Patterns
              </h4>
              <div className="mt-2 flex flex-wrap gap-2">
                {battleCard.topKeywordPatterns.map((k: string) => (
                  <span
                    key={k}
                    className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                    style={{ backgroundColor: "rgba(139,92,246,0.15)", color: "#A78BFA" }}
                  >
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Competitor Snapshots */}
      {competitors.length > 0 && (
        <section
          className="overflow-x-auto rounded-xl border"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <div className="p-4 pb-0">
            <h2 className="text-lg font-semibold" style={{ color: "#F4F4F5" }}>
              Competitor Snapshots
            </h2>
          </div>
          <table className="mt-4 w-full text-left text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid #27272A" }}>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  ASIN
                </th>
                <th className="px-4 py-3 font-medium" style={{ color: "#A1A1AA" }}>
                  Title
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  BSR
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Price
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Reviews
                </th>
                <th className="px-4 py-3 text-right font-medium" style={{ color: "#A1A1AA" }}>
                  Rating
                </th>
              </tr>
            </thead>
            <tbody>
              {competitors.map((c: typeof competitors[number]) => (
                <tr
                  key={c.id}
                  className="transition-colors hover:bg-white/5"
                  style={{ borderBottom: "1px solid #27272A" }}
                >
                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "#A1A1AA" }}>
                    {c.asin}
                  </td>
                  <td className="max-w-[200px] truncate px-4 py-3" style={{ color: "#F4F4F5" }}>
                    {c.title}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {c.bsrCurrent?.toLocaleString() ?? "N/A"}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {c.priceCents != null
                      ? formatCurrency(c.priceCents / 100)
                      : "N/A"}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {c.reviewsCount?.toLocaleString() ?? "N/A"}
                  </td>
                  <td className="px-4 py-3 text-right" style={{ color: "#A1A1AA" }}>
                    {c.ratingAvg?.toFixed(1) ?? "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
