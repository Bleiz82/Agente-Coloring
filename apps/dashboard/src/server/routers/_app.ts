import { createTRPCRouter } from "@/server/trpc";
import { healthRouter } from "./health";
import { alertsRouter } from "./alerts";

export const appRouter = createTRPCRouter({
  health: healthRouter,
  alerts: alertsRouter,
});

export type AppRouter = typeof appRouter;
