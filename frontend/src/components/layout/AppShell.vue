<script setup lang="ts">
import { watch } from "vue";

import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppTopbar from "@/components/layout/AppTopbar.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useSidebar } from "@/composables/useSidebar";

const { isMobile } = useBreakpoint();
const { mobileSidebarOpen, closeMobileSidebar } = useSidebar();

watch(isMobile, (mobile) => {
  if (!mobile) {
    closeMobileSidebar();
  }
});
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--mobile': isMobile }">
    <button
      v-if="isMobile && mobileSidebarOpen"
      type="button"
      class="app-shell__overlay"
      aria-label="关闭导航"
      @click="closeMobileSidebar"
    ></button>
    <div
      :class="[
        'app-shell__sidebar',
        { 'app-shell__sidebar--open': !isMobile || mobileSidebarOpen },
      ]"
    >
      <AppSidebar />
    </div>
    <div class="app-shell__workspace">
      <AppTopbar />
      <slot />
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: calc(100vh - 32px);
  height: calc(100dvh - 32px);
  min-height: 0;
  margin: var(--sp-space-4);
  overflow: hidden;
  background: var(--sp-color-shell);
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-shell);
  box-shadow: var(--sp-shadow-shell);
  backdrop-filter: blur(24px);
}

.app-shell__sidebar {
  position: relative;
  z-index: 30;
  display: flex;
  flex: 0 0 auto;
  min-width: 0;
  min-height: 0;
}

.app-shell__workspace {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior-y: contain;
}

.app-shell__overlay {
  position: fixed;
  z-index: 20;
  inset: 0;
  cursor: pointer;
  background: var(--sp-color-overlay);
  backdrop-filter: blur(3px);
}

@media (max-width: 1023px) {
  .app-shell {
    height: calc(100vh - 16px);
    height: calc(100dvh - 16px);
    min-height: 0;
    margin: var(--sp-space-2);
    border-radius: var(--sp-radius-card);
  }

  .app-shell__sidebar {
    position: fixed;
    top: var(--sp-space-2);
    bottom: var(--sp-space-2);
    left: var(--sp-space-2);
    z-index: 40;
    overflow: hidden;
    border-radius: var(--sp-radius-card) 0 0 var(--sp-radius-card);
    transform: translateX(calc(-100% - var(--sp-space-4)));
    transition: transform var(--sp-transition-normal);
  }

  .app-shell__sidebar--open {
    transform: translateX(0);
  }
}
</style>
