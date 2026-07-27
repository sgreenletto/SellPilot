<script setup lang="ts">
interface Props {
  value: number;
  max?: number;
}

const props = withDefaults(defineProps<Props>(), {
  max: 5,
});
</script>

<template>
  <span class="risk-indicator" :aria-label="`风险 ${props.value}/${props.max}`">
    <span class="risk-indicator__bars" aria-hidden="true">
      <span
        v-for="index in props.max"
        :key="index"
        :class="['risk-indicator__bar', { 'risk-indicator__bar--active': index <= props.value }]"
      ></span>
    </span>
    <span class="risk-indicator__text">{{ props.value }}/{{ props.max }}</span>
  </span>
</template>

<style scoped>
.risk-indicator {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
}

.risk-indicator__bars {
  display: inline-flex;
  gap: var(--sp-space-1);
  align-items: center;
}

.risk-indicator__bar {
  width: 5px;
  height: 17px;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-pill);
}

.risk-indicator__bar--active {
  background: var(--sp-color-accent-pink);
  border-color: var(--sp-color-accent-pink);
}

.risk-indicator__text {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 700;
}
</style>
