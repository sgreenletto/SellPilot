<script setup lang="ts">
import * as echarts from "echarts";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { HealthPoint } from "@/types/dashboard";

interface Props {
  points: HealthPoint[];
}

const props = defineProps<Props>();
const chartElement = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function renderChart() {
  if (!chartElement.value || props.points.length === 0) {
    return;
  }
  chart ||= echarts.init(chartElement.value);
  chart.setOption(
    {
      animationDuration: 500,
      grid: { top: 12, right: 8, bottom: 22, left: 8 },
      xAxis: {
        type: "category",
        data: props.points.map((point) => point.label),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: token("--sp-color-text-muted"),
          fontSize: 10,
        },
      },
      yAxis: { type: "value", min: 55, max: 90, show: false },
      series: [
        {
          type: "line",
          data: props.points.map((point) => point.value),
          smooth: 0.45,
          symbol: "circle",
          symbolSize: 6,
          lineStyle: { width: 2, color: token("--sp-color-accent-blue") },
          itemStyle: {
            color: token("--sp-color-surface-strong"),
            borderColor: token("--sp-color-accent-blue"),
            borderWidth: 2,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: token("--sp-color-accent-blue-soft") },
              { offset: 1, color: "transparent" },
            ]),
            opacity: 0.7,
          },
        },
      ],
    },
    true,
  );
}

onMounted(async () => {
  await nextTick();
  renderChart();
  if (chartElement.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize());
    resizeObserver.observe(chartElement.value);
  }
});
watch(() => props.points, renderChart, { deep: true });
onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
});
</script>

<template>
  <div ref="chartElement" class="mini-health-chart" aria-label="运营健康度趋势图"></div>
</template>

<style scoped>
.mini-health-chart {
  width: 100%;
  height: 116px;
}
</style>
