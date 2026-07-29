<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from "vue";
import { FileSpreadsheet, Search, Star } from "@lucide/vue";
import * as XLSX from "xlsx";

import defaultProductsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import defaultReviewsCsv from "../../../../data/demo/shopee_mock/reviews.csv?raw";
import {
  confirmCommerceOperation,
  listSelectionCandidates,
  requestProductImport,
  requestSelectionCandidate,
} from "@/api/commerce";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { sheetRows } from "@/utils/spreadsheet";
import type { ProductDraftPayload } from "@/types/commerce";

type MarketRow = Record<string, string | number | boolean>;

const marketFieldLabels: Record<string, string> = {
  product_id: "商品 ID（product_id）",
  shop_id: "店铺 ID（shop_id）",
  shop_name: "店铺名称（shop_name）",
  title: "商品名称（title）",
  category_id: "类目 ID（category_id）",
  category_name: "类目名称（category_name）",
  description: "商品描述（description）",
  platform: "平台（platform）",
  site: "站点（site）",
  source_type: "数据来源（source_type）",
  currency: "币种（currency）",
  price: "售价（price）",
  cost: "商品成本（cost）",
  shipping_cost: "物流成本（shipping_cost）",
  sales_count: "销量（sales_count）",
  rating: "评分（rating）",
  review_count: "评论数（review_count）",
  favorite_count: "收藏数（favorite_count）",
  status: "商品状态（status）",
  created_at: "创建时间（created_at）",
  updated_at: "更新时间（updated_at）",
  collected_at: "采集时间（collected_at）",
  is_mock_data: "是否为模拟数据（is_mock_data）",
};

const rows = ref<MarketRow[]>([]);
const reviews = ref<MarketRow[]>([]);
const query = ref("");
const sourceFilter = ref("");
const siteFilter = ref("");
const categoryFilter = ref("");
const statusFilter = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const source = ref("尚未导入");
const reviewSource = ref("尚未导入");
const selected = ref<MarketRow | null>(null);
const candidates = ref(new Set<string>());
const onlyCandidates = ref(false);
const showCandidateList = ref(false);
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
      (!statusFilter.value || String(row.status) === statusFilter.value) &&
      (!onlyCandidates.value || candidates.value.has(rowKey(row))),
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
const selectedReviews = computed(() => {
  const productId = selected.value?.product_id;
  if (!productId) return [];
  return reviews.value.filter((review) => String(review.product_id) === String(productId));
});
const candidateRows = computed(() => rows.value.filter((row) => candidates.value.has(rowKey(row))));
const selectionWorkbenchHref = computed(() => {
  const firstCandidate = candidateRows.value[0];
  const siteMap: Record<string, string> = {
    Singapore: "sg",
    Malaysia: "my",
    Philippines: "ph",
    Thailand: "th",
    Vietnam: "vn",
    Indonesia: "id",
  };
  const params = new URLSearchParams();
  const site = siteFilter.value || String(firstCandidate?.site ?? "");
  const normalizedSite = siteMap[site] ?? site.toLowerCase();
  if (["sg", "my", "ph", "th", "vn", "id"].includes(normalizedSite)) {
    params.set("site", normalizedSite);
  }
  const categoryId = String(firstCandidate?.category_id ?? "");
  if (categoryId) params.set("category", categoryId);
  const queryString = params.toString();
  return `/market/selection${queryString ? `?${queryString}` : ""}`;
});

function normalizedRow(row: MarketRow): MarketRow {
  const isMock = String(row.is_mock_data).toLowerCase() === "true";
  return {
    ...row,
    source_type: row.source_type || (isMock ? "simulated_experiment" : "manual_import"),
    is_mock_data: isMock,
  };
}

function isReviewDataset(importedRows: MarketRow[]): boolean {
  return importedRows.some((row) => row.review_id !== undefined && row.product_id !== undefined);
}

function loadWorkbook(workbook: XLSX.WorkBook, sourceName: string): "products" | "reviews" {
  const importedRows = sheetRows(workbook);
  if (!importedRows.length) throw new Error("文件中没有可读取的工作表或数据");
  const normalizedRows = importedRows.map(normalizedRow);
  if (isReviewDataset(normalizedRows)) {
    reviews.value = normalizedRows;
    reviewSource.value = sourceName;
    return "reviews";
  }
  rows.value = normalizedRows;
  source.value = sourceName;
  selected.value = null;
  currentPage.value = 1;
  return "products";
}

async function readFileWorkbook(file: File): Promise<XLSX.WorkBook> {
  if (file.name.toLowerCase().endsWith(".csv")) {
    return XLSX.read(await file.text(), { type: "string" });
  }
  return XLSX.read(await file.arrayBuffer(), { type: "array" });
}

async function importFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const files = [...(input.files ?? [])];
  if (!files.length) return;
  importMessage.value = "";
  try {
    const results: string[] = [];
    for (const file of files) {
      const workbook = await readFileWorkbook(file);
      const kind = loadWorkbook(workbook, file.name);
      if (
        kind === "products" &&
        window.confirm(`已校验 ${rows.value.length} 条市场商品，确认写入后端数据库吗？`)
      ) {
        const products: ProductDraftPayload[] = rows.value.map((row) => ({
          product_id: row.product_id ? String(row.product_id) : undefined,
          source_shop_id: String(row.shop_id ?? "SHOP001"),
          title: String(row.title ?? row.product_name ?? "未命名商品"),
          category_id: String(row.category_id ?? "MANUAL"),
          category_name: String(row.category_name ?? "未分类"),
          description: String(row.description ?? ""),
          site: String(row.site ?? "Singapore"),
          currency: String(row.currency ?? "SGD"),
          price: Number(row.price ?? 0),
          cost: Number(row.cost ?? 0),
          shipping_cost: Number(row.shipping_cost ?? 0),
          source_type: String(row.source_type ?? "manual_import"),
        }));
        const confirmation = await requestProductImport(products);
        await confirmCommerceOperation(confirmation.id);
      }
      results.push(
        `${file.name}（${kind === "reviews" ? reviews.value.length : rows.value.length} 条）`,
      );
    }
    importMessage.value = `已解析 ${results.join("、")}；确认过的商品批次已写入后端，评论文件保留为关联预览。`;
  } catch (error) {
    importMessage.value = error instanceof Error ? error.message : "文件解析失败";
  } finally {
    input.value = "";
  }
}

function loadProjectDemo(): void {
  loadWorkbook(XLSX.read(defaultProductsCsv, { type: "string" }), "项目演示数据 · products.csv");
  loadWorkbook(XLSX.read(defaultReviewsCsv, { type: "string" }), "项目演示数据 · reviews.csv");
  importMessage.value = `已加载项目内置的 ${rows.value.length} 条 Mock 商品和 ${reviews.value.length} 条关联评论。`;
}

function rowKey(row: MarketRow): string {
  return String(
    row.product_id ??
      row.review_id ??
      row.trend_id ??
      JSON.stringify(Object.values(row).slice(0, 3)),
  );
}

async function loadCandidates(): Promise<void> {
  try {
    candidates.value = new Set((await listSelectionCandidates()).map((item) => item.product_id));
  } catch {
    importMessage.value = "候选清单读取失败，请确认已登录且后端迁移已执行。";
  }
}

async function toggleCandidate(row: MarketRow): Promise<void> {
  const key = rowKey(row);
  const shouldAdd = !candidates.value.has(key);
  const verb = shouldAdd ? "加入" : "移出";
  if (!window.confirm(`确认将“${value(row, "title", "product_name")}”${verb}持久化候选清单？`))
    return;
  try {
    const confirmation = await requestSelectionCandidate(
      key,
      shouldAdd,
      value(row, "title", "product_name"),
      value(row, "source_type"),
      Boolean(row.is_mock_data),
    );
    await confirmCommerceOperation(confirmation.id);
    await loadCandidates();
    importMessage.value = `已${verb}后端候选清单。`;
  } catch (error) {
    importMessage.value = error instanceof Error ? error.message : `${verb}候选失败`;
  }
  if (candidates.value.size === 0) {
    onlyCandidates.value = false;
    showCandidateList.value = false;
  }
}

function value(row: MarketRow, ...keys: string[]): string {
  const key = keys.find((item) => row[item] !== undefined && row[item] !== "");
  return key ? String(row[key]) : "—";
}

function marketFieldLabel(key: string): string {
  return marketFieldLabels[key] ?? key;
}

onMounted(() => {
  loadProjectDemo();
  void loadCandidates();
});
let hasActivated = false;
onActivated(() => {
  if (hasActivated) void loadCandidates();
  hasActivated = true;
});
watch(
  [query, sourceFilter, siteFilter, categoryFilter, statusFilter, onlyCandidates, pageSize],
  () => (currentPage.value = 1),
);
watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages;
});
</script>

<template>
  <PageContainer>
    <header class="heading">
      <div class="heading-actions">
        <SpButton variant="secondary" @click="loadProjectDemo">加载项目演示数据</SpButton>
        <label class="file-button">
          <FileSpreadsheet :size="17" />
          导入 CSV / Excel
          <input type="file" accept=".csv,.xlsx,.xls" multiple @change="importFile" />
        </label>
      </div>
    </header>

    <section class="metrics" aria-label="导入摘要">
      <SpCard padding="md"
        ><strong>{{ rows.length }}</strong
        ><span>商品记录</span></SpCard
      >
      <SpCard padding="md"
        ><strong>{{ reviews.length }}</strong
        ><span>关联评论</span></SpCard
      >
      <button
        class="candidate-metric"
        type="button"
        :aria-expanded="showCandidateList"
        @click="showCandidateList = !showCandidateList"
      >
        <SpCard padding="md"
          ><strong>{{ candidates.size }}</strong
          ><span>选品候选 · 点击查看</span></SpCard
        >
      </button>
      <SpCard padding="md"
        ><strong>{{ source }}</strong
        ><span>商品来源文件</span></SpCard
      >
    </section>
    <p v-if="reviews.length" class="review-source">评论来源：{{ reviewSource }}</p>

    <p v-if="importMessage" class="message" role="status">{{ importMessage }}</p>

    <SpCard v-if="showCandidateList" padding="lg" class="candidate-list">
      <template #header>
        <div class="candidate-list-header">
          <div>
            <strong>选品候选列表</strong>
            <span>候选清单保存在后端，可跨会话和模块继续使用。</span>
          </div>
          <div class="candidate-list-actions">
            <a class="handoff-link" :href="selectionWorkbenchHref">打开智能选品</a>
            <SpButton size="sm" variant="ghost" @click="showCandidateList = false">收起</SpButton>
          </div>
        </div>
      </template>
      <SpEmptyState
        v-if="candidateRows.length === 0"
        title="暂无候选商品"
        description="在市场商品列表中点击“加入候选”。"
      />
      <ul v-else>
        <li v-for="row in candidateRows" :key="rowKey(row)">
          <button type="button" @click="selected = row">
            <strong>{{ value(row, "title", "category_name") }}</strong>
            <span>{{ rowKey(row) }} · {{ value(row, "site") }} · {{ value(row, "price") }}</span>
          </button>
          <SpButton size="sm" variant="ghost" @click="toggleCandidate(row)">移出</SpButton>
        </li>
      </ul>
    </SpCard>

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
          <label class="candidate-filter">
            <input v-model="onlyCandidates" type="checkbox" />
            只看候选
          </label>
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
            <div><span>市场记录 / MARKET RECORD</span><strong>市场商品详情</strong></div>
            <SpButton variant="ghost" @click="selected = null">关闭</SpButton>
          </header>
          <dl>
            <template v-for="(fieldValue, key) in selected" :key="key">
              <dt>{{ marketFieldLabel(String(key)) }}</dt>
              <dd>{{ fieldValue }}</dd>
            </template>
          </dl>
          <section class="review-section" aria-label="商品评论">
            <header>
              <div>
                <span>PRODUCT REVIEWS</span>
                <strong>关联评论（{{ selectedReviews.length }}）</strong>
              </div>
            </header>
            <p v-if="selectedReviews.length === 0" class="review-empty">
              当前评论文件中没有与该商品 ID（product_id）匹配的记录。
            </p>
            <template v-else>
              <article v-for="review in selectedReviews" :key="rowKey(review)" class="review-card">
                <div class="review-meta">
                  <strong>{{ value(review, "rating") }} / 5</strong>
                  <span>{{ value(review, "language") }}</span>
                  <time>{{ value(review, "created_at") }}</time>
                </div>
                <p>{{ value(review, "content") }}</p>
                <p v-if="review.content_zh" class="review-translation">
                  中文：{{ review.content_zh }}
                </p>
                <small>评论 ID：{{ value(review, "review_id") }}</small>
              </article>
            </template>
          </section>
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
  grid-template-columns: repeat(4, minmax(120px, 1fr)) auto;
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
.review-source {
  margin: calc(var(--sp-space-4) * -1) 0 var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-sm);
}
.heading {
  margin-bottom: var(--sp-space-6);
  justify-content: flex-end;
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
.candidate-metric {
  padding: 0;
  color: inherit;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
}
.candidate-metric :deep(.sp-card) {
  height: 100%;
}
.candidate-metric:focus-visible {
  outline: 3px solid var(--sp-color-accent-blue);
  outline-offset: 2px;
  border-radius: var(--sp-radius-card);
}
.candidate-list {
  margin-bottom: var(--sp-space-4);
}
.candidate-list-header,
.candidate-list-header > div {
  display: flex;
  gap: var(--sp-space-3);
}
.candidate-list-header {
  align-items: center;
  justify-content: space-between;
}
.candidate-list-header > div {
  flex-direction: column;
  gap: var(--sp-space-1);
}
.candidate-list-header span {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}
.candidate-list-actions {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
}
.handoff-link {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-primary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
  text-decoration: none;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.handoff-link:hover {
  background: var(--sp-color-accent-blue-soft);
}
.candidate-list ul {
  display: grid;
  gap: var(--sp-space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}
.candidate-list li {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-space-3);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.candidate-list li > button {
  display: grid;
  flex: 1;
  gap: var(--sp-space-1);
  padding: 0;
  color: inherit;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
}
.candidate-list li span {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}
.candidate-filter {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  min-height: 38px;
  padding: 0 var(--sp-space-3);
  white-space: nowrap;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.candidate-filter input {
  width: 16px;
  height: 16px;
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
.review-section {
  padding-top: var(--sp-space-5);
  margin-top: var(--sp-space-5);
  border-top: 1px solid var(--sp-border-subtle);
}
.review-section header div {
  display: grid;
  gap: var(--sp-space-1);
}
.review-section header span {
  color: var(--sp-color-primary);
  font-size: var(--sp-font-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
}
.review-empty {
  color: var(--sp-color-text-secondary);
}
.review-card {
  padding: var(--sp-space-4);
  margin-top: var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-subtle);
  border-radius: var(--sp-radius-card);
}
.review-card p {
  margin: var(--sp-space-3) 0;
  line-height: 1.6;
}
.review-card small,
.review-meta,
.review-translation {
  color: var(--sp-color-text-secondary);
}
.review-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-3);
  align-items: center;
}
.review-meta strong {
  color: var(--sp-color-text);
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
