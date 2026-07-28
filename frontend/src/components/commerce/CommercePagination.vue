<script setup lang="ts">
import { computed } from "vue";

import SpButton from "@/components/base/SpButton.vue";

interface Props {
  currentPage: number;
  pageSize: number;
  total: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  "update:currentPage": [value: number];
  "update:pageSize": [value: number];
}>();

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));

function updatePageSize(event: Event): void {
  emit("update:pageSize", Number((event.target as HTMLSelectElement).value));
  emit("update:currentPage", 1);
}
</script>

<template>
  <div class="commerce-pagination">
    <span>共 {{ props.total }} 条 · 第 {{ props.currentPage }} / {{ totalPages }} 页</span>
    <div class="commerce-pagination__actions">
      <label>
        每页
        <select :value="props.pageSize" aria-label="每页条数" @change="updatePageSize">
          <option :value="10">10 条</option>
          <option :value="20">20 条</option>
          <option :value="50">50 条</option>
        </select>
      </label>
      <SpButton
        size="sm"
        variant="ghost"
        :disabled="props.currentPage === 1"
        @click="emit('update:currentPage', props.currentPage - 1)"
      >
        上一页
      </SpButton>
      <SpButton
        size="sm"
        variant="secondary"
        :disabled="props.currentPage === totalPages"
        @click="emit('update:currentPage', props.currentPage + 1)"
      >
        下一页
      </SpButton>
    </div>
  </div>
</template>

<style scoped>
.commerce-pagination,
.commerce-pagination__actions,
.commerce-pagination__actions label {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
}

.commerce-pagination {
  justify-content: space-between;
  width: 100%;
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-sm);
}

select {
  min-height: 36px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-text);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}

@media (max-width: 767px) {
  .commerce-pagination {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
