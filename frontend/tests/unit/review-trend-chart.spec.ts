import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReviewTrendChart from "@/components/charts/ReviewTrendChart.vue";

const chart = vi.hoisted(() => ({
  setOption: vi.fn(),
  resize: vi.fn(),
  dispose: vi.fn(),
}));
vi.mock("echarts", () => ({ init: vi.fn(() => chart) }));

describe("ReviewTrendChart", () => {
  beforeEach(() => vi.clearAllMocks());

  it("updates and disposes its chart instance", async () => {
    const wrapper = mount(ReviewTrendChart, {
      props: {
        points: [
          {
            site: "sg",
            month: "2026-01",
            review_count: 10,
            negative_count: 2,
            average_rating: "4.2",
            topic_counts: {},
          },
        ],
      },
    });
    expect(chart.setOption).toHaveBeenCalled();
    await wrapper.setProps({ points: [] });
    expect(chart.setOption).toHaveBeenCalledTimes(2);
    wrapper.unmount();
    expect(chart.dispose).toHaveBeenCalledOnce();
  });
});
