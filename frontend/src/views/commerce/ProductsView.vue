<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Copy, FileSpreadsheet, Image as ImageIcon, Plus, Search } from "@lucide/vue";
import { storeToRefs } from "pinia";
import * as XLSX from "xlsx";

import productsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import skusCsv from "../../../../data/demo/shopee_mock/skus.csv?raw";
import {
  confirmCommerceOperation,
  requestProductDraft,
  requestProductImport,
} from "@/api/commerce";
import { loadCommerceDashboardSnapshot } from "@/api/dashboard";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import CommercePagination from "@/components/commerce/CommercePagination.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { useAppStore } from "@/stores/app";
import { csvRows, sheetRows } from "@/utils/spreadsheet";
import type { ProductDraftPayload } from "@/types/commerce";

type Row = Record<string, string | number | boolean | null>;

function readCsv(csv: string): Row[] {
  return csvRows(csv) as Row[];
}

const appStore = useAppStore();
const { selectedShopId } = storeToRefs(appStore);
const productReference = readCsv(productsCsv);
const products = ref<Row[]>([]);
const skus = readCsv(skusCsv);
const inventory = ref<Row[]>([]);
const query = ref("");
const status = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const selected = ref<Row | null>(null);
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
  category_name?: string;
}
const localizedByProduct = ref<Record<string, Record<string, LocalizedVersion>>>({});
const notice = ref("");
const history = ref<string[]>([]);
const dataStatus = ref<"loading" | "backend" | "error">("loading");
const dataMessage = ref("正在读取当前店铺后端商品…");

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
  inventory.value.find((item) => item.sku_id === selectedSku.value?.sku_id),
);

async function loadCurrentShop(): Promise<void> {
  dataStatus.value = "loading";
  dataMessage.value = "正在读取当前店铺后端商品…";
  try {
    const snapshot = await loadCommerceDashboardSnapshot(selectedShopId.value);
    products.value = snapshot.products.map((product) => {
      const reference = productReference.find(
        (candidate) => candidate.product_id === product.product_id,
      );
      return { ...reference, ...product };
    });
    inventory.value = snapshot.inventory.map((item) => ({ ...item }));
    selected.value =
      products.value.find((product) => product.product_id === selected.value?.product_id) ??
      products.value[0] ??
      null;
    currentPage.value = 1;
    const scope =
      selectedShopId.value === "all" ? "全部模拟店铺" : `来源店铺 ${selectedShopId.value}`;
    dataStatus.value = "backend";
    dataMessage.value = `已连接后端：当前展示${scope}的 ${products.value.length} 个商品。`;
    history.value.unshift(`从后端加载${scope}商品`);
  } catch {
    products.value = [];
    inventory.value = [];
    selected.value = null;
    dataStatus.value = "error";
    dataMessage.value = "后端商品读取失败，未使用本地全量 CSV 冒充当前店铺数据。";
  }
}

function defaultLocalizedTitle(language: string): string {
  const title = String(selected.value?.title ?? "未命名商品");
  return language === "en" ? title : "";
}

function defaultLocalizedDescription(language: string): string {
  const description = String(selected.value?.description ?? "");
  return language === "en" ? description : "";
}

function defaultLocalizedCategory(language: string): string {
  const category = String(selected.value?.category_name ?? "未分类");
  return language === "en" ? category : "";
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
const localizedCategory = localizedField("category_name", () =>
  defaultLocalizedCategory(activeLanguage.value),
);
const activeLanguageLabel = computed(
  () =>
    languageOptions.find((language) => language.code === activeLanguage.value)?.label ??
    activeLanguage.value,
);
const hasLocalizedContent = computed(
  () =>
    Boolean(localizedTitle.value.trim()) &&
    Boolean(localizedDescription.value.trim()) &&
    Boolean(localizedCategory.value.trim()),
);
const statusLabels: Record<string, Record<string, string>> = {
  en: {
    active: "Active",
    draft: "Draft",
    inactive: "Inactive",
    pending: "Pending",
    failed: "Failed",
  },
  "zh-CN": {
    active: "在售",
    draft: "草稿",
    inactive: "已下架",
    pending: "待处理",
    failed: "失败",
  },
  "zh-TW": {
    active: "上架中",
    draft: "草稿",
    inactive: "已下架",
    pending: "待處理",
    failed: "失敗",
  },
  ms: {
    active: "Aktif",
    draft: "Draf",
    inactive: "Tidak aktif",
    pending: "Menunggu",
    failed: "Gagal",
  },
  id: {
    active: "Aktif",
    draft: "Draf",
    inactive: "Tidak aktif",
    pending: "Menunggu",
    failed: "Gagal",
  },
  th: {
    active: "เปิดใช้งาน",
    draft: "ฉบับร่าง",
    inactive: "ปิดใช้งาน",
    pending: "รอดำเนินการ",
    failed: "ล้มเหลว",
  },
  vi: {
    active: "Đang hoạt động",
    draft: "Bản nháp",
    inactive: "Ngừng hoạt động",
    pending: "Đang chờ",
    failed: "Thất bại",
  },
  tl: {
    active: "Aktibo",
    draft: "Draft",
    inactive: "Hindi aktibo",
    pending: "Nakabinbin",
    failed: "Nabigo",
  },
  "pt-BR": {
    active: "Ativo",
    draft: "Rascunho",
    inactive: "Inativo",
    pending: "Pendente",
    failed: "Falhou",
  },
};
const localizedStatus = computed(() => {
  const statusCode = String(selected.value?.status ?? "");
  return (statusLabels[activeLanguage.value]?.[statusCode] ?? statusCode) || "—";
});

function draftPayload(row: Row): ProductDraftPayload {
  const productId = String(row.product_id ?? "");
  return {
    product_id:
      productId && !productId.startsWith("LOCAL-") && !productId.startsWith("COPY-")
        ? productId
        : undefined,
    source_shop_id:
      selectedShopId.value === "all"
        ? String(row.source_shop_id ?? "SHOP001")
        : selectedShopId.value,
    title: String(row.title ?? "未命名商品"),
    category_id: String(row.category_id ?? row.category_external_id ?? "MANUAL"),
    category_name: String(row.category_name ?? "未分类"),
    description: String(row.description ?? ""),
    site: String(row.site ?? "Singapore"),
    currency: String(row.currency ?? "SGD"),
    price: Number(row.price ?? 0),
    cost: Number(row.cost ?? 0),
    shipping_cost: Number(row.shipping_cost ?? 0),
    source_type: String(row.source_type ?? "manual_import"),
  };
}

async function importProducts(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const workbook = XLSX.read(await file.arrayBuffer(), { type: "array" });
  const importedRows = sheetRows(workbook) as Row[];
  if (!importedRows.length) return;
  products.value = importedRows;
  selected.value = products.value[0] ?? null;
  notice.value = `已校验并预览 ${products.value.length} 条商品，确认后才会写入后端。`;
  if (window.confirm(`字段校验通过。确认将 ${products.value.length} 条商品写入数据库吗？`)) {
    try {
      const confirmation = await requestProductImport(importedRows.map(draftPayload));
      await confirmCommerceOperation(confirmation.id);
      await loadCurrentShop();
      notice.value = `已确认导入 ${importedRows.length} 条商品并重新读取后端数据。`;
      history.value.unshift(`确认导入文件 ${file.name}`);
    } catch (error) {
      notice.value = error instanceof Error ? error.message : "商品导入失败";
    }
  }
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

async function saveDraft(): Promise<void> {
  if (!selected.value || !window.confirm("确认将当前商品保存为后端草稿吗？")) return;
  try {
    const confirmation = await requestProductDraft(draftPayload(selected.value));
    await confirmCommerceOperation(confirmation.id);
    editing.value = false;
    await loadCurrentShop();
    notice.value = "商品草稿已通过确认流程持久化，刷新页面后仍会保留。";
    history.value.unshift(`保存后端草稿 ${selected.value?.product_id}`);
  } catch (error) {
    notice.value = error instanceof Error ? error.message : "保存草稿失败";
  }
}

function badge(value: unknown): "active" | "pending" | "failed" {
  const text = String(value);
  if (text.includes("fail")) return "failed";
  if (text.includes("draft") || text.includes("pending")) return "pending";
  return "active";
}

watch([query, status, pageSize], () => (currentPage.value = 1));
watch(selectedShopId, () => void loadCurrentShop());
onMounted(() => void loadCurrentShop());
</script>

<template>
  <PageContainer>
    <header class="heading">
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

    <p :class="['data-status', `data-status--${dataStatus}`]" role="status">
      {{ dataMessage }}
    </p>
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
          <label
            >类目<input
              v-model="localizedCategory"
              :disabled="!editing"
              :placeholder="
                activeLanguage === 'en' ? '商品类目' : `待补充${activeLanguageLabel}类目`
              "
          /></label>
          <label
            >价格（{{ selected.currency }}）<input
              v-model="selected.price"
              :disabled="!editing"
              type="number"
          /></label>
          <label
            >状态<input :value="localizedStatus" disabled /><small
              >系统状态代码：{{ selected.status }}</small
            ></label
          >
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
            <strong>{{ localizedCategory || "待翻译类目" }}</strong>
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
  justify-content: flex-end;
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
.data-status {
  padding: var(--sp-space-3) var(--sp-space-4);
  margin: 0 0 var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.data-status--backend {
  color: var(--sp-color-success);
  background: var(--sp-color-success-soft);
}
.data-status--error {
  color: var(--sp-color-danger);
  background: var(--sp-color-danger-soft);
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
