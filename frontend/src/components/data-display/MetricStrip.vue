<script setup lang="ts">
import MetricItem from "@/components/data-display/MetricItem.vue";
import type { DashboardMetric } from "@/types/dashboard";

interface Props {
  metrics: DashboardMetric[];
}

const props = defineProps<Props>();
</script>

<template>
  <div class="metric-strip">
    <MetricItem v-for="metric in props.metrics" :key="metric.id" :metric="metric" />
  </div>
</template>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  overflow: hidden;
  background: var(--sp-color-surface-strong);
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-card-small);
}

.metric-strip > * + * {
  border-left: 1px solid var(--sp-border-soft);
}

@media (max-width: 767px) {
  .metric-strip {
    grid-template-columns: 1fr;
  }

  .metric-strip > * + * {
    border-top: 1px solid var(--sp-border-soft);
    border-left: 0;
  }
}
</style>
