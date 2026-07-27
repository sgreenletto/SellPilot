<script setup lang="ts">
interface Props {
  variant?: "glass" | "solid" | "flat";
  padding?: "sm" | "md" | "lg";
  hoverable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "glass",
  padding: "md",
  hoverable: false,
});
</script>

<template>
  <section
    :class="[
      'sp-card',
      `sp-card--${props.variant}`,
      `sp-card--padding-${props.padding}`,
      { 'sp-card--hoverable': props.hoverable },
    ]"
  >
    <header v-if="$slots.header" class="sp-card__header">
      <slot name="header" />
    </header>
    <div class="sp-card__body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="sp-card__footer">
      <slot name="footer" />
    </footer>
  </section>
</template>

<style scoped>
.sp-card {
  min-width: 0;
  border-radius: var(--sp-radius-card);
  transition:
    transform var(--sp-transition-normal),
    box-shadow var(--sp-transition-normal);
}

.sp-card--glass {
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-highlight);
  box-shadow: var(--sp-shadow-card);
  backdrop-filter: blur(18px);
}

.sp-card--solid {
  background: var(--sp-color-surface-strong);
  border: 1px solid var(--sp-border-soft);
  box-shadow: var(--sp-shadow-card);
}

.sp-card--flat {
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
}

.sp-card--hoverable:hover {
  box-shadow: var(--sp-shadow-hover);
  transform: translateY(-2px);
}

.sp-card--padding-sm {
  padding: var(--sp-space-4);
}

.sp-card--padding-md {
  padding: var(--sp-space-6);
}

.sp-card--padding-lg {
  padding: var(--sp-space-8);
}

.sp-card__header {
  margin-bottom: var(--sp-space-5);
}

.sp-card__footer {
  margin-top: var(--sp-space-5);
}

@media (max-width: 767px) {
  .sp-card--padding-lg {
    padding: var(--sp-space-5);
  }
}
</style>
