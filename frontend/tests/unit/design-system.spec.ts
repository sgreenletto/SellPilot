import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DesignSystemView from "@/views/dev/DesignSystemView.vue";

describe("设计系统展示页", () => {
  it("可以渲染公共组件参考内容", () => {
    const wrapper = mount(DesignSystemView);

    expect(wrapper.text()).toContain("SellPilot 设计系统");
    expect(wrapper.text()).toContain("颜色与字体");
    expect(wrapper.text()).toContain("按钮与状态");
    expect(wrapper.text()).toContain("AI Orb 与图表容器");
  });
});
