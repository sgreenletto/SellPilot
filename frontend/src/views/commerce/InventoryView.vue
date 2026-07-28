<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { AlertTriangle, Boxes, RefreshCw } from "@lucide/vue";

import inventoryCsv from "../../../../data/demo/shopee_mock/inventory.csv?raw";
import productsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import skusCsv from "../../../../data/demo/shopee_mock/skus.csv?raw";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import CommercePagination from "@/components/commerce/CommercePagination.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { csvRows } from "@/utils/spreadsheet";

type Row = Record<string, string | number>;
const parse = (csv: string): Row[] => {
  return csvRows(csv) as Row[];
};

const rows = ref(parse(inventoryCsv));
const listingDrafts = ref([
  ...parse(productsCsv).slice(0, 4),
  {
    product_id: "DRAFT-INCOMPLETE",
    title: "字段缺失演示草稿",
    category_name: "待补充类目",
    currency: "SGD",
    price: "",
    status: "draft",
  },
]);
const skus = parse(skusCsv);
const lowOnly = ref(false);
const draftPage = ref(1);
const draftPageSize = ref(10);
const inventoryPage = ref(1);
const inventoryPageSize = ref(10);
const selected = ref(new Set<string>());
const amount = ref(10);
const notice = ref("");
const ledger = ref<string[]>([]);

const visible = computed(() =>
  rows.value.filter(
    (row) => !lowOnly.value || Number(row.available_stock) <= Number(row.safety_stock),
  ),
);
const paginatedDrafts = computed(() => {
  const start = (draftPage.value - 1) * draftPageSize.value;
  return listingDrafts.value.slice(start, start + draftPageSize.value);
});
const paginatedInventory = computed(() => {
  const start = (inventoryPage.value - 1) * inventoryPageSize.value;
  return visible.value.slice(start, start + inventoryPageSize.value);
});
const lowCount = computed(
  () => rows.value.filter((row) => Number(row.available_stock) <= Number(row.safety_stock)).length,
);

function skuOf(row: Row): Row | undefined {
  return skus.find((sku) => sku.sku_id === row.sku_id);
}
function toggle(id: string): void {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}
function adjust(targets: Row[]): void {
  if (targets.length === 0) return;
  for (const row of targets) {
    const before = Number(row.available_stock);
    row.available_stock = Math.max(0, before + Number(amount.value));
    ledger.value.unshift(
      `${new Date().toLocaleTimeString()} · ${row.sku_id} · ${before} → ${row.available_stock}`,
    );
  }
  notice.value = `已在前端预演 ${targets.length} 项库存调整；正式执行仍需创建待确认任务。`;
}
function replenish(row: Row): number {
  return Math.max(Number(row.safety_stock) * 3 - Number(row.available_stock), 0);
}
function completeness(row: Row): number {
  return (
    [row.title, row.category_name, row.price, skuOfProduct(row)?.sku_id].filter(Boolean).length * 25
  );
}
function skuOfProduct(product: Row): Row | undefined {
  return skus.find((sku) => sku.product_id === product.product_id);
}
function simulateListing(row: Row, publish: boolean): void {
  const complete = completeness(row) === 100;
  row.listing_result = !publish ? "模拟下架成功" : complete ? "模拟上架成功" : "模拟上架失败";
  notice.value = `${row.product_id}：${row.listing_result}。这只是 Mock 结果展示，未修改平台数据。`;
}

watch([lowOnly, inventoryPageSize], () => (inventoryPage.value = 1));
watch(draftPageSize, () => (draftPage.value = 1));
</script>

<template>
  <PageContainer>
    <header class="heading">
      <div>
        <p class="eyebrow">MOCK SHOPEE · 上架与库存</p>
        <h1>库存工作台</h1>
        <p>检查 SKU 库存、预警阈值，预演单项与批量调整并查看流水。</p>
      </div>
      <SpButton variant="secondary" @click="rows = parse(inventoryCsv)"
        ><template #icon><RefreshCw :size="16" /></template>恢复项目数据</SpButton
      >
    </header>
    <section class="metrics">
      <SpCard padding="md"
        ><strong>{{ rows.length }}</strong
        ><span>库存记录</span></SpCard
      ><SpCard padding="md"
        ><strong>{{ lowCount }}</strong
        ><span>低库存预警</span></SpCard
      ><SpCard padding="md"
        ><strong>{{ selected.size }}</strong
        ><span>已选择 SKU</span></SpCard
      >
    </section>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <SpCard class="drafts" padding="lg">
      <template #header><strong>上架草稿、预览与完整性检查</strong></template>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>商品预览</th>
              <th>完整度</th>
              <th>SKU</th>
              <th>价格</th>
              <th>库存检查</th>
              <th>模拟结果</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="draft in paginatedDrafts" :key="String(draft.product_id)">
              <td>
                <strong>{{ draft.title }}</strong
                ><small>{{ draft.category_name }}</small>
              </td>
              <td>{{ completeness(draft) }}%</td>
              <td>{{ skuOfProduct(draft)?.sku_id || "缺失" }}</td>
              <td>{{ draft.currency }} {{ draft.price || "缺失" }}</td>
              <td>
                {{
                  rows.find((item) => item.sku_id === skuOfProduct(draft)?.sku_id)
                    ?.available_stock ?? "缺失"
                }}
              </td>
              <td>{{ draft.listing_result || "待模拟" }}</td>
              <td>
                <div class="batch">
                  <SpButton size="sm" variant="secondary" @click="simulateListing(draft, true)"
                    >模拟上架</SpButton
                  ><SpButton size="sm" variant="ghost" @click="simulateListing(draft, false)"
                    >模拟下架</SpButton
                  >
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <CommercePagination
          v-model:current-page="draftPage"
          v-model:page-size="draftPageSize"
          :total="listingDrafts.length"
        />
      </template>
    </SpCard>
    <SpCard padding="lg">
      <template #header
        ><div class="toolbar">
          <label><input v-model="lowOnly" type="checkbox" />只看低库存</label>
          <div class="batch">
            <input v-model.number="amount" type="number" aria-label="库存调整数量" /><SpButton
              size="sm"
              :disabled="selected.size === 0"
              @click="adjust(rows.filter((row) => selected.has(String(row.inventory_id))))"
              >批量调整</SpButton
            >
          </div>
        </div></template
      >
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th></th>
              <th>SKU / 规格</th>
              <th>仓库</th>
              <th>可用</th>
              <th>预留</th>
              <th>阈值</th>
              <th>状态</th>
              <th>补货建议</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in paginatedInventory" :key="String(row.inventory_id)">
              <td>
                <input
                  type="checkbox"
                  :checked="selected.has(String(row.inventory_id))"
                  @change="toggle(String(row.inventory_id))"
                />
              </td>
              <td>
                <strong>{{ row.sku_id }}</strong
                ><small>{{ skuOf(row)?.variation_name }}: {{ skuOf(row)?.variation_value }}</small>
              </td>
              <td>{{ row.warehouse_name }}</td>
              <td>{{ row.available_stock }}</td>
              <td>{{ row.reserved_stock }}</td>
              <td>{{ row.safety_stock }}</td>
              <td>
                <StatusBadge
                  :status="
                    Number(row.available_stock) <= Number(row.safety_stock) ? 'failed' : 'active'
                  "
                  :label="String(row.stock_status)"
                />
              </td>
              <td>{{ replenish(row) ? `建议补 ${replenish(row)}` : "库存充足" }}</td>
              <td>
                <SpButton size="sm" variant="ghost" @click="adjust([row])"
                  >调整 {{ amount }}</SpButton
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <CommercePagination
          v-model:current-page="inventoryPage"
          v-model:page-size="inventoryPageSize"
          :total="visible.length"
        />
      </template>
    </SpCard>
    <SpCard class="ledger" padding="lg"
      ><template #header
        ><div class="toolbar"><strong>库存变更流水（本次前端预演）</strong><Boxes :size="18" /></div
      ></template>
      <p v-if="ledger.length === 0"><AlertTriangle :size="16" />尚无调整记录</p>
      <ol v-else>
        <li v-for="item in ledger" :key="item">{{ item }}</li>
      </ol></SpCard
    >
  </PageContainer>
</template>

<style scoped>
.heading,
.toolbar,
.batch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-3);
}
.heading {
  margin-bottom: var(--sp-space-6);
}
.heading h1 {
  margin: 4px 0;
  font-size: var(--sp-font-page-title);
}
.heading p,
.metrics span,
small {
  color: var(--sp-color-text-secondary);
}
.eyebrow {
  color: var(--sp-color-accent-blue) !important;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.1em;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
}
.metrics :deep(.sp-card__body) {
  display: grid;
  gap: var(--sp-space-1);
}
.metrics strong {
  font-size: var(--sp-font-xl);
}
.notice {
  padding: var(--sp-space-3);
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-control);
}
.drafts {
  margin-bottom: var(--sp-space-5);
}
input[type="number"] {
  width: 90px;
  min-height: 36px;
  padding: 0 var(--sp-space-3);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.table-scroll {
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--sp-font-sm);
}
th,
td {
  padding: var(--sp-space-3);
  text-align: left;
  border-bottom: 1px solid var(--sp-border-soft);
  white-space: nowrap;
}
td:nth-child(2) {
  display: grid;
  gap: 3px;
}
.ledger {
  margin-top: var(--sp-space-5);
}
.ledger p {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  color: var(--sp-color-text-muted);
}
ol {
  color: var(--sp-color-text-secondary);
}
@media (max-width: 767px) {
  .heading,
  .toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .metrics {
    grid-template-columns: 1fr;
  }
}
</style>
