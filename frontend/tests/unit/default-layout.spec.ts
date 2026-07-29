import { flushPromises, mount } from "@vue/test-utils";
import { defineComponent, ref } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import DefaultLayout from "@/layouts/DefaultLayout.vue";

describe("DefaultLayout", () => {
  it("keeps opted-in workbench state and in-flight results across route changes", async () => {
    let finishAnalysis: ((value: string) => void) | undefined;
    const Workbench = defineComponent({
      setup() {
        const result = ref("");
        const run = async () => {
          result.value = "正在分析";
          result.value = await new Promise<string>((resolve) => {
            finishAnalysis = resolve;
          });
        };
        return { result, run };
      },
      template:
        '<section data-testid="workbench"><button @click="run">分析</button><span>{{ result }}</span></section>',
    });
    const OtherPage = defineComponent({
      template: '<section data-testid="other-page">其他页面</section>',
    });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: "/workbench",
          name: "workbench",
          component: Workbench,
          meta: {
            title: "测试工作台",
            module: "测试",
            description: "验证跨路由状态恢复",
            keepAlive: true,
          },
        },
        { path: "/other", name: "other", component: OtherPage },
      ],
    });
    await router.push("/workbench");
    await router.isReady();

    const wrapper = mount(DefaultLayout, {
      global: {
        plugins: [router],
        stubs: {
          AppShell: { template: "<main><slot /></main>" },
        },
      },
    });
    await wrapper.get("button").trigger("click");
    expect(wrapper.text()).toContain("正在分析");

    await router.push("/other");
    await flushPromises();
    finishAnalysis?.("分析完成");
    await flushPromises();
    await router.push("/workbench");
    await flushPromises();

    expect(wrapper.text()).toContain("分析完成");
  });
});
