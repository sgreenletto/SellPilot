<script setup lang="ts">
import { LoaderCircle } from "@lucide/vue";

interface Props {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  type?: "button" | "submit" | "reset";
  loading?: boolean;
  disabled?: boolean;
  block?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "primary",
  size: "md",
  type: "button",
  loading: false,
  disabled: false,
  block: false,
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<template>
  <button
    :class="[
      'sp-button',
      `sp-button--${props.variant}`,
      `sp-button--${props.size}`,
      { 'sp-button--block': props.block },
    ]"
    :type="props.type"
    :disabled="props.disabled || props.loading"
    :aria-busy="props.loading"
    @click="emit('click', $event)"
  >
    <LoaderCircle v-if="props.loading" class="sp-button__spinner" :size="17" aria-hidden="true" />
    <span v-else-if="$slots.icon" class="sp-button__icon" aria-hidden="true">
      <slot name="icon" />
    </span>
    <span><slot /></span>
  </button>
</template>

<style scoped>
.sp-button {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  justify-content: center;
  min-width: 0;
  font-weight: 650;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: var(--sp-radius-control);
  transition:
    transform var(--sp-transition-fast),
    box-shadow var(--sp-transition-fast),
    background var(--sp-transition-fast),
    opacity var(--sp-transition-fast);
}

.sp-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.sp-button:disabled {
  cursor: not-allowed;
  opacity: 0.52;
}

.sp-button--sm {
  min-height: 34px;
  padding: 0 var(--sp-space-3);
  font-size: var(--sp-font-xs);
}

.sp-button--md {
  min-height: 42px;
  padding: 0 var(--sp-space-5);
  font-size: var(--sp-font-sm);
}

.sp-button--lg {
  min-height: 50px;
  padding: 0 var(--sp-space-6);
  font-size: var(--sp-font-md);
}

.sp-button--primary {
  color: var(--sp-color-text-inverse);
  background: var(--sp-color-primary);
  box-shadow: 0 10px 24px color-mix(in srgb, var(--sp-color-primary) 20%, transparent);
}

.sp-button--primary:hover:not(:disabled) {
  background: var(--sp-color-primary-hover);
}

.sp-button--secondary {
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-strong);
  border-color: var(--sp-border-strong);
}

.sp-button--ghost {
  color: var(--sp-color-text-secondary);
  background: transparent;
}

.sp-button--ghost:hover:not(:disabled) {
  background: var(--sp-color-surface-hover);
}

.sp-button--danger {
  color: var(--sp-color-text-inverse);
  background: var(--sp-color-danger);
}

.sp-button--block {
  width: 100%;
}

.sp-button__icon,
.sp-button__spinner {
  flex: 0 0 auto;
}

.sp-button__spinner {
  animation: sp-spin 0.85s linear infinite;
}

@keyframes sp-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
