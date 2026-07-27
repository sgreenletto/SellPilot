<script setup lang="ts">
import { ElTooltip } from "element-plus";

interface Props {
  ariaLabel: string;
  tooltip?: string;
  round?: boolean;
  disabled?: boolean;
  size?: "sm" | "md" | "lg";
}

const props = withDefaults(defineProps<Props>(), {
  tooltip: "",
  round: true,
  disabled: false,
  size: "md",
});

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<template>
  <ElTooltip :content="props.tooltip || props.ariaLabel" placement="top" :show-after="400">
    <button
      type="button"
      :class="[
        'sp-icon-button',
        `sp-icon-button--${props.size}`,
        { 'sp-icon-button--round': props.round },
      ]"
      :aria-label="props.ariaLabel"
      :disabled="props.disabled"
      @click="emit('click', $event)"
    >
      <slot />
    </button>
  </ElTooltip>
</template>

<style scoped>
.sp-icon-button {
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--sp-color-text-secondary);
  cursor: pointer;
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-control);
  transition:
    transform var(--sp-transition-fast),
    color var(--sp-transition-fast),
    box-shadow var(--sp-transition-fast);
}

.sp-icon-button:hover:not(:disabled) {
  color: var(--sp-color-primary);
  box-shadow: var(--sp-shadow-card);
  transform: translateY(-1px);
}

.sp-icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.sp-icon-button--round {
  border-radius: var(--sp-radius-pill);
}

.sp-icon-button--sm {
  width: 34px;
  height: 34px;
}

.sp-icon-button--md {
  width: 42px;
  height: 42px;
}

.sp-icon-button--lg {
  width: 50px;
  height: 50px;
}
</style>
