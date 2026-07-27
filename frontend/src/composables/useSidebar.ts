import { storeToRefs } from "pinia";

import { useAppStore } from "@/stores/app";

export function useSidebar() {
  const appStore = useAppStore();
  const { sidebarCollapsed, mobileSidebarOpen } = storeToRefs(appStore);

  return {
    sidebarCollapsed,
    mobileSidebarOpen,
    toggleSidebar: appStore.toggleSidebar,
    toggleMobileSidebar: appStore.toggleMobileSidebar,
    closeMobileSidebar: appStore.closeMobileSidebar,
  };
}
