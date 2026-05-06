import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

export type DateRange = "7d" | "30d" | "90d" | "365d";

interface DashboardState {
  selectedAccounts: string[];
  dateRange: DateRange;
  setSelectedAccounts: (ids: string[]) => void;
  toggleAccount: (id: string) => void;
  setDateRange: (range: DateRange) => void;
}

export const useDashboardStore = create<DashboardState>()(
  immer((set) => ({
    selectedAccounts: [],
    dateRange: "30d",
    setSelectedAccounts: (ids) =>
      set((state) => {
        state.selectedAccounts = ids;
      }),
    toggleAccount: (id) =>
      set((state) => {
        const idx = state.selectedAccounts.indexOf(id);
        if (idx >= 0) state.selectedAccounts.splice(idx, 1);
        else state.selectedAccounts.push(id);
      }),
    setDateRange: (range) =>
      set((state) => {
        state.dateRange = range;
      }),
  })),
);
