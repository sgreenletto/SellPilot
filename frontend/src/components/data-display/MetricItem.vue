<script setup lang="ts">
import { MessageCircleMore, PackageCheck, TrendingUp } from "@lucide/vue";

import type { DashboardMetric } from "@/types/dashboard";

interface Props {
  metric: DashboardMetric;
}

const props = defineProps<Props>();

const iconMap = {
  trend: TrendingUp,
  message: MessageCircleMore,
  package: PackageCheck,
};
</script>

<template>
  <article :class="['metric-item', `metric-item--${props.metric.tone}`]">
    <div class="metric-item__top">
      <strong>{{ props.metric.value }}</strong>
      <component :is="iconMap[props.metric.icon]" :size="17" aria-hidden="true" />
    </div>
    <span>{{ props.metric.label }}</span>
  </article>
</template>

<style scoped>
.metric-item {
  display: grid;
  gap: var(--sp-space-2);
  min-width: 0;
  padding: var(--sp-space-4) var(--sp-space-5);
}

.metric-item__top {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: space-between;
}

.metric-item strong {
  color: var(--sp-color-text);
  font-size: var(--sp-font-metric);
  font-weight: 640;
  letter-spacing: -0.04em;
}

.metric-item span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.metric-item--pink svg {
  color: var(--sp-color-accent-pink);
}

.metric-item--blue svg {
  color: var(--sp-color-accent-blue);
}

.metric-item--navy svg {
  color: var(--sp-color-primary);
}
</style>
