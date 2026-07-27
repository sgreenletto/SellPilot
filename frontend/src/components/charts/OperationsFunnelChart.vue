<script setup lang="ts">
import * as echarts from "echarts";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import SpEmptyState from "@/components/base/SpEmptyState.vue";
import type { FunnelStage } from "@/types/dashboard";

interface Props {
  stages: FunnelStage[];
}

const props = defineProps<Props>();
const chartElement = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

const hasData = computed(() => props.stages.length > 0);

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function buildOption(): echarts.EChartsOption {
  const labels = props.stages.map((stage) => stage.label);
  const values = props.stages.map((stage) => Math.max(10, Math.sqrt(stage.percentage) * 10));
  const middleValues = values.map((value) => value * 0.72);
  const innerValues = values.map((value) => value * 0.46);

  return {
    animationDuration: 700,
    grid: { top: 8, right: 12, bottom: 2, left: 12 },
    tooltip: {
      trigger: "axis",
      backgroundColor: token("--sp-color-surface-strong"),
      borderColor: token("--sp-border-strong"),
      textStyle: { color: token("--sp-color-text") },
      formatter: (params) => {
        const items = Array.isArray(params) ? params : [params];
        const index = items[0]?.dataIndex ?? 0;
        const stage = props.stages[index];
        return stage
          ? `${stage.label}<br/><strong>${stage.count.toLocaleString("zh-CN")}</strong> · ${stage.percentage}%`
          : "";
      },
    },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: {
        show: true,
        lineStyle: { color: token("--sp-border-soft"), width: 1 },
      },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 110,
      show: false,
    },
    series: [
      {
        type: "line",
        data: values,
        smooth: 0.52,
        symbol: "none",
        lineStyle: { width: 1, color: token("--sp-color-accent-blue-soft") },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: token("--sp-color-accent-blue-soft") },
            { offset: 1, color: "transparent" },
          ]),
          opacity: 0.85,
        },
      },
      {
        type: "line",
        data: middleValues,
        smooth: 0.5,
        symbol: "none",
        lineStyle: { width: 1, color: token("--sp-color-accent-blue") },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: token("--sp-color-accent-blue") },
            { offset: 1, color: "transparent" },
          ]),
          opacity: 0.34,
        },
      },
      {
        type: "line",
        data: innerValues,
        smooth: 0.48,
        symbol: "none",
        lineStyle: { width: 0, color: token("--sp-color-primary") },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: token("--sp-color-primary") },
            { offset: 1, color: "transparent" },
          ]),
          opacity: 0.16,
        },
      },
    ],
  };
}

function renderChart() {
  if (!chartElement.value || !hasData.value) {
    return;
  }
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

watch(() => props.stages, renderChart, { deep: true });

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div v-if="hasData" class="operations-funnel">
    <div class="operations-funnel__stages">
      <article v-for="stage in props.stages" :key="stage.id">
        <strong>{{ stage.count.toLocaleString("zh-CN") }}</strong>
        <span>{{ stage.label }}</span>
      </article>
    </div>
    <div ref="chartElement" class="operations-funnel__chart" aria-label="商品运营漏斗面积图"></div>
    <div class="operations-funnel__percentages">
      <span v-for="stage in props.stages" :key="`${stage.id}-percentage`">
        {{ stage.percentage }}%
      </span>
    </div>
  </div>
  <SpEmptyState v-else title="暂无漏斗数据" description="数据准备完成后将在此展示转化趋势。" />
</template>

<style scoped>
.operations-funnel {
  min-width: 0;
}

.operations-funnel__stages,
.operations-funnel__percentages {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.operations-funnel__stages article {
  display: grid;
  gap: var(--sp-space-1);
  padding: 0 var(--sp-space-4);
  border-left: 1px solid var(--sp-border-soft);
}

.operations-funnel__stages article:first-child {
  border-left: 0;
}

.operations-funnel__stages strong {
  font-size: var(--sp-font-xl);
  font-weight: 640;
  letter-spacing: -0.04em;
}

.operations-funnel__stages span,
.operations-funnel__percentages span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.operations-funnel__chart {
  width: 100%;
  height: 210px;
  margin-top: var(--sp-space-2);
}

.operations-funnel__percentages span {
  padding: var(--sp-space-2) var(--sp-space-4) 0;
  border-left: 1px solid var(--sp-border-soft);
}

.operations-funnel__percentages span:first-child {
  border-left: 0;
}

@media (max-width: 767px) {
  .operations-funnel__stages article,
  .operations-funnel__percentages span {
    padding-inline: var(--sp-space-2);
  }

  .operations-funnel__stages strong {
    font-size: var(--sp-font-lg);
  }

  .operations-funnel__chart {
    height: 170px;
  }
}
</style>
