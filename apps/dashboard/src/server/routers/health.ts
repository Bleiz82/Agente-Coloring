import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";
import {
  computeSystemHealth,
  ROI_THRESHOLD_PCT,
} from "@/lib/health-engine";
import type { HealthSnapshot } from "@/lib/health-engine";

export const healthRouter = createTRPCRouter({
  snapshot: protectedProcedure.query(async ({ ctx }) => {
    const [
      killswitchRow,
      p0AlertCount,
      unackedAlertCount,
      pendingPoliciesCount,
      accounts,
    ] = await Promise.all([
      ctx.prisma.systemState.findUnique({
        where: { key: "KILLSWITCH" },
      }),
      ctx.prisma.alert.count({
        where: { acknowledged: false, severity: "P0" },
      }),
      ctx.prisma.alert.count({
        where: { acknowledged: false },
      }),
      ctx.prisma.policy.count({
        where: { status: "PROPOSED" },
      }),
      ctx.prisma.account.findMany({
        where: { active: true },
        select: { id: true },
      }),
    ]);

    // Royalty drop: compare last 30d vs prior 30d from royaltySnapshot
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 86_400_000);
    const sixtyDaysAgo = new Date(now.getTime() - 60 * 86_400_000);

    const [recentSnapshots, priorSnapshots] = await Promise.all([
      ctx.prisma.royaltySnapshot.findMany({
        where: { createdAt: { gte: thirtyDaysAgo } },
      }),
      ctx.prisma.royaltySnapshot.findMany({
        where: {
          createdAt: { gte: sixtyDaysAgo, lt: thirtyDaysAgo },
        },
      }),
    ]);

    const recentTotal = recentSnapshots.reduce(
      (sum: number, s: { totalRoyalty: unknown }) =>
        sum + Number(s.totalRoyalty),
      0,
    );
    const priorTotal = priorSnapshots.reduce(
      (sum: number, s: { totalRoyalty: unknown }) =>
        sum + Number(s.totalRoyalty),
      0,
    );

    let royaltyDropPercent = 0;
    if (priorTotal > 0) {
      royaltyDropPercent =
        ((recentTotal - priorTotal) / priorTotal) * 100;
    }

    // Quota: per-account books published this week, take max
    const weekAgo = new Date(now.getTime() - 7 * 86_400_000);
    let quotaUsedPercent = 0;

    if (accounts.length > 0) {
      const accountQuotas = await Promise.all(
        accounts.map(async (acc: { id: string }) => {
          const count = await ctx.prisma.book.count({
            where: {
              accountId: acc.id,
              state: { in: ["PUBLISHING", "LIVE"] },
              publishedAt: { gte: weekAgo },
            },
          });
          return (count / 10) * 100;
        }),
      );
      quotaUsedPercent = Math.max(...accountQuotas, 0);
    }

    // ROI: last month royalty / estimated cost
    let roiPercent = ROI_THRESHOLD_PCT + 5; // safe default
    if (recentSnapshots.length > 0) {
      // Estimate cost as $2 per book
      const totalBooks = recentSnapshots.reduce(
        (sum: number, s: { bookCount: number }) => sum + s.bookCount,
        0,
      );
      const estimatedCost = totalBooks * 2;
      if (estimatedCost > 0) {
        roiPercent = (recentTotal / estimatedCost) * 100;
      }
    }

    const snapshot: HealthSnapshot = {
      killswitchActive: killswitchRow?.value === "ACTIVE",
      p0AlertCount,
      royaltyDropPercent,
      pendingPoliciesCount,
      quotaUsedPercent,
      roiPercent,
      unackedAlertCount,
    };

    return computeSystemHealth(snapshot);
  }),

  history: protectedProcedure
    .input(
      z.object({
        days: z.number().int().min(1).max(90).default(30),
      }),
    )
    .query(async ({ ctx, input }) => {
      const since = new Date(
        Date.now() - input.days * 86_400_000,
      );

      const snapshots = await ctx.prisma.royaltySnapshot.findMany({
        where: { createdAt: { gte: since } },
        orderBy: { createdAt: "asc" },
      });

      return snapshots.map((s: { yearMonth: string; totalRoyalty: unknown; totalUnits: number; bookCount: number; hitRate: number }) => ({
        yearMonth: s.yearMonth,
        totalRoyalty: Number(s.totalRoyalty),
        totalUnits: s.totalUnits,
        bookCount: s.bookCount,
        hitRate: s.hitRate,
      }));
    }),
});
