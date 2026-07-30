<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import type { TrendPoint } from "@/types/review-analysis";
import { formatSiteName } from "@/utils/displayLabels";

const props = defineProps<{ points: TrendPoint[] }>();
const singlePoint = computed(() => (props.points.length === 1 ? props.points[0] : null));
const root = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;
let observer: ResizeObserver | null = null;

function render(): void {
  if (!root.value) return;
  chart ??= echarts.init(root.value);
  const styles = getComputedStyle(root.value);
  const primary = styles.getPropertyValue("--sp-color-primary").trim();
  const danger = styles.getPropertyValue("--sp-color-danger").trim();
  const muted = styles.getPropertyValue("--sp-color-text-muted").trim();
  const border = styles.getPropertyValue("--sp-border-soft").trim();
  const compact = props.points.length <= 2;
  chart.setOption({
    animation: false,
    color: [primary, danger],
    tooltip: { trigger: "axis", valueFormatter: (value: unknown) => String(value) },
    legend: {
      top: 0,
      right: 0,
      data: ["评论总数", "含改进信号评论"],
      textStyle: { color: muted },
    },
    grid: { left: 36, right: 16, top: 42, bottom: 28, containLabel: true },
    xAxis: {
      type: "category",
      data: props.points.map((item) => `${item.month} · ${formatSiteName(item.site)}`),
      axisLine: { lineStyle: { color: border } },
      axisTick: { show: false },
      axisLabel: { color: muted },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: muted },
      splitLine: { lineStyle: { color: border } },
    },
    series: [
      {
        name: "评论总数",
        type: compact ? "bar" : "line",
        barMaxWidth: 56,
        symbolSize: 8,
        smooth: !compact,
        data: props.points.map((item) => item.review_count),
      },
      {
        name: "含改进信号评论",
        type: compact ? "bar" : "line",
        barMaxWidth: 56,
        symbolSize: 8,
        smooth: !compact,
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
  <div v-if="singlePoint" class="single-period" aria-label="单期评论统计">
    <div class="single-period__label">
      <small>统计周期</small>
      <strong>{{ singlePoint.month }}</strong>
      <span>{{ formatSiteName(singlePoint.site) }}</span>
    </div>
    <div>
      <small>评论总数</small><strong>{{ singlePoint.review_count }}</strong>
    </div>
    <div>
      <small>含改进信号评论</small><strong>{{ singlePoint.negative_count }}</strong>
    </div>
    <div>
      <small>平均评分</small><strong>{{ Number(singlePoint.average_rating).toFixed(1) }}</strong
      ><span>/ 5.0</span>
    </div>
  </div>
  <div v-else ref="root" class="review-trend-chart" role="img" aria-label="评论时间趋势图"></div>
</template>

<style scoped>
.review-trend-chart {
  width: 100%;
  height: 220px;
  margin-top: var(--sp-space-4);
}
.single-period {
  display: grid;
  grid-template-columns: 1.3fr repeat(3, 1fr);
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-4);
}
.single-period > div {
  display: grid;
  gap: var(--sp-space-1);
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.single-period small,
.single-period span {
  color: var(--sp-color-text-muted);
}
.single-period strong {
  font-size: var(--sp-font-xl);
}
@media (max-width: 640px) {
  .single-period {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
