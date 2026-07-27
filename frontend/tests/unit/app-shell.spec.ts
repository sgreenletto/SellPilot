import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppShell from "@/components/layout/AppShell.vue";
import { useAppStore } from "@/stores/app";

describe("AppShell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("移动宽度下通过顶部按钮切换侧边栏", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 600,
    });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    const pinia = createPinia();
    setActivePinia(pinia);
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: "/dashboard",
          component: { template: "<div />" },
          meta: {
            title: "经营看板",
            module: "经营概览",
            description: "跨境店铺运营概览",
          },
        },
        {
          path: "/tasks",
          component: { template: "<div />" },
          meta: {
            title: "任务中心",
            module: "任务",
            description: "任务占位",
          },
        },
      ],
    });
    await router.push("/dashboard");
    await router.isReady();

    const wrapper = mount(AppShell, {
      global: { plugins: [pinia, router] },
    });
    await flushPromises();

    expect(useAppStore().mobileSidebarOpen).toBe(false);
    await wrapper.get('[aria-label="打开导航"]').trigger("click");
    expect(useAppStore().mobileSidebarOpen).toBe(true);
    expect(wrapper.find(".app-shell__sidebar--open").exists()).toBe(true);
  });
});
