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
      { path: "/:pathMatch(.*)*", component: { template: "<div />" } },
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

  it("菜单滚动区和底部用户区分离，并为导航文字提供截断容器", async () => {
    const wrapper = await mountSidebar();
    const sidebar = wrapper.get(".app-sidebar");
    const navigation = wrapper.get(".app-sidebar__nav");
    const operator = wrapper.get(".app-sidebar__operator");

    expect(sidebar.element.children).toHaveLength(3);
    expect(navigation.element.nextElementSibling).toBe(operator.element);
    expect(wrapper.findAll(".sidebar-nav-item__label").length).toBeGreaterThan(0);
    expect(wrapper.findAll(".sidebar-nav-group__label").length).toBeGreaterThan(0);
  });

  it("折叠状态使用专用侧边栏宽度类且隐藏完整导航文字", async () => {
    const wrapper = await mountSidebar();

    await wrapper.get('[aria-label="收起侧边栏"]').trigger("click");

    expect(wrapper.get(".app-sidebar").classes()).toContain("app-sidebar--collapsed");
    expect(
      wrapper.find(".app-sidebar__nav > .sidebar-nav-item .sidebar-nav-item__label").exists(),
    ).toBe(false);
    expect(wrapper.find(".sidebar-nav-group__label").exists()).toBe(false);
    for (const children of wrapper.findAll(".sidebar-nav-group__children")) {
      expect(children.isVisible()).toBe(false);
    }
  });
});
