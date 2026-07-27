<script setup lang="ts">
import { Boxes, LayoutDashboard } from "@lucide/vue";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

const route = useRoute();
const router = useRouter();

const pageName = computed(() => String(route.meta.title ?? "功能模块"));
const moduleName = computed(() => String(route.meta.module ?? "SellPilot"));
const description = computed(() =>
  String(route.meta.description ?? "该模块的业务能力将在后续阶段按计划建设。"),
);

function goToDashboard(): void {
  void router.push("/dashboard");
}
</script>

<template>
  <PageContainer>
    <SpCard class="placeholder-card" padding="lg">
      <div class="placeholder-icon" aria-hidden="true">
        <Boxes :size="32" />
      </div>
      <SpBadge tone="info">{{ moduleName }}</SpBadge>
      <h1>{{ pageName }}</h1>
      <p class="description">{{ description }}</p>
      <p class="status-copy">功能将在对应业务分支实现</p>
      <SpButton @click="goToDashboard">
        <template #icon><LayoutDashboard :size="17" /></template>
        返回经营看板
      </SpButton>
    </SpCard>
  </PageContainer>
</template>

<style scoped>
.placeholder-card {
  display: grid;
  min-height: 430px;
  place-items: center;
  align-content: center;
  text-align: center;
}

.placeholder-icon {
  display: grid;
  width: 76px;
  height: 76px;
  margin-bottom: var(--sp-space-5);
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-card-small);
  place-items: center;
  box-shadow: var(--sp-shadow-card);
}

h1 {
  margin: var(--sp-space-4) 0 var(--sp-space-2);
  font-size: var(--sp-font-xl);
}

.description {
  max-width: 520px;
  margin: 0;
  color: var(--sp-color-text-secondary);
  line-height: 1.8;
}

.status-copy {
  margin: var(--sp-space-5) 0;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-sm);
}
</style>
