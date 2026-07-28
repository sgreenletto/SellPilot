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
    return { label: "状态检测中", tone: "neutral" as const };
  }
  if (props.error || !props.status) {
    return { label: "后端未连接", tone: "danger" as const };
  }
  if (props.status.adapter === "mock") {
    return {
      label: props.status.reachable ? "后端已连接" : "Mock 不可用",
      tone: props.status.reachable ? ("success" as const) : ("danger" as const),
    };
  }
  return {
    label:
      props.status.configured && props.status.reachable
        ? "Real 模式 · 后端已连接"
        : "Real Stub 未配置 · 后端未连接",
    tone:
      props.status.configured && props.status.reachable
        ? ("success" as const)
        : ("warning" as const),
  };
});
</script>

<template>
  <SpBadge :tone="view.tone" dot>{{ view.label }}</SpBadge>
</template>
