import { createPinia } from "pinia";
import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import ModulePlaceholderView from "@/views/placeholder/ModulePlaceholderView.vue";

describe("模块占位页", () => {
  it("根据路由元数据展示页面名称和模块", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: "/products",
          component: ModulePlaceholderView,
          meta: {
            title: "商品管理",
            module: "商品运营",
            description: "模拟商品资料管理占位说明。",
          },
        },
        { path: "/dashboard", component: { template: "<div />" } },
      ],
    });
    await router.push("/products");
    await router.isReady();

    const wrapper = mount(ModulePlaceholderView, {
      global: { plugins: [createPinia(), router] },
    });

    expect(wrapper.text()).toContain("商品管理");
    expect(wrapper.text()).toContain("商品运营");
    expect(wrapper.text()).toContain("功能将在对应业务分支实现");
  });
});
