<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Database, RefreshCw } from "@lucide/vue";

import {
  listInventory,
  listOrders,
  listProducts,
  requestInventoryUpdate,
  requestProductStatus,
} from "@/api/commerce";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpSkeleton from "@/components/base/SpSkeleton.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type { CommerceRow, InventoryItem, Product } from "@/types/commerce";

type PageKind = "products" | "inventory" | "orders";

interface Props {
  kind: PageKind;
  title: string;
  description: string;
}

const props = defineProps<Props>();
const rows = ref<CommerceRow[]>([]);
const loading = ref(false);
const error = ref("");
const notice = ref("");
const statusFilter = ref("");
const offset = ref(0);
const pageSize = 20;

type Column = readonly [key: string, label: string];

const columns = computed<Column[]>(() => {
  if (props.kind === "products") {
    return [
      ["title", "商品"],
      ["site", "站点"],
      ["category_name", "类目"],
      ["price", "价格"],
      ["rating", "评分"],
      ["status", "状态"],
    ];
  }
  if (props.kind === "inventory") {
    return [
      ["sku_id", "SKU"],
      ["warehouse_id", "仓库"],
      ["available_stock", "可用库存"],
      ["reserved_stock", "预留"],
      ["safety_stock", "安全库存"],
      ["stock_status", "状态"],
    ];
  }
  return [
    ["order_id", "订单号"],
    ["buyer_id", "买家标识"],
    ["site", "站点"],
    ["total_amount", "金额"],
    ["payment_status", "支付"],
    ["order_status", "订单状态"],
  ];
});

function statusOf(row: CommerceRow): string {
  if ("stock_status" in row) return row.stock_status;
  if ("order_status" in row) return row.order_status;
  return row.status;
}

function badgeStatus(row: CommerceRow): "active" | "pending" | "failed" | "offline" {
  const value = statusOf(row);
  if (value.includes("fail") || value.includes("out_of_stock") || value.includes("exception")) {
    return "failed";
  }
  if (value.includes("pending") || value.includes("low_stock") || value.includes("draft")) {
    return "pending";
  }
  return "active";
}

function displayValue(row: CommerceRow, key: string): string {
  const value = (row as unknown as Record<string, unknown>)[key];
  if (key === "price" && "currency" in row) return `${row.currency} ${value}`;
  if (key === "total_amount" && "currency" in row) return `${row.currency} ${value}`;
  return String(value ?? "—");
}

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  notice.value = "";
  const params = new URLSearchParams({ offset: String(offset.value), limit: String(pageSize) });
  if (statusFilter.value) params.set("status", statusFilter.value);
  try {
    if (props.kind === "products") rows.value = await listProducts(`?${params}`);
    else if (props.kind === "inventory") rows.value = await listInventory(`?${params}`);
    else rows.value = await listOrders(`?${params}`);
  } catch (caught) {
    rows.value = [];
    error.value = caught instanceof Error ? caught.message : "后端未连接";
  } finally {
    loading.value = false;
  }
}

function rowKey(row: CommerceRow): string {
  if ("inventory_id" in row) return row.inventory_id;
  if ("order_id" in row) return row.order_id;
  return row.product_id;
}

function productRow(row: CommerceRow): Product {
  return row as Product;
}

function inventoryRow(row: CommerceRow): InventoryItem {
  return row as InventoryItem;
}

async function toggleProduct(row: Product): Promise<void> {
  loading.value = true;
  try {
    const task = await requestProductStatus(row.product_id, row.status !== "active");
    notice.value = `已创建待确认任务 ${task.id.slice(0, 8)}，确认前不会修改商品。`;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "创建待确认任务失败";
  } finally {
    loading.value = false;
  }
}

async function setInventoryZero(row: InventoryItem): Promise<void> {
  loading.value = true;
  try {
    const task = await requestInventoryUpdate(row.product_id, row.sku_id, 0);
    notice.value = `已创建库存调整任务 ${task.id.slice(0, 8)}，请到任务中心确认。`;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "创建库存任务失败";
  } finally {
    loading.value = false;
  }
}

function nextPage(): void {
  offset.value += pageSize;
  void load();
}

function previousPage(): void {
  offset.value = Math.max(0, offset.value - pageSize);
  void load();
}

onMounted(() => void load());
</script>

<template>
  <PageContainer>
    <header class="page-heading">
      <div>
        <p class="eyebrow">MOCK SHOPEE · MEMBER 2</p>
        <h1>{{ props.title }}</h1>
        <p>{{ props.description }}</p>
      </div>
      <SpButton variant="secondary" :loading="loading" @click="load">
        <template #icon><RefreshCw :size="16" /></template>
        刷新
      </SpButton>
    </header>

    <SpCard padding="lg">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>模拟业务数据</strong>
            <span>全部记录均标记为 Mock</span>
          </div>
          <input
            v-model="statusFilter"
            class="status-input"
            placeholder="输入状态筛选"
            aria-label="状态筛选"
            @keyup.enter="
              offset = 0;
              load();
            "
          />
        </div>
      </template>

      <p v-if="notice" class="notice" role="status">{{ notice }}</p>
      <SpEmptyState v-if="error" title="后端未连接或需要登录" :description="error">
        <template #icon><Database :size="24" /></template>
        <template #action><SpButton @click="load">重新连接</SpButton></template>
      </SpEmptyState>
      <div v-else-if="loading" class="loading-list">
        <SpSkeleton v-for="index in 6" :key="index" />
      </div>
      <SpEmptyState
        v-else-if="rows.length === 0"
        title="暂无数据"
        description="请先运行模拟数据导入命令，或调整筛选条件。"
      >
        <template #icon><Database :size="24" /></template>
      </SpEmptyState>
      <div v-else class="table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="column in columns" :key="column[0]">{{ column[1] }}</th>
              <th v-if="props.kind !== 'orders'">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="rowKey(row)">
              <td v-for="column in columns" :key="column[0]">
                <StatusBadge
                  v-if="
                    column[0] === 'status' ||
                    column[0] === 'stock_status' ||
                    column[0] === 'order_status'
                  "
                  :status="badgeStatus(row)"
                  :label="displayValue(row, column[0])"
                />
                <span v-else>{{ displayValue(row, column[0]) }}</span>
              </td>
              <td v-if="props.kind === 'products'">
                <SpButton size="sm" variant="ghost" @click="toggleProduct(productRow(row))">
                  {{ productRow(row).status === "active" ? "申请下架" : "申请上架" }}
                </SpButton>
              </td>
              <td v-else-if="props.kind === 'inventory'">
                <SpButton size="sm" variant="ghost" @click="setInventoryZero(inventoryRow(row))">
                  申请清零
                </SpButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <template #footer>
        <div class="pagination">
          <span>第 {{ Math.floor(offset / pageSize) + 1 }} 页</span>
          <div>
            <SpButton size="sm" variant="ghost" :disabled="offset === 0" @click="previousPage">
              上一页
            </SpButton>
            <SpButton
              size="sm"
              variant="secondary"
              :disabled="rows.length < pageSize"
              @click="nextPage"
            >
              下一页
            </SpButton>
          </div>
        </div>
      </template>
    </SpCard>
  </PageContainer>
</template>

<style scoped>
.page-heading,
.toolbar,
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-4);
}
.page-heading {
  margin-bottom: var(--sp-space-6);
}
.page-heading h1 {
  margin: 4px 0;
  font-size: var(--sp-font-page-title);
}
.page-heading p,
.toolbar span {
  color: var(--sp-color-text-secondary);
}
.eyebrow {
  color: var(--sp-color-accent-blue) !important;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.12em;
}
.toolbar > div {
  display: grid;
  gap: var(--sp-space-1);
}
.status-input {
  min-height: 40px;
  padding: 0 var(--sp-space-4);
  color: var(--sp-color-text);
  background: var(--sp-color-surface-strong);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--sp-font-sm);
}
th,
td {
  padding: var(--sp-space-4);
  text-align: left;
  border-bottom: 1px solid var(--sp-border-soft);
  white-space: nowrap;
}
th {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 700;
}
tbody tr:hover {
  background: var(--sp-color-surface-hover);
}
.loading-list {
  display: grid;
  gap: var(--sp-space-5);
  padding: var(--sp-space-5) 0;
}
.notice {
  padding: var(--sp-space-3) var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-control);
}
.pagination > div {
  display: flex;
  gap: var(--sp-space-2);
}
@media (max-width: 767px) {
  .page-heading,
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
