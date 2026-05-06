import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const salesRouter = createTRPCRouter({
  daily: protectedProcedure
    .input(
      z.object({
        accountId: z.string().optional(),
        bookId: z.string().optional(),
        days: z.number().int().min(1).max(365).default(30),
      }),
    )
    .query(async ({ ctx, input }) => {
      const since = new Date(Date.now() - input.days * 86_400_000);

      const where: Record<string, unknown> = {
        date: { gte: since },
      };
      if (input.accountId !== undefined) {
        where.accountId = input.accountId;
      }
      if (input.bookId !== undefined) {
        where.bookId = input.bookId;
      }

      const records = await ctx.prisma.salesDaily.findMany({
        where,
        select: {
          id: true,
          bookId: true,
          accountId: true,
          date: true,
          unitsSold: true,
          royalty: true,
          kenpRead: true,
          refunds: true,
          marketplace: true,
        },
        orderBy: { date: "desc" },
      });

      return records.map((r: { id: string; bookId: string; accountId: string; date: Date; unitsSold: number; royalty: unknown; kenpRead: number; refunds: number; marketplace: string }) => ({
        id: r.id,
        bookId: r.bookId,
        accountId: r.accountId,
        date: r.date,
        unitsSold: r.unitsSold,
        royalty: Number(r.royalty),
        kenpRead: r.kenpRead,
        refunds: r.refunds,
        marketplace: r.marketplace,
      }));
    }),

  summary: protectedProcedure
    .input(
      z.object({
        days: z.number().int().min(1).max(365).default(30),
      }),
    )
    .query(async ({ ctx, input }) => {
      const since = new Date(Date.now() - input.days * 86_400_000);

      const agg = await ctx.prisma.salesDaily.aggregate({
        where: { date: { gte: since } },
        _sum: {
          unitsSold: true,
          royalty: true,
          kenpRead: true,
          refunds: true,
        },
      });

      const totalUnits = agg._sum.unitsSold ?? 0;
      const totalRoyalty = Number(agg._sum.royalty ?? 0);
      const totalKenpRead = agg._sum.kenpRead ?? 0;
      const totalRefunds = agg._sum.refunds ?? 0;
      const averageDailyRoyalty =
        input.days > 0 ? totalRoyalty / input.days : 0;

      return {
        totalUnits,
        totalRoyalty,
        totalKenpRead,
        totalRefunds,
        averageDailyRoyalty,
      };
    }),
});
