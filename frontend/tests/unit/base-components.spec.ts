import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";

describe("基础组件", () => {
  it.each(["primary", "secondary", "ghost", "danger"] as const)(
    "SpButton 渲染 %s 变体",
    (variant) => {
      const wrapper = mount(SpButton, {
        props: { variant },
        slots: { default: "按钮" },
      });

      expect(wrapper.classes()).toContain(`sp-button--${variant}`);
    },
  );

  it("SpButton 禁用时不触发点击", async () => {
    const wrapper = mount(SpButton, {
      props: { disabled: true },
      slots: { default: "禁用按钮" },
    });

    await wrapper.trigger("click");

    expect(wrapper.attributes("disabled")).toBeDefined();
    expect(wrapper.emitted("click")).toBeUndefined();
  });

  it("SpCard 渲染 header、default 和 footer 插槽", () => {
    const wrapper = mount(SpCard, {
      slots: {
        header: "卡片标题",
        default: "卡片内容",
        footer: "卡片页脚",
      },
    });

    expect(wrapper.text()).toContain("卡片标题");
    expect(wrapper.text()).toContain("卡片内容");
    expect(wrapper.text()).toContain("卡片页脚");
  });
});
