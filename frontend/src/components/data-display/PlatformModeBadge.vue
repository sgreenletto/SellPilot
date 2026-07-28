<script setup lang="ts">
import { computed } from "vue";

import SpBadge from "@/components/base/SpBadge.vue";
import type { PlatformPingData } from "@/api/types";

interface Props {
  status: PlatformPingData | null;
  loading?: boolean;
  error?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
});

const view = computed(() => {
  if (props.loading) {
    return { label: "状态检测中", tone: "neutral" as const }
  }
  if (props.error || !props.status) {
    return { label: "后端未连接", tone: "danger" as const }
  }
  if (props.status.reachable) {
    return { label: "后端已连接", tone: "success" as const }
  }
  return { label: "后端未连接", tone: "danger" as const }
});
</script>

<template>
  <SpBadge :tone="view.tone" dot>{{ view.label }}</SpBadge>
</template>
