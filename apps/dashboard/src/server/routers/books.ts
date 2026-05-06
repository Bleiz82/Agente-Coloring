import { z } from "zod";
import { TRPCError } from "@trpc/server";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const booksRouter = createTRPCRouter({
  list: protectedProcedure
    .input(
      z.object({
        accountId: z.string().optional(),
        state: z.string().optional(),
        limit: z.number().int().min(1).max(200).default(50),
        offset: z.number().int().min(0).default(0),
      }),
    )
    .query(async ({ ctx, input }) => {
      const where: Record<string, unknown> = {};
      if (input.accountId !== undefined) {
        where.accountId = input.accountId;
      }
      if (input.state !== undefined) {
        where.state = input.state;
      }

      return ctx.prisma.book.findMany({
        where,
        select: {
          id: true,
          accountId: true,
          nicheId: true,
          state: true,
          asin: true,
          brandAuthor: true,
          pageCount: true,
          createdAt: true,
          publishedAt: true,
          killedAt: true,
        },
        orderBy: { createdAt: "desc" },
        take: input.limit,
        skip: input.offset,
      });
    }),

  get: protectedProcedure
    .input(z.object({ id: z.string().uuid() }))
    .query(async ({ ctx, input }) => {
      const book = await ctx.prisma.book.findUnique({
        where: { id: input.id },
      });
      if (!book) {
        throw new TRPCError({ code: "NOT_FOUND", message: "Book not found" });
      }
      return book;
    }),

  stats: protectedProcedure.query(async ({ ctx }) => {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 86_400_000);

    const [total, byStateRaw, publishedLast30d, killedLast30d] =
      await Promise.all([
        ctx.prisma.book.count(),
        ctx.prisma.book.groupBy({
          by: ["state"],
          _count: { id: true },
        }),
        ctx.prisma.book.count({
          where: {
            state: "LIVE",
            publishedAt: { gte: thirtyDaysAgo },
          },
        }),
        ctx.prisma.book.count({
          where: {
            state: "KILLED",
            killedAt: { gte: thirtyDaysAgo },
          },
        }),
      ]);

    const byState: Record<string, number> = {};
    for (const row of byStateRaw) {
      byState[row.state] = row._count.id;
    }

    return { total, byState, publishedLast30d, killedLast30d };
  }),
});
