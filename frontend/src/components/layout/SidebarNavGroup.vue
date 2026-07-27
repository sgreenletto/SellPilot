<script setup lang="ts">
import { ChevronDown } from "@lucide/vue";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

import SidebarNavItem from "@/components/layout/SidebarNavItem.vue";
import type { NavigationGroup } from "@/types/navigation";

interface Props {
  group: NavigationGroup;
  collapsed?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  collapsed: false,
});
const emit = defineEmits<{
  navigate: [];
}>();
const route = useRoute();
const hasActiveChild = computed(() =>
  props.group.children.some((child) => child.path === route.path),
);
const expanded = ref(hasActiveChild.value);

watch(hasActiveChild, (active) => {
  if (active) {
    expanded.value = true;
  }
});
</script>

<template>
  <div class="sidebar-nav-group">
    <button
      type="button"
      :class="[
        'sidebar-nav-group__trigger',
        { 'sidebar-nav-group__trigger--active': hasActiveChild },
      ]"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <component :is="props.group.icon" :size="18" aria-hidden="true" />
      <span v-if="!props.collapsed">{{ props.group.label }}</span>
      <span v-else class="sp-visually-hidden">{{ props.group.label }}</span>
      <ChevronDown
        v-if="!props.collapsed"
        :size="15"
        :class="{ 'sidebar-nav-group__chevron--open': expanded }"
        aria-hidden="true"
      />
    </button>
    <div v-show="expanded && !props.collapsed" class="sidebar-nav-group__children">
      <SidebarNavItem
        v-for="item in props.group.children"
        :key="item.id"
        :item="item"
        @navigate="emit('navigate')"
      />
    </div>
  </div>
</template>

<style scoped>
.sidebar-nav-group {
  display: grid;
  gap: var(--sp-space-1);
}

.sidebar-nav-group__trigger {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  width: 100%;
  min-height: 42px;
  padding: 0 var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  text-align: left;
  cursor: pointer;
  background: transparent;
  border-radius: var(--sp-radius-pill);
  transition:
    color var(--sp-transition-fast),
    background var(--sp-transition-fast);
}

.sidebar-nav-group__trigger:hover,
.sidebar-nav-group__trigger--active {
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-hover);
}

.sidebar-nav-group__trigger > span {
  flex: 1;
}

.sidebar-nav-group__trigger > svg:last-child {
  transition: transform var(--sp-transition-fast);
}

.sidebar-nav-group__chevron--open {
  transform: rotate(180deg);
}

.sidebar-nav-group__children {
  display: grid;
  gap: var(--sp-space-1);
  padding-left: var(--sp-space-4);
}
</style>
