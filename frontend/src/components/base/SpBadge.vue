<script setup lang="ts">
interface Props {
  tone?: "neutral" | "primary" | "success" | "warning" | "danger" | "info" | "purple";
  dot?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  tone: "neutral",
  dot: false,
});
</script>

<template>
  <span :class="['sp-badge', `sp-badge--${props.tone}`]">
    <span v-if="props.dot" class="sp-badge__dot" aria-hidden="true"></span>
    <slot />
  </span>
</template>

<style scoped>
.sp-badge {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  min-height: 26px;
  padding: 0 var(--sp-space-3);
  font-size: var(--sp-font-xs);
  font-weight: 700;
  border-radius: var(--sp-radius-pill);
}

.sp-badge__dot {
  width: 7px;
  height: 7px;
  background: currentColor;
  border-radius: var(--sp-radius-pill);
}

.sp-badge--neutral {
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface-muted);
}

.sp-badge--primary {
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
}

.sp-badge--success {
  color: var(--sp-color-success);
  background: color-mix(in srgb, var(--sp-color-success) 12%, var(--sp-color-surface-strong));
}

.sp-badge--warning {
  color: var(--sp-color-warning);
  background: color-mix(in srgb, var(--sp-color-warning) 13%, var(--sp-color-surface-strong));
}

.sp-badge--danger {
  color: var(--sp-color-danger);
  background: var(--sp-color-accent-pink-soft);
}

.sp-badge--info {
  color: var(--sp-color-info);
  background: var(--sp-color-accent-blue-soft);
}

.sp-badge--purple {
  color: var(--sp-color-accent-purple);
  background: color-mix(in srgb, var(--sp-color-accent-purple) 14%, var(--sp-color-surface-strong));
}
</style>
