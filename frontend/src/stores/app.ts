import { defineStore } from "pinia";

import type { PlatformPingData } from "@/api/types";

export const useAppStore = defineStore("app", {
  state: () => ({
    sidebarCollapsed: false,
    mobileSidebarOpen: false,
    currentPageTitle: "经营看板",
    platformStatus: null as PlatformPingData | null,
    platformStatusLoading: false,
    platformStatusError: null as string | null,
  }),
  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
    },
    toggleMobileSidebar() {
      this.mobileSidebarOpen = !this.mobileSidebarOpen;
    },
    closeMobileSidebar() {
      this.mobileSidebarOpen = false;
    },
    setPageTitle(title: string) {
      this.currentPageTitle = title;
    },
  },
});
