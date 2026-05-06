import type { Metadata } from "next";
import { prisma } from "@/lib/prisma";
import PoliciesList from "./PoliciesList";

export const metadata: Metadata = { title: "Policies — ColorForge AI" };

async function getPolicies() {
  try {
    return await prisma.policy.findMany({
      orderBy: { proposedAt: "desc" },
      take: 50,
      select: {
        id: true,
        ruleText: true,
        appliesTo: true,
        status: true,
        confidenceScore: true,
        proposedAt: true,
      },
    });
  } catch {
    return [];
  }
}

function countByStatus(
  policies: { status: string }[],
  status: string,
): number {
  return policies.filter((p) => p.status === status).length;
}

export default async function PoliciesPage() {
  const policies = await getPolicies();

  const proposed = countByStatus(policies, "PROPOSED");
  const approved = countByStatus(policies, "APPROVED");
  const rejected = countByStatus(policies, "REJECTED");

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold" style={{ color: "#F4F4F5" }}>
          Policies
        </h1>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{
            backgroundColor: "rgba(245,158,11,0.15)",
            color: "#FCD34D",
          }}
        >
          {proposed} proposed
        </span>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{
            backgroundColor: "rgba(16,185,129,0.15)",
            color: "#6EE7B7",
          }}
        >
          {approved} approved
        </span>
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{
            backgroundColor: "rgba(220,38,38,0.15)",
            color: "#FCA5A5",
          }}
        >
          {rejected} rejected
        </span>
      </div>

      {policies.length > 0 ? (
        <PoliciesList policies={policies} />
      ) : (
        <div
          className="rounded-xl border p-8 text-center"
          style={{ backgroundColor: "#18181B", borderColor: "#27272A" }}
        >
          <p className="text-sm" style={{ color: "#71717A" }}>
            No policies yet — the performance monitor will propose policies
            based on book performance.
          </p>
        </div>
      )}
    </div>
  );
}
