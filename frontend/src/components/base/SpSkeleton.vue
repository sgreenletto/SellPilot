<script setup lang="ts">
interface Props {
  variant?: "line" | "circle" | "card";
}

const props = withDefaults(defineProps<Props>(), {
  variant: "line",
});
</script>

<template>
  <span
    :class="['sp-skeleton', `sp-skeleton--${props.variant}`]"
    role="status"
    aria-label="内容加载中"
  ></span>
</template>

<style scoped>
.sp-skeleton {
  display: block;
  overflow: hidden;
  background: linear-gradient(
    100deg,
    var(--sp-color-surface-muted) 20%,
    var(--sp-color-surface-strong) 42%,
    var(--sp-color-surface-muted) 64%
  );
  background-size: 220% 100%;
  animation: sp-shimmer 1.5s ease-in-out infinite;
}

.sp-skeleton--line {
  width: 100%;
  height: 14px;
  border-radius: var(--sp-radius-pill);
}

.sp-skeleton--circle {
  width: 46px;
  height: 46px;
  border-radius: var(--sp-radius-pill);
}

.sp-skeleton--card {
  width: 100%;
  min-height: 150px;
  border-radius: var(--sp-radius-card-small);
}

@keyframes sp-shimmer {
  to {
    background-position-x: -220%;
  }
}
</style>
