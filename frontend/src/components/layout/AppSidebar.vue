<script setup lang="ts">
import { PanelLeftClose, PanelLeftOpen } from "@lucide/vue";
import { computed } from "vue";

import SpAvatar from "@/components/base/SpAvatar.vue";
import SpIconButton from "@/components/base/SpIconButton.vue";
import SidebarNavGroup from "@/components/layout/SidebarNavGroup.vue";
import SidebarNavItem from "@/components/layout/SidebarNavItem.vue";
import { navigationEntries } from "@/config/navigation";
import { useSidebar } from "@/composables/useSidebar";
import { isNavigationGroup } from "@/types/navigation";

const { sidebarCollapsed, closeMobileSidebar, toggleSidebar } = useSidebar();
const entries = computed(() => navigationEntries);
</script>

<template>
  <aside :class="['app-sidebar', { 'app-sidebar--collapsed': sidebarCollapsed }]">
    <div class="app-sidebar__brand">
      <span class="app-sidebar__mark" aria-hidden="true"> <i></i><i></i><i></i><i></i> </span>
      <strong v-if="!sidebarCollapsed">SellPilot</strong>
      <SpIconButton
        :ariaLabel="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
        size="sm"
        @click="toggleSidebar"
      >
        <PanelLeftOpen v-if="sidebarCollapsed" :size="17" />
        <PanelLeftClose v-else :size="17" />
      </SpIconButton>
    </div>

    <nav class="app-sidebar__nav" aria-label="主导航">
      <template v-for="entry in entries" :key="entry.id">
        <SidebarNavGroup
          v-if="isNavigationGroup(entry)"
          :group="entry"
          :collapsed="sidebarCollapsed"
          @navigate="closeMobileSidebar"
        />
        <SidebarNavItem
          v-else
          :item="entry"
          :collapsed="sidebarCollapsed"
          @navigate="closeMobileSidebar"
        />
      </template>
    </nav>

    <div class="app-sidebar__operator">
      <SpAvatar initials="AD" gradient="purple" />
      <div v-if="!sidebarCollapsed">
        <strong>管理员</strong>
        <span>SellPilot 运营人员</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: var(--sp-sidebar-width);
  min-width: var(--sp-sidebar-width);
  height: 100%;
  min-height: 0;
  padding: var(--sp-space-6) var(--sp-space-4);
  overflow-x: hidden;
  overflow: hidden;
  background: var(--sp-color-sidebar);
  border-right: 1px solid var(--sp-border-highlight);
  box-shadow: var(--sp-shadow-sidebar);
  transition:
    width var(--sp-transition-normal),
    min-width var(--sp-transition-normal),
    transform var(--sp-transition-normal);
  backdrop-filter: blur(20px);
}

.app-sidebar--collapsed {
  width: var(--sp-sidebar-collapsed-width);
  min-width: var(--sp-sidebar-collapsed-width);
  padding-inline: var(--sp-space-3);
}

.app-sidebar--collapsed .app-sidebar__brand {
  gap: var(--sp-space-2);
  padding-inline: 0;
}

.app-sidebar__brand {
  display: flex;
  flex: 0 0 auto;
  gap: var(--sp-space-3);
  align-items: center;
  min-width: 0;
  min-height: 44px;
  padding: 0 var(--sp-space-2);
}

.app-sidebar__brand strong {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: var(--sp-font-lg);
  letter-spacing: -0.03em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-sidebar__mark {
  display: grid;
  grid-template-columns: repeat(2, 8px);
  gap: 3px;
  flex: 0 0 auto;
}

.app-sidebar__mark i {
  width: 8px;
  height: 8px;
  background: var(--sp-color-accent-pink);
  border-radius: 3px;
}

.app-sidebar__nav {
  display: grid;
  flex: 1 1 auto;
  gap: var(--sp-space-1);
  width: 100%;
  min-width: 0;
  min-height: 0;
  padding-top: var(--sp-space-8);
  overflow-x: hidden;
  overflow-y: auto;
}

.app-sidebar__operator {
  display: flex;
  flex: 0 0 auto;
  gap: var(--sp-space-3);
  align-items: center;
  min-width: 0;
  overflow: hidden;
  padding: var(--sp-space-4) var(--sp-space-2) 0;
  margin-top: auto;
  border-top: 1px solid var(--sp-border-soft);
}

.app-sidebar__operator > div {
  display: grid;
  flex: 1;
  min-width: 0;
}

.app-sidebar__operator strong {
  font-size: var(--sp-font-sm);
}

.app-sidebar__operator span {
  overflow: hidden;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1023px) {
  .app-sidebar,
  .app-sidebar--collapsed {
    width: min(var(--sp-sidebar-width), calc(100vw - 56px));
    min-width: min(var(--sp-sidebar-width), calc(100vw - 56px));
  }
}
</style>
