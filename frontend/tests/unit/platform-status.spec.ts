import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getPlatformStatus } from "@/api/platform";
import { usePlatformStatus } from "@/composables/usePlatformStatus";
import { useAppStore } from "@/stores/app";

vi.mock("@/api/platform", () => ({
  getPlatformStatus: vi.fn(),
}));

const Harness = defineComponent({
  setup() {
    usePlatformStatus();
    return {};
  },
  template: "<div />",
});

describe("平台状态", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(getPlatformStatus).mockReset();
  });

  it("接口失败时明确显示后端未连接状态", async () => {
    vi.mocked(getPlatformStatus).mockRejectedValue(new Error("offline"));
    mount(Harness);
    await flushPromises();

    const store = useAppStore();
    expect(store.platformStatus).toBeNull();
    expect(store.platformStatusError).toBe("后端未连接");
    expect(store.platformStatusLoading).toBe(false);
  });
});
