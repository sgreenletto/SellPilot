import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppTopbar from "@/components/layout/AppTopbar.vue";
import { navigationEntries } from "@/config/navigation";
import { APP_TITLE, router as applicationRouter } from "@/router";

describe("全局展示治理", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });
  it("不再公开设计系统导航和路由", () => {
    expect(JSON.stringify(navigationEntries)).not.toContain("design-system");
    expect(JSON.stringify(navigationEntries)).not.toContain("设计系统");
    expect(applicationRouter.getRoutes().some((route) => route.path === "/dev/design-system")).toBe(
      false,
    );
  });

  it("公共页头只渲染一个主标题且不渲染路由解释", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: "/tasks",
          component: { template: "<div />" },
          meta: {
            title: "任务中心",
            module: "任务",
            description: "不应展示的内部说明",
          },
        },
      ],
    });
    await router.push("/tasks");
    await router.isReady();
    const wrapper = mount(AppTopbar, {
      global: { plugins: [createPinia(), router] },
    });

    expect(wrapper.findAll("h1")).toHaveLength(1);
    expect(wrapper.get("h1").text()).toBe("任务中心");
    expect(wrapper.text()).not.toContain("不应展示的内部说明");
  });

  it("路由切换后浏览器标题保持为 SellPilot", async () => {
    setActivePinia(createPinia());
    localStorage.clear();
    document.title = "临时页面标题";
    await applicationRouter.push("/tasks");
    expect(document.title).toBe(APP_TITLE);
    expect(document.title).toBe("SellPilot");
    expect(document.title).not.toContain("经营看板");
  });
});
