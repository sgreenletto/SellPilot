<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { FileSpreadsheet, Search, Star } from "@lucide/vue";
import * as XLSX from "xlsx";

import defaultProductsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

type MarketRow = Record<string, string | number | boolean>;

const rows = ref<MarketRow[]>([]);
const query = ref("");
const source = ref("尚未导入");
const selected = ref<MarketRow | null>(null);
const candidates = ref(new Set<number>());
const importMessage = ref("");

const filteredRows = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (!keyword) return rows.value;
  return rows.value.filter((row) =>
    Object.values(row).some((value) => String(value).toLowerCase().includes(keyword)),
  );
});

function normalizedRow(row: MarketRow): MarketRow {
  return {
    ...row,
    source_type: row.source_type || "manual_import",
    is_mock_data: String(row.is_mock_data).toLowerCase() === "true",
  };
}

function loadWorkbook(workbook: XLSX.WorkBook, sourceName: string): void {
  const sheet = workbook.Sheets[workbook.SheetNames[0] ?? ""];
  if (!sheet) throw new Error("文件中没有可读取的工作表");
  rows.value = XLSX.utils.sheet_to_json<MarketRow>(sheet, { defval: "" }).map(normalizedRow);
  source.value = sourceName;
  selected.value = null;
  candidates.value.clear();
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

function toggleCandidate(index: number): void {
  const next = new Set(candidates.value);
  if (next.has(index)) next.delete(index);
  else next.add(index);
  candidates.value = next;
}

function value(row: MarketRow, ...keys: string[]): string {
  const key = keys.find((item) => row[item] !== undefined && row[item] !== "");
  return key ? String(row[key]) : "—";
}

onMounted(loadProjectDemo);
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
            <tr v-for="(row, index) in filteredRows" :key="index">
              <td>{{ value(row, "title", "category_name", "content") }}</td>
              <td>{{ value(row, "source_type") }}</td>
              <td>{{ value(row, "price", "average_price") }}</td>
              <td>{{ value(row, "rating") }}</td>
              <td>{{ value(row, "review_count") }}</td>
              <td>{{ value(row, "search_index", "sales_count", "sales_index") }}</td>
              <td>{{ value(row, "updated_at", "date", "collected_at") }}</td>
              <td class="actions">
                <SpButton size="sm" variant="ghost" @click="selected = row">详情</SpButton>
                <SpButton size="sm" variant="secondary" @click="toggleCandidate(index)">
                  <template #icon><Star :size="14" /></template>
                  {{ candidates.has(index) ? "移出候选" : "加入候选" }}
                </SpButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </SpCard>

    <SpCard v-if="selected" class="detail" padding="lg">
      <template #header>
        <div class="toolbar">
          <strong>市场商品详情抽屉</strong
          ><SpButton variant="ghost" @click="selected = null">关闭</SpButton>
        </div>
      </template>
      <dl>
        <template v-for="(fieldValue, key) in selected" :key="key">
          <dt>{{ key }}</dt>
          <dd>{{ fieldValue }}</dd>
        </template>
      </dl>
    </SpCard>
  </PageContainer>
</template>

<style scoped>
.heading,
.heading-actions,
.toolbar,
.actions {
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
.detail {
  margin-top: var(--sp-space-5);
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
