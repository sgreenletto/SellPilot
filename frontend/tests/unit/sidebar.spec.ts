import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import AppSidebar from "@/components/layout/AppSidebar.vue";

async function mountSidebar(path = "/dashboard") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/dashboard", component: { template: "<div />" } },
      { path: "/market/data", component: { template: "<div />" } },
    ],
  });
  await router.push(path);
  await router.isReady();

  return mount(AppSidebar, {
    global: {
      plugins: [createPinia(), router],
    },
  });
}

describe("侧边导航", () => {
  it("从配置渲染导航并标记当前路由", async () => {
    const wrapper = await mountSidebar();

    expect(wrapper.text()).toContain("经营看板");
    expect(wrapper.text()).toContain("市场与选品");
    expect(wrapper.get('a[href="/dashboard"]').classes()).toContain("sidebar-nav-item--active");
  });

  it("点击分组后展开子导航", async () => {
    const wrapper = await mountSidebar();
    const trigger = wrapper
      .findAll(".sidebar-nav-group__trigger")
      .find((item) => item.text().includes("市场与选品"));

    expect(trigger).toBeDefined();
    expect(trigger?.attributes("aria-expanded")).toBe("false");
    await trigger?.trigger("click");
    expect(trigger?.attributes("aria-expanded")).toBe("true");
    expect(wrapper.text()).toContain("智能选品");
  });
});
