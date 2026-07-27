<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";

import type { NavigationItem } from "@/types/navigation";

interface Props {
  item: NavigationItem;
  collapsed?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  collapsed: false,
});
const route = useRoute();

const emit = defineEmits<{
  navigate: [];
}>();
</script>

<template>
  <RouterLink
    :to="props.item.path"
    :class="['sidebar-nav-item', { 'sidebar-nav-item--active': route.path === props.item.path }]"
    :aria-current="route.path === props.item.path ? 'page' : undefined"
    @click="emit('navigate')"
  >
    <component :is="props.item.icon" :size="18" aria-hidden="true" />
    <span v-if="!props.collapsed">{{ props.item.label }}</span>
    <span v-else class="sp-visually-hidden">{{ props.item.label }}</span>
  </RouterLink>
</template>

<style scoped>
.sidebar-nav-item {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  min-height: 42px;
  padding: 0 var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  border: 1px solid transparent;
  border-radius: var(--sp-radius-pill);
  transition:
    color var(--sp-transition-fast),
    background var(--sp-transition-fast),
    transform var(--sp-transition-fast);
}

.sidebar-nav-item:hover {
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-hover);
  transform: translateX(2px);
}

.sidebar-nav-item--active {
  color: var(--sp-color-primary);
  font-weight: 750;
  background: var(--sp-color-surface);
  border-color: var(--sp-border-highlight);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--sp-color-primary) 5%, transparent);
}
</style>
