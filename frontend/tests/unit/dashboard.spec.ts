import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DashboardView from "@/views/dashboard/DashboardView.vue";

describe("经营看板", () => {
  it("渲染漏斗、AI Co-Pilot 与风险事项核心卡片", () => {
    const wrapper = mount(DashboardView);

    expect(wrapper.text()).toContain("商品运营漏斗");
    expect(wrapper.text()).toContain("SellPilot");
    expect(wrapper.text()).toContain("AI Co-Pilot");
    expect(wrapper.text()).toContain("高风险运营事项");
  });

  it("渲染四个漏斗阶段及模拟标签", () => {
    const wrapper = mount(DashboardView);

    for (const label of ["市场商品", "选品候选", "上架草稿", "模拟上架"]) {
      expect(wrapper.text()).toContain(label);
    }
  });

  it("渲染三条稳定 ID 的风险事项数据", () => {
    const wrapper = mount(DashboardView);

    expect(wrapper.findAll(".risk-table tbody tr")).toHaveLength(3);
    expect(wrapper.text()).toContain("无线耳机");
    expect(wrapper.text()).toContain("折叠支架");
    expect(wrapper.text()).toContain("收纳包");
    expect(wrapper.text()).toContain("¥18,600");
  });
});
