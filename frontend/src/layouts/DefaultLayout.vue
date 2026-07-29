<script setup lang="ts">
import AppShell from "@/components/layout/AppShell.vue";
</script>

<template>
  <AppShell>
    <RouterView v-slot="{ Component, route }">
      <KeepAlive :max="4">
        <component :is="Component" v-if="route.meta.keepAlive" :key="String(route.name)" />
      </KeepAlive>
      <component :is="Component" v-if="!route.meta.keepAlive" :key="route.fullPath" />
    </RouterView>
  </AppShell>
</template>
