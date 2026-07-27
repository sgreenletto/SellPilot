<script setup lang="ts">
import SpBadge from "@/components/base/SpBadge.vue";

interface Props {
  status: "active" | "pending" | "failed" | "offline";
  label: string;
}

const props = defineProps<Props>();

const toneMap = {
  active: "success",
  pending: "warning",
  failed: "danger",
  offline: "neutral",
} as const;
</script>

<template>
  <SpBadge :tone="toneMap[props.status]" dot>{{ props.label }}</SpBadge>
</template>
