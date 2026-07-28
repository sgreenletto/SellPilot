<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { FileSpreadsheet, Search, Star } from "@lucide/vue";
import * as XLSX from "xlsx";

import defaultProductsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { sheetRows } from "@/utils/spreadsheet";

type MarketRow = Record<string, string | number | boolean>;

const rows = ref<MarketRow[]>([]);
const query = ref("");
const sourceFilter = ref("");
const siteFilter = ref("");
const categoryFilter = ref("");
const statusFilter = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const source = ref("尚未导入");
const selected = ref<MarketRow | null>(null);
const candidates = ref(new Set<string>());
const importMessage = ref("");

const filteredRows = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return rows.value.filter(
    (row) =>
      (!keyword ||
        Object.values(row).some((value) => String(value).toLowerCase().includes(keyword))) &&
      (!sourceFilter.value || String(row.source_type) === sourceFilter.value) &&
      (!siteFilter.value || String(row.site) === siteFilter.value) &&
      (!categoryFilter.value || String(row.category_name) === categoryFilter.value) &&
      (!statusFilter.value || String(row.status) === statusFilter.value),
  );
});
const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)),
);
const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredRows.value.slice(start, start + pageSize.value);
});
const optionValues = (key: string): string[] =>
  [...new Set(rows.value.map((row) => String(row[key] ?? "")).filter(Boolean))].sort();
const sourceOptions = computed(() => optionValues("source_type"));
const siteOptions = computed(() => optionValues("site"));
const categoryOptions = computed(() => optionValues("category_name"));
const statusOptions = computed(() => optionValues("status"));

function normalizedRow(row: MarketRow): MarketRow {
  const isMock = String(row.is_mock_data).toLowerCase() === "true";
  return {
    ...row,
    source_type: row.source_type || (isMock ? "simulated_experiment" : "manual_import"),
    is_mock_data: isMock,
  };
}

function loadWorkbook(workbook: XLSX.WorkBook, sourceName: string): void {
  const importedRows = sheetRows(workbook);
  if (!importedRows.length) throw new Error("文件中没有可读取的工作表或数据");
  rows.value = importedRows.map(normalizedRow);
  source.value = sourceName;
  selected.value = null;
  candidates.value.clear();
  currentPage.value = 1;
}

async function importFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  importMessage.value = "";
  try {
    const workbook = XLSX.read(await file.arrayBuffer(), { type: "array" });
    loadWorkbook(workbook, file.name);
    importMessage.value = `已在本地解析 ${rows.value.length} 条记录；尚未写入后端。`;
  } catch (error) {
    rows.value = [];
    importMessage.value = error instanceof Error ? error.message : "文件解析失败";
  } finally {
    input.value = "";
  }
}

function loadProjectDemo(): void {
  loadWorkbook(XLSX.read(defaultProductsCsv, { type: "string" }), "项目演示数据 · products.csv");
  importMessage.value = `已加载项目内置的 ${rows.value.length} 条 Mock 商品记录。`;
}

function rowKey(row: MarketRow): string {
  return String(
    row.product_id ??
      row.review_id ??
      row.trend_id ??
      JSON.stringify(Object.values(row).slice(0, 3)),
  );
}

function toggleCandidate(row: MarketRow): void {
  const key = rowKey(row);
  const next = new Set(candidates.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  candidates.value = next;
}

function value(row: MarketRow, ...keys: string[]): string {
  const key = keys.find((item) => row[item] !== undefined && row[item] !== "");
  return key ? String(row[key]) : "—";
}

onMounted(loadProjectDemo);
watch(
  [query, sourceFilter, siteFilter, categoryFilter, statusFilter, pageSize],
  () => (currentPage.value = 1),
);
watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages;
});
</script>

<template>
  <PageContainer>
    <header class="heading">
      <div>
        <p class="eyebrow">MOCK / 公开采集 / 手工导入</p>
        <h1>市场数据</h1>
        <p>导入市场商品或评论 CSV/Excel，并核对来源、指标和候选商品。</p>
      </div>
      <div class="heading-actions">
        <SpButton variant="secondary" @click="loadProjectDemo">加载项目演示数据</SpButton>
        <label class="file-button">
          <FileSpreadsheet :size="17" />
          导入 CSV / Excel
          <input type="file" accept=".csv,.xlsx,.xls" @change="importFile" />
        </label>
      </div>
    </header>

    <section class="metrics" aria-label="导入摘要">
      <SpCard padding="md"
        ><strong>{{ rows.length }}</strong
        ><span>导入记录</span></SpCard
      >
      <SpCard padding="md"
        ><strong>{{ filteredRows.length }}</strong
        ><span>当前结果</span></SpCard
      >
      <SpCard padding="md"
        ><strong>{{ candidates.size }}</strong
        ><span>选品候选</span></SpCard
      >
      <SpCard padding="md"
        ><strong>{{ source }}</strong
        ><span>数据来源文件</span></SpCard
      >
    </section>

    <p v-if="importMessage" class="message" role="status">{{ importMessage }}</p>

    <SpCard padding="lg">
      <template #header>
        <div class="toolbar">
          <SpInput v-model="query" type="search" clearable placeholder="搜索商品、类目或评论">
            <template #prefix><Search :size="16" /></template>
          </SpInput>
          <span>价格、评分、评论数、热度和更新时间均取自导入文件</span>
        </div>
        <div class="filters" aria-label="市场商品筛选">
          <select v-model="sourceFilter" aria-label="来源筛选">
            <option value="">全部来源</option>
            <option v-for="item in sourceOptions" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="siteFilter" aria-label="站点筛选">
            <option value="">全部站点</option>
            <option v-for="item in siteOptions" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="categoryFilter" aria-label="类目筛选">
            <option value="">全部类目</option>
            <option v-for="item in categoryOptions" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="statusFilter" aria-label="状态筛选">
            <option value="">全部状态</option>
            <option v-for="item in statusOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>
      </template>

      <SpEmptyState
        v-if="rows.length === 0"
        title="尚未导入市场数据"
        description="请选择成员二准备的 products、category_trends 或 reviews CSV，也可选择 Excel。"
      >
        <template #icon><FileSpreadsheet :size="24" /></template>
      </SpEmptyState>
      <div v-else class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>商品 / 类目</th>
              <th>来源</th>
              <th>价格</th>
              <th>评分</th>
              <th>评论数</th>
              <th>热度 / 销量</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in paginatedRows" :key="rowKey(row)">
              <td>{{ value(row, "title", "category_name", "content") }}</td>
              <td>{{ value(row, "source_type") }}</td>
              <td>{{ value(row, "price", "average_price") }}</td>
              <td>{{ value(row, "rating") }}</td>
              <td>{{ value(row, "review_count") }}</td>
              <td>{{ value(row, "search_index", "sales_count", "sales_index") }}</td>
              <td>{{ value(row, "updated_at", "date", "collected_at") }}</td>
              <td class="actions">
                <SpButton size="sm" variant="ghost" @click="selected = row">详情</SpButton>
                <SpButton size="sm" variant="secondary" @click="toggleCandidate(row)">
                  <template #icon><Star :size="14" /></template>
                  {{ candidates.has(rowKey(row)) ? "移出候选" : "加入候选" }}
                </SpButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template #footer>
        <div class="pagination">
          <span>共 {{ filteredRows.length }} 条 · 第 {{ currentPage }} / {{ totalPages }} 页</span>
          <div class="pagination-actions">
            <label>
              每页
              <select v-model.number="pageSize" aria-label="每页条数">
                <option :value="10">10 条</option>
                <option :value="20">20 条</option>
                <option :value="50">50 条</option>
              </select>
            </label>
            <SpButton
              size="sm"
              variant="ghost"
              :disabled="currentPage === 1"
              @click="currentPage -= 1"
            >
              上一页
            </SpButton>
            <SpButton
              size="sm"
              variant="secondary"
              :disabled="currentPage === totalPages"
              @click="currentPage += 1"
            >
              下一页
            </SpButton>
          </div>
        </div>
      </template>
    </SpCard>

    <Teleport to="body">
      <div
        v-if="selected"
        class="drawer-backdrop"
        role="presentation"
        @click.self="selected = null"
      >
        <aside class="detail-drawer" role="dialog" aria-modal="true" aria-label="市场商品详情">
          <header class="drawer-header">
            <div><span>MARKET RECORD</span><strong>市场商品详情</strong></div>
            <SpButton variant="ghost" @click="selected = null">关闭</SpButton>
          </header>
          <dl>
            <template v-for="(fieldValue, key) in selected" :key="key">
              <dt>{{ key }}</dt>
              <dd>{{ fieldValue }}</dd>
            </template>
          </dl>
        </aside>
      </div>
    </Teleport>
  </PageContainer>
</template>

<style scoped>
.heading,
.heading-actions,
.toolbar,
.actions,
.pagination,
.pagination-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-3);
}
.filters {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-4);
}
.filters select,
.pagination select {
  min-height: 38px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-text);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.pagination {
  width: 100%;
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-sm);
}
.pagination-actions label {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
}
.heading {
  margin-bottom: var(--sp-space-6);
}
.heading h1 {
  margin: 4px 0;
  font-size: var(--sp-font-page-title);
}
.heading p,
.toolbar span,
.metrics span {
  color: var(--sp-color-text-secondary);
}
.eyebrow {
  color: var(--sp-color-accent-blue) !important;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.1em;
}
.file-button {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  min-height: 42px;
  padding: 0 var(--sp-space-5);
  color: var(--sp-color-text-inverse);
  font-weight: 650;
  cursor: pointer;
  background: var(--sp-color-primary);
  border-radius: var(--sp-radius-control);
}
.file-button input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
}
.metrics :deep(.sp-card__body) {
  display: grid;
  gap: var(--sp-space-1);
}
.metrics strong {
  overflow: hidden;
  font-size: var(--sp-font-lg);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.message {
  padding: var(--sp-space-3);
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
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
  padding: var(--sp-space-3);
  text-align: left;
  border-bottom: 1px solid var(--sp-border-soft);
  white-space: nowrap;
}
th {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.drawer-backdrop {
  position: fixed;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  background: color-mix(in srgb, var(--sp-color-text) 28%, transparent);
  inset: 0;
}
.detail-drawer {
  width: min(560px, 92vw);
  height: 100%;
  padding: var(--sp-space-6);
  overflow-y: auto;
  background: var(--sp-color-surface-strong);
  box-shadow: -24px 0 60px color-mix(in srgb, var(--sp-color-text) 16%, transparent);
  animation: drawer-enter 180ms ease-out;
}
.drawer-header {
  position: sticky;
  top: calc(var(--sp-space-6) * -1);
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-space-4) 0;
  margin-bottom: var(--sp-space-4);
  background: var(--sp-color-surface-strong);
}
.drawer-header > div {
  display: grid;
  gap: var(--sp-space-1);
}
.drawer-header span {
  color: var(--sp-color-accent-blue);
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.1em;
}
@keyframes drawer-enter {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}
dl {
  display: grid;
  grid-template-columns: minmax(120px, 180px) 1fr;
  margin: 0;
}
dt,
dd {
  padding: var(--sp-space-3);
  margin: 0;
  border-bottom: 1px solid var(--sp-border-soft);
  overflow-wrap: anywhere;
}
dt {
  color: var(--sp-color-text-muted);
}
@media (max-width: 900px) {
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .filters {
    grid-template-columns: repeat(2, 1fr);
  }
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
  .filters {
    grid-template-columns: 1fr;
  }
  .pagination {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
