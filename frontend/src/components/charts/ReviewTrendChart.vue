<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import type { TrendPoint } from "@/types/review-analysis";

const props = defineProps<{ points: TrendPoint[] }>();
const root = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let observer: ResizeObserver | null = null;

function render(): void {
  if (!root.value) return;
  chart ??= echarts.init(root.value);
  chart.setOption({
    animation: false,
    tooltip: { trigger: "axis" },
    legend: { data: ["评论数", "负面评论"] },
    grid: { left: 42, right: 18, top: 36, bottom: 32 },
    xAxis: { type: "category", data: props.points.map((item) => `${item.month} · ${item.site}`) },
    yAxis: { type: "value", minInterval: 1 },
    series: [
      {
        name: "评论数",
        type: "line",
        smooth: true,
        data: props.points.map((item) => item.review_count),
      },
      {
        name: "负面评论",
        type: "line",
        smooth: true,
        data: props.points.map((item) => item.negative_count),
      },
    ],
  });
}

onMounted(() => {
  render();
  if (root.value) {
    observer = new ResizeObserver(() => chart?.resize());
    observer.observe(root.value);
  }
});
watch(() => props.points, render, { deep: true });
onBeforeUnmount(() => {
  observer?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div ref="root" class="review-trend-chart" role="img" aria-label="评论时间趋势图"></div>
</template>

<style scoped>
.review-trend-chart {
  width: 100%;
  height: 280px;
}
</style>
