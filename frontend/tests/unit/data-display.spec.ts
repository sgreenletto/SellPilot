import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlatformModeBadge from "@/components/data-display/PlatformModeBadge.vue";
import RiskIndicator from "@/components/data-display/RiskIndicator.vue";

describe("数据展示组件", () => {
  it("RiskIndicator 显示指定数量的风险条", () => {
    const wrapper = mount(RiskIndicator, { props: { value: 3 } });

    expect(wrapper.findAll(".risk-indicator__bar")).toHaveLength(5);
    expect(wrapper.findAll(".risk-indicator__bar--active")).toHaveLength(3);
    expect(wrapper.text()).toContain("3/5");
  });

  it("PlatformModeBadge 区分 Mock、Real Stub 和断连状态", async () => {
    const wrapper = mount(PlatformModeBadge, {
      props: {
        status: {
          adapter: "mock",
          configured: true,
          reachable: true,
          message: "ready",
          capabilities: ["ping"],
        },
      },
    });

    expect(wrapper.text()).toContain("Mock 模拟模式");

    await wrapper.setProps({
      status: {
        adapter: "real",
        configured: false,
        reachable: false,
        message: "not configured",
        capabilities: [],
      },
    });
    expect(wrapper.text()).toContain("Real Stub 未配置");

    await wrapper.setProps({ status: null, error: "后端未连接" });
    expect(wrapper.text()).toContain("后端未连接");
  });
});
