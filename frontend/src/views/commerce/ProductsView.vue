<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Copy, FileSpreadsheet, Image as ImageIcon, Plus, Search } from "@lucide/vue";
import * as XLSX from "xlsx";

import inventoryCsv from "../../../../data/demo/shopee_mock/inventory.csv?raw";
import productsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import skusCsv from "../../../../data/demo/shopee_mock/skus.csv?raw";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import CommercePagination from "@/components/commerce/CommercePagination.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { csvRows, sheetRows } from "@/utils/spreadsheet";

type Row = Record<string, string | number>;

function readCsv(csv: string): Row[] {
  return csvRows(csv) as Row[];
}

const products = ref<Row[]>(readCsv(productsCsv));
const skus = readCsv(skusCsv);
const inventory = readCsv(inventoryCsv);
const query = ref("");
const status = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const selected = ref<Row | null>(products.value[0] ?? null);
const editing = ref(false);
const activeLanguage = ref("en");
const languageOptions = [
  { code: "en", label: "English" },
  { code: "zh-CN", label: "简体中文" },
  { code: "zh-TW", label: "繁體中文" },
  { code: "ms", label: "Bahasa Melayu" },
  { code: "id", label: "Bahasa Indonesia" },
  { code: "th", label: "ไทย" },
  { code: "vi", label: "Tiếng Việt" },
  { code: "tl", label: "Filipino" },
  { code: "pt-BR", label: "Português (Brasil)" },
] as const;
interface LocalizedVersion {
  title?: string;
  description?: string;
}
const localizedByProduct = ref<Record<string, Record<string, LocalizedVersion>>>({});
const notice = ref("");
const history = ref<string[]>(["已从项目 Mock 数据包载入商品"]);

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  return products.value.filter((product) => {
    const matchesKeyword =
      !keyword ||
      [product.title, product.product_id, product.category_name].some((value) =>
        String(value).toLowerCase().includes(keyword),
      );
    return matchesKeyword && (!status.value || product.status === status.value);
  });
});
const paginated = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filtered.value.slice(start, start + pageSize.value);
});

const selectedSku = computed(() =>
  skus.find((sku) => sku.product_id === selected.value?.product_id),
);
const selectedInventory = computed(() =>
  inventory.find((item) => item.sku_id === selectedSku.value?.sku_id),
);

function defaultLocalizedTitle(language: string): string {
  const title = String(selected.value?.title ?? "未命名商品");
  return language === "en" ? title : "";
}

function defaultLocalizedDescription(language: string): string {
  const description = String(selected.value?.description ?? "");
  return language === "en" ? description : "";
}

function localizedField(field: keyof LocalizedVersion, fallback: () => string) {
  return computed({
    get: () => {
      const productId = String(selected.value?.product_id ?? "");
      return localizedByProduct.value[productId]?.[activeLanguage.value]?.[field] ?? fallback();
    },
    set: (text: string) => {
      const productId = String(selected.value?.product_id ?? "");
      if (!productId) return;
      localizedByProduct.value[productId] = {
        ...localizedByProduct.value[productId],
        [activeLanguage.value]: {
          ...localizedByProduct.value[productId]?.[activeLanguage.value],
          [field]: text,
        },
      };
      if (activeLanguage.value === "en" && selected.value) selected.value[field] = text;
    },
  });
}

const localizedTitle = localizedField("title", () => defaultLocalizedTitle(activeLanguage.value));
const localizedDescription = localizedField("description", () =>
  defaultLocalizedDescription(activeLanguage.value),
);
const activeLanguageLabel = computed(
  () =>
    languageOptions.find((language) => language.code === activeLanguage.value)?.label ??
    activeLanguage.value,
);
const hasLocalizedContent = computed(
  () => Boolean(localizedTitle.value.trim()) && Boolean(localizedDescription.value.trim()),
);

async function importProducts(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const workbook = XLSX.read(await file.arrayBuffer(), { type: "array" });
  const importedRows = sheetRows(workbook) as Row[];
  if (!importedRows.length) return;
  products.value = importedRows;
  selected.value = products.value[0] ?? null;
  notice.value = `已在前端导入 ${products.value.length} 条商品，尚未写入后端。`;
  history.value.unshift(`导入文件 ${file.name}`);
  input.value = "";
}

function createDraft(): void {
  const draft: Row = {
    product_id: `LOCAL-${Date.now()}`,
    title: "未命名商品",
    category_name: "未分类",
    site: "Singapore",
    currency: "SGD",
    price: 0,
    status: "draft",
    description: "",
    is_mock_data: "true",
  };
  products.value.unshift(draft);
  selected.value = draft;
  editing.value = true;
  history.value.unshift("手工新建本地草稿");
}

function copyProduct(): void {
  if (!selected.value) return;
  const copy = {
    ...selected.value,
    product_id: `COPY-${Date.now()}`,
    title: `${selected.value.title}（副本）`,
    status: "draft",
  };
  products.value.unshift(copy);
  selected.value = copy;
  editing.value = true;
  history.value.unshift(`复制商品 ${copy.product_id}`);
}

function saveDraft(): void {
  editing.value = false;
  notice.value = "草稿已保存在当前浏览器会话；后端商品写入接口尚未开放。";
  history.value.unshift(`保存草稿 ${selected.value?.product_id}`);
}

function badge(value: unknown): "active" | "pending" | "failed" {
  const text = String(value);
  if (text.includes("fail")) return "failed";
  if (text.includes("draft") || text.includes("pending")) return "pending";
  return "active";
}

watch([query, status, pageSize], () => (currentPage.value = 1));
</script>

<template>
  <PageContainer>
    <header class="heading">
      <div>
        <p class="eyebrow">MOCK SHOPEE · 商品运营</p>
        <h1>商品管理</h1>
        <p>管理商品资料、草稿、SKU、多语言内容与操作历史。</p>
      </div>
      <div class="actions">
        <label class="file-button"
          ><FileSpreadsheet :size="16" />导入 CSV / Excel<input
            type="file"
            accept=".csv,.xlsx,.xls"
            @change="importProducts"
        /></label>
        <SpButton @click="createDraft"
          ><template #icon><Plus :size="16" /></template>手工新建</SpButton
        >
      </div>
    </header>

    <p v-if="notice" class="notice" role="status">{{ notice }}</p>

    <div class="workspace">
      <SpCard padding="lg">
        <template #header>
          <div class="filters">
            <SpInput v-model="query" type="search" clearable placeholder="搜索名称、商品 ID 或类目"
              ><template #prefix><Search :size="16" /></template
            ></SpInput>
            <select v-model="status" aria-label="商品状态筛选">
              <option value="">全部状态</option>
              <option value="active">在售</option>
              <option value="draft">草稿</option>
              <option value="inactive">下架</option>
            </select>
          </div>
        </template>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>商品</th>
                <th>站点</th>
                <th>价格</th>
                <th>库存</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="product in paginated"
                :key="String(product.product_id)"
                :class="{ selected: selected?.product_id === product.product_id }"
                @click="selected = product"
              >
                <td>
                  <strong>{{ product.title }}</strong
                  ><small>{{ product.product_id }} · {{ product.category_name }}</small>
                </td>
                <td>{{ product.site }}</td>
                <td>{{ product.currency }} {{ product.price }}</td>
                <td>
                  {{
                    inventory.find(
                      (item) =>
                        item.sku_id ===
                        skus.find((sku) => sku.product_id === product.product_id)?.sku_id,
                    )?.available_stock ?? "—"
                  }}
                </td>
                <td>
                  <StatusBadge :status="badge(product.status)" :label="String(product.status)" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <template #footer>
          <CommercePagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="filtered.length"
          />
        </template>
      </SpCard>

      <SpCard v-if="selected" padding="lg" class="detail">
        <template #header
          ><div class="detail-header">
            <strong>商品详情</strong>
            <div class="actions">
              <SpButton size="sm" variant="ghost" @click="copyProduct"
                ><template #icon><Copy :size="14" /></template>复制</SpButton
              ><SpButton size="sm" variant="secondary" @click="editing = !editing">{{
                editing ? "取消编辑" : "编辑"
              }}</SpButton>
            </div>
          </div></template
        >
        <div class="form-grid">
          <label class="wide">
            当前内容语言
            <select v-model="activeLanguage">
              <option
                v-for="language in languageOptions"
                :key="language.code"
                :value="language.code"
              >
                {{ language.label }}
              </option>
            </select>
          </label>
          <div v-if="activeLanguage !== 'en'" class="translation-status wide" role="status">
            <div>
              <strong>{{ hasLocalizedContent ? "人工译文" : "待翻译" }}</strong>
              <span v-if="hasLocalizedContent">
                当前{{ activeLanguageLabel }}内容保存在浏览器会话中，尚未写入后端。
              </span>
              <span v-else>
                暂无{{
                  activeLanguageLabel
                }}内容；机器翻译接口待成员三接入，也可以进入编辑模式人工补充。
              </span>
            </div>
            <SpButton size="sm" variant="secondary" disabled>机器翻译服务未配置</SpButton>
          </div>
          <label
            >商品名称<input
              v-model="localizedTitle"
              :disabled="!editing"
              :placeholder="
                activeLanguage === 'en' ? '商品名称' : `待补充${activeLanguageLabel}名称`
              "
          /></label>
          <label>类目<input v-model="selected.category_name" :disabled="!editing" /></label>
          <label>价格<input v-model="selected.price" :disabled="!editing" type="number" /></label>
          <label>状态<input v-model="selected.status" disabled /></label>
          <label class="wide"
            >商品描述<textarea
              v-model="localizedDescription"
              :disabled="!editing"
              :placeholder="
                activeLanguage === 'en' ? '商品描述' : `待补充${activeLanguageLabel}描述`
              "
            />
          </label>
        </div>
        <SpButton v-if="editing" block @click="saveDraft">保存为草稿</SpButton>

        <h3>SKU、规格、价格和库存</h3>
        <dl>
          <dt>Seller SKU</dt>
          <dd>{{ selectedSku?.seller_sku ?? "待创建" }}</dd>
          <dt>规格</dt>
          <dd>
            {{
              selectedSku
                ? `${selectedSku.variation_name}: ${selectedSku.variation_value}`
                : "待补充"
            }}
          </dd>
          <dt>SKU 价格</dt>
          <dd>{{ selectedSku?.price ?? "待补充" }}</dd>
          <dt>可用库存 / 预警阈值</dt>
          <dd>
            {{ selectedInventory?.available_stock ?? 0 }} /
            {{ selectedInventory?.safety_stock ?? 0 }}
          </dd>
          <dt>图片</dt>
          <dd>以下为合成 Mock 占位图，不代表真实商品素材</dd>
        </dl>

        <div class="mock-gallery" aria-label="Mock 商品图片预览">
          <div v-for="index in 3" :key="index" class="mock-image">
            <ImageIcon :size="28" />
            <strong>{{ selected.category_name }}</strong>
            <span>Mock 视图 {{ index }}</span>
          </div>
        </div>

        <h3>操作历史</h3>
        <ol>
          <li v-for="item in history.slice(0, 6)" :key="item">{{ item }}</li>
        </ol>
      </SpCard>
      <SpEmptyState v-else title="请选择商品" description="从左侧商品列表选择一条记录查看详情。" />
    </div>
  </PageContainer>
</template>

<style scoped>
.heading,
.actions,
.filters,
.detail-header {
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
small {
  color: var(--sp-color-text-secondary);
}
.eyebrow {
  color: var(--sp-color-accent-blue) !important;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.1em;
}
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(340px, 0.8fr);
  gap: var(--sp-space-5);
  align-items: start;
}
.file-button {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  min-height: 42px;
  padding: 0 var(--sp-space-4);
  font-weight: 650;
  cursor: pointer;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.file-button input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
.notice {
  padding: var(--sp-space-3);
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-control);
}
.translation-status {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-accent-blue-soft);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.translation-status div {
  display: grid;
  gap: var(--sp-space-1);
}
.translation-status strong {
  color: var(--sp-color-text);
}
.translation-status span {
  font-size: var(--sp-font-xs);
  font-weight: 500;
}
select,
input,
textarea {
  min-height: 40px;
  padding: var(--sp-space-2) var(--sp-space-3);
  color: var(--sp-color-text);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.table-scroll {
  max-height: 650px;
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
}
td:first-child {
  display: grid;
  gap: 3px;
}
tbody tr {
  cursor: pointer;
}
tbody tr:hover,
.selected {
  background: var(--sp-color-surface-hover);
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-space-3);
  margin-bottom: var(--sp-space-4);
}
label {
  display: grid;
  gap: var(--sp-space-2);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}
.wide {
  grid-column: 1/-1;
}
textarea {
  min-height: 90px;
  resize: vertical;
}
.detail h3 {
  margin: var(--sp-space-6) 0 var(--sp-space-3);
  font-size: var(--sp-font-md);
}
dl {
  display: grid;
  grid-template-columns: 140px 1fr;
  margin: 0;
}
dt,
dd {
  padding: var(--sp-space-2);
  margin: 0;
  border-bottom: 1px solid var(--sp-border-soft);
}
dt {
  color: var(--sp-color-text-muted);
}
.mock-gallery {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-4);
}
.mock-image {
  display: grid;
  gap: var(--sp-space-2);
  place-items: center;
  min-height: 130px;
  padding: var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  text-align: center;
  background:
    radial-gradient(circle at top, var(--sp-color-accent-blue-soft), transparent 65%),
    var(--sp-color-surface);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.mock-image span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
ol {
  padding-left: var(--sp-space-5);
  color: var(--sp-color-text-secondary);
}
@media (max-width: 1000px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 767px) {
  .heading,
  .filters {
    align-items: stretch;
    flex-direction: column;
  }
  .actions {
    flex-wrap: wrap;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .wide {
    grid-column: auto;
  }
}
</style>
