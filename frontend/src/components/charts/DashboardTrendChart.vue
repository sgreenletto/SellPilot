<script setup lang="ts">
import * as echarts from "echarts";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import SpEmptyState from "@/components/base/SpEmptyState.vue";
import type { TrendDataset, TrendType } from "@/types/dashboard";

interface Props {
  dataset: TrendDataset;
  trendType: TrendType;
}

const props = defineProps<Props>();

const chartElement = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

const hasData = computed(() => props.dataset.categories.length > 0);

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const colorMap: Record<string, string> = {
  blue: token("--sp-color-accent-blue"),
  pink: token("--sp-color-accent-pink"),
  purple: token("--sp-color-accent-purple"),
  green: token("--sp-color-success"),
  navy: token("--sp-color-primary"),
};

const colorSoftMap: Record<string, string> = {
  blue: token("--sp-color-accent-blue-soft"),
  pink: token("--sp-color-accent-pink-soft"),
  purple: token("--sp-color-accent-purple"),
  green: token("--sp-color-success"),
  navy: token("--sp-color-primary"),
};

function buildFunnelOption(): echarts.EChartsOption {
  const values = props.dataset.series[0]?.data ?? [];
  const maxValue = Math.max(...values, 1);
  const middleLayer = values.map((value) => value * 0.68);
  const innerLayer = values.map((value) => value * 0.38);
  const layerColors = [
    token("--sp-color-accent-blue-soft"),
    token("--sp-color-accent-blue"),
    token("--sp-color-primary"),
  ];

  return {
    animationDuration: 700,
    grid: { top: 12, right: 12, bottom: 4, left: 12 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: token("--sp-border-strong"),
      textStyle: { color: token("--sp-color-text"), fontSize: 13 },
      formatter: (params) => {
        const items = Array.isArray(params) ? params : [params];
        const index = items[0]?.dataIndex ?? 0;
        const category = props.dataset.categories[index];
        const value = values[index];
        return category && value != null
          ? `${category}<br/><strong>${value.toLocaleString("zh-CN")}</strong>`
          : "";
      },
    },
    xAxis: {
      type: "category",
      data: props.dataset.categories,
      boundaryGap: false,
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: {
        show: true,
        lineStyle: { color: token("--sp-border-soft"), width: 1 },
      },
    },
    yAxis: { type: "value", min: 0, max: Math.ceil(maxValue * 1.1), show: false },
    series: [values, middleLayer, innerLayer].map((data, index) => ({
      type: "line",
      data,
      smooth: 0.32,
      symbol: "none",
      silent: index > 0,
      lineStyle: {
        width: index === 0 ? 1.5 : index === 1 ? 1 : 0,
        color: layerColors[index],
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: layerColors[index]! },
          { offset: 1, color: "transparent" },
        ]),
        opacity: [0.78, 0.34, 0.16][index],
      },
    })),
  };
}

function buildLineOption(): echarts.EChartsOption {
  return {
    animationDuration: 600,
    grid: { top: 16, right: 16, bottom: 28, left: 40 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: token("--sp-border-strong"),
      textStyle: { color: token("--sp-color-text"), fontSize: 13 },
    },
    legend: {
      bottom: 0,
      textStyle: { color: token("--sp-color-text-muted"), fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 16,
    },
    xAxis: {
      type: "category",
      data: props.dataset.categories,
      boundaryGap: false,
      axisLine: { lineStyle: { color: token("--sp-border-soft") } },
      axisTick: { show: false },
      axisLabel: { color: token("--sp-color-text-muted"), fontSize: 11 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: token("--sp-border-soft"), type: "dashed" } },
      axisLabel: { color: token("--sp-color-text-muted"), fontSize: 11 },
    },
    series: props.dataset.series.map((s) => ({
      name: s.name,
      type: "line",
      data: s.data,
      smooth: 0.45,
      symbol: "circle",
      symbolSize: 5,
      lineStyle: { width: 2, color: colorMap[s.color ?? "blue"] ?? colorMap.blue! },
      itemStyle: { color: colorMap[s.color ?? "blue"] ?? colorMap.blue! },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: colorSoftMap[s.color ?? "blue"] ?? colorSoftMap.blue! },
          { offset: 1, color: "transparent" },
        ]),
        opacity: 0.45,
      },
    })),
  };
}

function buildOption(): echarts.EChartsOption {
  if (props.trendType === "funnel") {
    return buildFunnelOption();
  }
  return buildLineOption();
}

function renderChart() {
  if (!chartElement.value || !hasData.value) return;
  chart ||= echarts.init(chartElement.value);
  chart.setOption(buildOption(), true);
}

onMounted(async () => {
  await nextTick();
  renderChart();
  if (chartElement.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize());
    resizeObserver.observe(chartElement.value);
  }
});

watch(
  () => [props.dataset, props.trendType],
  () => renderChart(),
  { deep: true },
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div v-if="hasData" ref="chartElement" class="dashboard-trend-chart" aria-label="趋势图表"></div>
  <SpEmptyState v-else title="暂无趋势数据" description="数据准备完成后将在此展示趋势图表。" />
</template>

<style scoped>
.dashboard-trend-chart {
  width: 100%;
  height: 320px;
}

@media (max-width: 767px) {
  .dashboard-trend-chart {
    height: 260px;
  }
}
</style>
