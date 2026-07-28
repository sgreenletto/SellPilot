<script setup lang="ts">
import * as echarts from "echarts"
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"

import SpEmptyState from "@/components/base/SpEmptyState.vue"
import type { TrendDataset, TrendType } from "@/types/dashboard"

interface Props {
  dataset: TrendDataset
  trendType: TrendType
}

const props = defineProps<Props>()

const chartElement = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const hasData = computed(() => props.dataset.categories.length > 0)

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

const colorMap: Record<string, string> = {
  blue: token("--sp-color-accent-blue"),
  pink: token("--sp-color-accent-pink"),
  purple: token("--sp-color-accent-purple"),
  green: token("--sp-color-success"),
  navy: token("--sp-color-primary"),
}

const colorSoftMap: Record<string, string> = {
  blue: token("--sp-color-accent-blue-soft"),
  pink: token("--sp-color-accent-pink-soft"),
  purple: token("--sp-color-accent-purple"),
  green: token("--sp-color-success"),
  navy: token("--sp-color-primary"),
}

function buildFunnelOption(): echarts.EChartsOption {
  const values = props.dataset.series[0]?.data ?? []
  const maxVal = Math.max(...values, 1)
  const scaled = values.map((v) => Math.max(8, (v / maxVal) * 100))
  const mid = scaled.map((v) => v * 0.7)
  const inner = scaled.map((v) => v * 0.42)

  return {
    animationDuration: 700,
    grid: { top: 8, right: 12, bottom: 2, left: 12 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#ffffff",
      borderColor: token("--sp-border-strong"),
      textStyle: { color: token("--sp-color-text"), fontSize: 13 },
      formatter: (params) => {
        const items = Array.isArray(params) ? params : [params]
        const index = items[0]?.dataIndex ?? 0
        const cat = props.dataset.categories[index]
        const val = values[index]
        return cat && val != null
          ? `${cat}<br/><strong>${val.toLocaleString("zh-CN")}</strong>`
          : ""
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
    yAxis: { type: "value", min: 0, max: 110, show: false },
    series: [scaled, mid, inner].map((data, i) => ({
      type: "line",
      data,
      smooth: 0.52,
      symbol: "none",
      lineStyle: {
        width: i === 0 ? 1 : i === 1 ? 1 : 0,
        color: [token("--sp-color-accent-blue-soft"), token("--sp-color-accent-blue"), token("--sp-color-primary")][i],
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: [token("--sp-color-accent-blue-soft"), token("--sp-color-accent-blue"), token("--sp-color-primary")][i] },
          { offset: 1, color: "transparent" },
        ]),
        opacity: [0.85, 0.34, 0.16][i],
      },
    })),
  }
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
      lineStyle: { width: 2, color: colorMap[s.color ?? "blue"] || colorMap.blue },
      itemStyle: { color: colorMap[s.color ?? "blue"] || colorMap.blue },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: colorSoftMap[s.color ?? "blue"] || colorSoftMap.blue },
          { offset: 1, color: "transparent" },
        ]),
        opacity: 0.45,
      },
    })),
  }
}

function buildOption(): echarts.EChartsOption {
  if (props.trendType === "funnel") {
    return buildFunnelOption()
  }
  return buildLineOption()
}

function renderChart() {
  if (!chartElement.value || !hasData.value) return
  chart ||= echarts.init(chartElement.value)
  chart.setOption(buildOption(), true)
}

onMounted(async () => {
  await nextTick()
  renderChart()
  if (chartElement.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartElement.value)
  }
})

watch(
  () => [props.dataset, props.trendType],
  () => renderChart(),
  { deep: true },
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
})
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
