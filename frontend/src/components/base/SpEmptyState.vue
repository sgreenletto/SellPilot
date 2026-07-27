<script setup lang="ts">
interface Props {
  title: string;
  description?: string;
}

withDefaults(defineProps<Props>(), {
  description: "",
});
</script>

<template>
  <div class="sp-empty-state" role="status">
    <div v-if="$slots.icon" class="sp-empty-state__icon" aria-hidden="true">
      <slot name="icon" />
    </div>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.action" class="sp-empty-state__action">
      <slot name="action" />
    </div>
  </div>
</template>

<style scoped>
.sp-empty-state {
  display: grid;
  justify-items: center;
  padding: var(--sp-space-10) var(--sp-space-6);
  color: var(--sp-color-text-secondary);
  text-align: center;
}

.sp-empty-state__icon {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin-bottom: var(--sp-space-4);
  color: var(--sp-color-accent-blue);
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-card-small);
}

.sp-empty-state h3 {
  color: var(--sp-color-text);
  font-size: var(--sp-font-md);
}

.sp-empty-state p {
  max-width: 420px;
  margin-top: var(--sp-space-2);
  color: var(--sp-color-text-muted);
}

.sp-empty-state__action {
  margin-top: var(--sp-space-5);
}
</style>
