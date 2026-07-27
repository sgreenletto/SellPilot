<script setup lang="ts">
interface Props {
  initials: string;
  gradient?: "blue" | "pink" | "purple";
  size?: "sm" | "md" | "lg";
  label?: string;
}

const props = withDefaults(defineProps<Props>(), {
  gradient: "blue",
  size: "md",
  label: "",
});
</script>

<template>
  <span
    :class="['sp-avatar', `sp-avatar--${props.gradient}`, `sp-avatar--${props.size}`]"
    role="img"
    :aria-label="props.label || props.initials"
  >
    {{ props.initials }}
  </span>
</template>

<style scoped>
.sp-avatar {
  display: inline-grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--sp-color-text-inverse);
  font-size: var(--sp-font-xs);
  font-weight: 800;
  letter-spacing: 0.02em;
  border: 2px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-pill);
  box-shadow: 0 8px 18px color-mix(in srgb, var(--sp-color-primary) 12%, transparent);
}

.sp-avatar--sm {
  width: 34px;
  height: 34px;
}

.sp-avatar--md {
  width: 42px;
  height: 42px;
}

.sp-avatar--lg {
  width: 54px;
  height: 54px;
  font-size: var(--sp-font-sm);
}

.sp-avatar--blue {
  background: linear-gradient(145deg, var(--sp-color-accent-blue), var(--sp-color-primary));
}

.sp-avatar--pink {
  background: linear-gradient(145deg, var(--sp-color-accent-pink), var(--sp-color-accent-purple));
}

.sp-avatar--purple {
  background: linear-gradient(145deg, var(--sp-color-accent-purple), var(--sp-color-accent-blue));
}
</style>
