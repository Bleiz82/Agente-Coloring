import { z } from "zod";
import { createTRPCRouter, protectedProcedure } from "@/server/trpc";

export const killswitchRouter = createTRPCRouter({
  status: protectedProcedure.query(async ({ ctx }) => {
    const row = await ctx.prisma.systemState.findUnique({
      where: { key: "KILLSWITCH" },
    });

    return {
      active: row?.value === "ACTIVE",
      activatedAt: row?.activatedAt ?? null,
      activatedBy: row?.activatedBy ?? null,
      reason: row?.reason ?? null,
    };
  }),

  activate: protectedProcedure
    .input(z.object({ reason: z.string().min(3).max(500) }))
    .mutation(async ({ ctx, input }) => {
      const now = new Date();
      const activatedBy = ctx.session.userId ?? "owner";

      const row = await ctx.prisma.systemState.upsert({
        where: { key: "KILLSWITCH" },
        create: {
          key: "KILLSWITCH",
          value: "ACTIVE",
          reason: input.reason,
          activatedAt: now,
          activatedBy,
        },
        update: {
          value: "ACTIVE",
          reason: input.reason,
          activatedAt: now,
          activatedBy,
        },
      });

      return {
        active: true as const,
        activatedAt: row.activatedAt,
        activatedBy: row.activatedBy,
        reason: row.reason,
      };
    }),

  deactivate: protectedProcedure.mutation(async ({ ctx }) => {
    const activatedBy = ctx.session.userId ?? "owner";

    await ctx.prisma.systemState.upsert({
      where: { key: "KILLSWITCH" },
      create: {
        key: "KILLSWITCH",
        value: "INACTIVE",
        reason: "Manual deactivation",
        activatedAt: new Date(),
        activatedBy,
      },
      update: {
        value: "INACTIVE",
        reason: "Manual deactivation",
        activatedBy,
        activatedAt: new Date(),
      },
    });

    return { active: false as const };
  }),
});
