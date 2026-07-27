<script setup lang="ts">
import { Ellipsis } from "@lucide/vue";

import SpAvatar from "@/components/base/SpAvatar.vue";
import SpIconButton from "@/components/base/SpIconButton.vue";
import RiskIndicator from "@/components/data-display/RiskIndicator.vue";
import type { RiskOperation } from "@/types/dashboard";

interface Props {
  items: RiskOperation[];
}

const props = defineProps<Props>();

const currency = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  maximumFractionDigits: 0,
});
</script>

<template>
  <div class="risk-table-wrap">
    <table class="risk-table">
      <thead>
        <tr>
          <th>事项</th>
          <th>风险</th>
          <th>关键因素</th>
          <th>预计影响</th>
          <th>AI 建议</th>
          <th><span class="sp-visually-hidden">操作</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in props.items" :key="item.id">
          <td>
            <div class="risk-table__subject">
              <SpAvatar :initials="item.initials" :gradient="item.tone" size="sm" />
              <span>
                <strong>{{ item.name }}</strong>
                <small>{{ item.code }} · 模拟商品</small>
              </span>
            </div>
          </td>
          <td><RiskIndicator :value="item.risk" /></td>
          <td>{{ item.factor }}</td>
          <td class="risk-table__impact">{{ currency.format(item.impact) }}</td>
          <td>{{ item.suggestion }}</td>
          <td>
            <SpIconButton :ariaLabel="`查看${item.name}${item.code}操作`" size="sm">
              <Ellipsis :size="18" />
            </SpIconButton>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.risk-table-wrap {
  width: 100%;
  overflow-x: auto;
}

.risk-table {
  width: 100%;
  min-width: 920px;
  border-collapse: collapse;
}

.risk-table th {
  padding: 0 var(--sp-space-4) var(--sp-space-3);
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 600;
  text-align: left;
}

.risk-table td {
  padding: var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  border-top: 1px solid var(--sp-border-soft);
  transition: background var(--sp-transition-fast);
}

.risk-table tbody tr:hover td {
  background: var(--sp-color-surface-hover);
}

.risk-table__subject {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
}

.risk-table__subject > span {
  display: grid;
  gap: var(--sp-space-1);
}

.risk-table__subject strong {
  color: var(--sp-color-text);
  font-weight: 700;
}

.risk-table__subject small {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.risk-table__impact {
  color: var(--sp-color-text) !important;
  font-weight: 750;
  white-space: nowrap;
}
</style>
