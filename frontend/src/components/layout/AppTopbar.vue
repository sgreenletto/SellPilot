<script setup lang="ts">
import { Filter, ListTodo, Menu, Search } from "@lucide/vue";
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import SpIconButton from "@/components/base/SpIconButton.vue";
import SpInput from "@/components/base/SpInput.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import PlatformModeBadge from "@/components/data-display/PlatformModeBadge.vue";
import { usePlatformStatus } from "@/composables/usePlatformStatus";
import { useSidebar } from "@/composables/useSidebar";
import { useAppStore } from "@/stores/app";

const route = useRoute();
const router = useRouter();
const appStore = useAppStore();
const { platformStatus, platformStatusLoading, platformStatusError } = storeToRefs(appStore);
const { toggleMobileSidebar } = useSidebar();
const searchQuery = ref("");
const scope = ref("mock-shop");
const scopeOptions = [
  { label: "Shopee 模拟店铺", value: "mock-shop" },
  { label: "全部模拟数据", value: "all-mock" },
];

usePlatformStatus();

watch(
  () => route.meta.title,
  (title) => appStore.setPageTitle(title),
  { immediate: true },
);
</script>

<template>
  <header class="app-topbar">
    <div class="app-topbar__heading">
      <span class="app-topbar__menu">
        <SpIconButton ariaLabel="打开导航" @click="toggleMobileSidebar">
          <Menu :size="20" />
        </SpIconButton>
      </span>
      <div>
        <h1>{{ route.meta.title }}</h1>
        <p>{{ route.meta.description }}</p>
      </div>
    </div>

    <div class="app-topbar__tools">
      <SpSelect v-model="scope" :options="scopeOptions" placeholder="数据范围" />
      <SpInput
        v-model="searchQuery"
        class="app-topbar__search"
        type="search"
        placeholder="搜索（仅本地输入）"
        clearable
      >
        <template #prefix><Search :size="17" /></template>
      </SpInput>
      <SpIconButton ariaLabel="筛选" tooltip="筛选">
        <Filter :size="17" />
      </SpIconButton>
      <SpIconButton ariaLabel="前往任务中心" tooltip="任务中心" @click="router.push('/tasks')">
        <ListTodo :size="19" />
      </SpIconButton>
      <PlatformModeBadge
        :status="platformStatus"
        :loading="platformStatusLoading"
        :error="platformStatusError"
      />
    </div>
  </header>
</template>

<style scoped>
.app-topbar {
  display: flex;
  gap: var(--sp-space-6);
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-space-8) var(--sp-space-8) var(--sp-space-5);
}

.app-topbar__heading,
.app-topbar__tools {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
}

.app-topbar__heading h1 {
  font-size: var(--sp-font-page-title);
  line-height: 1.14;
  letter-spacing: -0.045em;
}

.app-topbar__heading p {
  margin-top: var(--sp-space-1);
  color: var(--sp-color-text-muted);
}

.app-topbar__menu {
  display: none;
}

.app-topbar__search {
  width: min(240px, 22vw);
}

.app-topbar__search :deep(.sp-input-field__control) {
  background: var(--sp-color-surface);
  border: 1px solid transparent;
  border-radius: var(--sp-radius-control);
  box-shadow: none;
  transition:
    background var(--sp-transition-fast),
    border-color var(--sp-transition-fast),
    box-shadow var(--sp-transition-fast);
}

.app-topbar__search :deep(.sp-input-field__control:focus-within) {
  background: var(--sp-color-surface-strong);
  border-color: var(--sp-color-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-color-accent-blue) 14%, transparent);
}

@media (max-width: 1279px) {
  .app-topbar {
    align-items: flex-start;
  }

  .app-topbar__tools {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}

@media (max-width: 1023px) {
  .app-topbar {
    padding: var(--sp-space-5);
  }

  .app-topbar__menu {
    display: inline-flex;
  }

  .app-topbar__tools > :first-child {
    display: none;
  }
}

@media (max-width: 767px) {
  .app-topbar {
    display: grid;
  }

  .app-topbar__heading h1 {
    font-size: var(--sp-font-xl);
  }

  .app-topbar__tools {
    display: grid;
    grid-template-columns: 1fr auto;
    justify-content: stretch;
  }

  .app-topbar__search {
    width: 100%;
  }

  .app-topbar__tools > :last-child {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
