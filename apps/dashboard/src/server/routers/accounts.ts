import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const accountsRouter = createTRPCRouter({
  list: protectedProcedure.query(async ({ ctx }) => {
    return ctx.prisma.account.findMany({
      select: {
        id: true,
        label: true,
        brandAuthors: true,
        nicheSpecialization: true,
        active: true,
        dailyQuota: true,
        warmingStartedAt: true,
        createdAt: true,
      },
    });
  }),

  stats: protectedProcedure.query(async ({ ctx }) => {
    const [accounts, totalActive, totalBooks, booksByAccount] =
      await Promise.all([
        ctx.prisma.account.findMany({
          select: { id: true, label: true },
        }),
        ctx.prisma.account.count({ where: { active: true } }),
        ctx.prisma.book.count(),
        ctx.prisma.book.groupBy({
          by: ["accountId"],
          where: { state: { in: ["LIVE", "PUBLISHING"] } },
          _count: { id: true },
        }),
      ]);

    const countMap = new Map<string, number>();
    for (const row of booksByAccount) {
      countMap.set(row.accountId, row._count.id);
    }

    const booksPerAccount = accounts.map((acc: { id: string; label: string }) => ({
      accountId: acc.id,
      label: acc.label,
      count: countMap.get(acc.id) ?? 0,
    }));

    return { totalActive, totalBooks, booksPerAccount };
  }),
});
