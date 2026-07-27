import { onMounted } from "vue";

import { FrontendApiError } from "@/api/http";
import { getPlatformStatus } from "@/api/platform";
import { useAppStore } from "@/stores/app";

export function usePlatformStatus() {
  const appStore = useAppStore();

  async function refreshPlatformStatus(): Promise<void> {
    appStore.platformStatusLoading = true;
    appStore.platformStatusError = null;
    try {
      appStore.platformStatus = await getPlatformStatus();
    } catch (error: unknown) {
      appStore.platformStatus = null;
      appStore.platformStatusError =
        error instanceof FrontendApiError ? error.message : "后端未连接";
    } finally {
      appStore.platformStatusLoading = false;
    }
  }

  onMounted(refreshPlatformStatus);

  return {
    refreshPlatformStatus,
  };
}
