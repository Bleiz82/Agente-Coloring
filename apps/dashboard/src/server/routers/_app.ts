import { createTRPCRouter } from "@/server/trpc";
import { healthRouter } from "./health";
import { alertsRouter } from "./alerts";
import { booksRouter } from "./books";
import { accountsRouter } from "./accounts";
import { salesRouter } from "./sales";
import { policiesRouter } from "./policies";
import { killswitchRouter } from "./killswitch";
import { feedbackRouter } from "./feedback";

export const appRouter = createTRPCRouter({
  health: healthRouter,
  alerts: alertsRouter,
  books: booksRouter,
  accounts: accountsRouter,
  sales: salesRouter,
  policies: policiesRouter,
  killswitch: killswitchRouter,
  feedback: feedbackRouter,
});

export type AppRouter = typeof appRouter;
