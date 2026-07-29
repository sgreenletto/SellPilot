<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { AlertTriangle, Boxes, RefreshCw } from "@lucide/vue";
import { storeToRefs } from "pinia";

import inventoryCsv from "../../../../data/demo/shopee_mock/inventory.csv?raw";
import skusCsv from "../../../../data/demo/shopee_mock/skus.csv?raw";
import {
  cancelCommerceOperation,
  confirmCommerceOperation,
  requestInventoryUpdate,
  requestProductStatus,
} from "@/api/commerce";
import { loadCommerceDashboardSnapshot } from "@/api/dashboard";
import { createTask, runTask } from "@/api/tasks";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import CommercePagination from "@/components/commerce/CommercePagination.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { useAppStore } from "@/stores/app";
import { csvRows } from "@/utils/spreadsheet";

type Row = Record<string, string | number | boolean | null>;
const parse = (csv: string): Row[] => {
  return csvRows(csv) as Row[];
};

const appStore = useAppStore();
const { selectedShopId } = storeToRefs(appStore);
const inventoryReference = parse(inventoryCsv);
const rows = ref<Row[]>([]);
const listingDrafts = ref<Row[]>([]);
const skus = parse(skusCsv);
const dataStatus = ref<"loading" | "backend" | "error">("loading");
const dataMessage = ref("正在读取当前店铺的后端商品与库存…");
const lowOnly = ref(false);
const draftPage = ref(1);
const draftPageSize = ref(10);
const inventoryPage = ref(1);
const inventoryPageSize = ref(10);
const selected = ref(new Set<string>());
const amount = ref(10);
const notice = ref("");
const ledger = ref<string[]>([]);
const pendingStatusTasks = ref(new Map<string, { confirmationId: string; publish: boolean }>());
const statusOperationLoading = ref(new Set<string>());
const pendingInventoryTasks = ref(
  new Map<string, { confirmationId: string; skuId: string; before: number; after: number }>(),
);
const inventoryOperationLoading = ref(false);
const replenishmentLoading = ref(false);
const replenishmentError = ref("");
const replenishmentResult = ref<ReplenishmentOutput | null>(null);
const analysisDays = ref(90);
const leadTimeDays = ref(30);
const safetyFactor = ref(1.5);

interface ReplenishmentRecommendation {
  product_id: string;
  product_title: string;
  sku_id: string;
  seller_sku: string;
  available_stock: number;
  safety_stock: number;
  units_sold: number;
  average_daily_sales: string | number;
  days_of_supply: string | number | null;
  target_stock: number;
  recommended_quantity: number;
  risk_level: "critical" | "warning" | "healthy";
  reason: string;
  is_mock_data: boolean;
}

interface ReplenishmentOutput {
  shop_external_id: string;
  analysis_days: number;
  lead_time_days: number;
  safety_factor: string | number;
  formula_version: string;
  summary: {
    analyzed_skus: number;
    replenishment_skus: number;
    critical_skus: number;
    recommended_units: number;
  };
  recommendations: ReplenishmentRecommendation[];
  is_mock_data: boolean;
}

function applyReplenishmentPreset(days: number, leadTime: number, factor: number): void {
  analysisDays.value = days;
  leadTimeDays.value = leadTime;
  safetyFactor.value = factor;
  replenishmentResult.value = null;
}

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
const healthyProductIds = computed(
  () =>
    new Set(
      rows.value
        .filter(
          (row) =>
            row.stock_status !== "low_stock" &&
            Number(row.available_stock) > Number(row.safety_stock),
        )
        .map((row) => String(row.product_id)),
    ),
);
const listedCount = computed(
  () => listingDrafts.value.filter((product) => product.status === "active").length,
);
const healthyListedCount = computed(
  () =>
    listingDrafts.value.filter(
      (product) =>
        product.status === "active" && healthyProductIds.value.has(String(product.product_id)),
    ).length,
);

function skuOf(row: Row): Row | undefined {
  return skus.find((sku) => sku.sku_id === row.sku_id);
}
function backendStatusLabel(status: unknown): string {
  const labels: Record<string, string> = {
    active: "Mock 已上架",
    draft: "草稿",
    inactive: "Mock 已下架",
    archived: "已归档",
  };
  return labels[String(status)] ?? `未知状态（${String(status)}）`;
}
function backendStatusTone(status: unknown): "active" | "pending" | "failed" {
  if (status === "active") return "active";
  if (status === "draft") return "pending";
  return "failed";
}
async function loadCurrentShop(): Promise<void> {
  dataStatus.value = "loading";
  dataMessage.value = "正在读取当前店铺的后端商品与库存…";
  try {
    const snapshot = await loadCommerceDashboardSnapshot(selectedShopId.value);
    rows.value = snapshot.inventory.map((item) => {
      const reference = inventoryReference.find(
        (candidate) => candidate.inventory_id === item.inventory_id,
      );
      return {
        ...item,
        warehouse_name: reference?.warehouse_name ?? item.warehouse_id,
      };
    });
    listingDrafts.value = snapshot.products.map((product) => ({ ...product }));
    selected.value = new Set();
    draftPage.value = 1;
    inventoryPage.value = 1;
    const scope =
      selectedShopId.value === "all" ? "全部模拟店铺" : `来源店铺 ${selectedShopId.value}`;
    dataStatus.value = "backend";
    dataMessage.value = `已连接后端：当前展示${scope}的 ${listingDrafts.value.length} 个商品和 ${rows.value.length} 条库存记录。`;
  } catch {
    rows.value = [];
    listingDrafts.value = [];
    dataStatus.value = "error";
    dataMessage.value = "后端数据读取失败，未使用本地全量 CSV 冒充当前店铺数据。";
  }
}
async function analyzeReplenishment(): Promise<void> {
  if (selectedShopId.value === "all") {
    replenishmentError.value = "请先选择一个具体店铺，再生成补货建议。";
    return;
  }
  replenishmentLoading.value = true;
  replenishmentError.value = "";
  try {
    const task = await createTask("inventory_replenishment", {
      shop_external_id: selectedShopId.value,
      analysis_days: analysisDays.value,
      lead_time_days: leadTimeDays.value,
      safety_factor: String(safetyFactor.value),
      only_replenishment: true,
    });
    const execution = await runTask(task.id);
    if (execution.status !== "succeeded" || !execution.result) {
      throw new Error(execution.error_message || "补货分析任务未成功完成");
    }
    replenishmentResult.value = execution.result as unknown as ReplenishmentOutput;
  } catch (caught) {
    replenishmentResult.value = null;
    replenishmentError.value = caught instanceof Error ? caught.message : "补货分析失败";
  } finally {
    replenishmentLoading.value = false;
  }
}
function toggle(id: string): void {
  const next = new Set(selected.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  selected.value = next;
}
async function requestAdjust(targets: Row[]): Promise<void> {
  if (targets.length === 0) return;
  inventoryOperationLoading.value = true;
  try {
    const next = new Map(pendingInventoryTasks.value);
    for (const row of targets) {
      const inventoryId = String(row.inventory_id);
      if (next.has(inventoryId)) continue;
      const before = Number(row.available_stock);
      const after = Math.max(0, before + Number(amount.value));
      const confirmation = await requestInventoryUpdate(
        String(row.product_id),
        String(row.sku_id),
        after,
      );
      next.set(inventoryId, {
        confirmationId: confirmation.id,
        skuId: String(row.sku_id),
        before,
        after,
      });
      pendingInventoryTasks.value = new Map(next);
    }
    notice.value = `已创建 ${next.size} 个库存待确认任务；确认执行后才会修改 Mock 平台库存。`;
  } catch (caught) {
    notice.value = caught instanceof Error ? caught.message : "创建库存待确认任务失败";
  } finally {
    inventoryOperationLoading.value = false;
  }
}
async function confirmInventoryAdjustments(): Promise<void> {
  if (pendingInventoryTasks.value.size === 0) return;
  inventoryOperationLoading.value = true;
  const remaining = new Map(pendingInventoryTasks.value);
  let succeeded = 0;
  try {
    for (const [inventoryId, task] of pendingInventoryTasks.value) {
      await confirmCommerceOperation(task.confirmationId);
      ledger.value.unshift(
        `${new Date().toLocaleTimeString()} · ${task.skuId} · ${task.before} → ${task.after}`,
      );
      remaining.delete(inventoryId);
      succeeded += 1;
    }
    pendingInventoryTasks.value = remaining;
    notice.value = `已确认并执行 ${succeeded} 项库存调整，Mock 平台库存已更新。`;
    await loadCurrentShop();
  } catch (caught) {
    pendingInventoryTasks.value = remaining;
    notice.value =
      caught instanceof Error
        ? `已执行 ${succeeded} 项，其余任务失败：${caught.message}`
        : "库存确认执行失败";
  } finally {
    inventoryOperationLoading.value = false;
  }
}
async function cancelInventoryAdjustments(): Promise<void> {
  if (pendingInventoryTasks.value.size === 0) return;
  inventoryOperationLoading.value = true;
  try {
    for (const task of pendingInventoryTasks.value.values()) {
      await cancelCommerceOperation(task.confirmationId);
    }
    pendingInventoryTasks.value = new Map();
    notice.value = "已取消库存待确认任务，未修改 Mock 平台库存。";
  } catch (caught) {
    notice.value = caught instanceof Error ? caught.message : "取消库存任务失败";
  } finally {
    inventoryOperationLoading.value = false;
  }
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
function setStatusOperationLoading(productId: string, loading: boolean): void {
  const next = new Set(statusOperationLoading.value);
  if (loading) next.add(productId);
  else next.delete(productId);
  statusOperationLoading.value = next;
}
async function requestListing(row: Row, publish: boolean): Promise<void> {
  const complete = completeness(row) === 100;
  if (publish && !complete) {
    row.listing_result = "申请失败：商品字段不完整";
    notice.value = `${row.product_id}：字段完整度不足，未创建上架确认任务。`;
    return;
  }
  const productId = String(row.product_id);
  setStatusOperationLoading(productId, true);
  try {
    const confirmation = await requestProductStatus(productId, publish);
    const next = new Map(pendingStatusTasks.value);
    next.set(productId, { confirmationId: confirmation.id, publish });
    pendingStatusTasks.value = next;
    row.listing_result = publish ? "等待确认上架" : "等待确认下架";
    notice.value = `${productId}：已创建待确认任务 ${confirmation.id.slice(0, 8)}。再次确认后才会修改 Mock 平台数据。`;
  } catch (caught) {
    notice.value = caught instanceof Error ? caught.message : "创建待确认任务失败";
  } finally {
    setStatusOperationLoading(productId, false);
  }
}
async function confirmListing(row: Row): Promise<void> {
  const productId = String(row.product_id);
  const pending = pendingStatusTasks.value.get(productId);
  if (!pending) return;
  setStatusOperationLoading(productId, true);
  try {
    await confirmCommerceOperation(pending.confirmationId);
    const next = new Map(pendingStatusTasks.value);
    next.delete(productId);
    pendingStatusTasks.value = next;
    notice.value = `${productId}：已确认执行，Mock 平台商品状态已修改。`;
    await loadCurrentShop();
  } catch (caught) {
    notice.value = caught instanceof Error ? caught.message : "确认执行失败";
  } finally {
    setStatusOperationLoading(productId, false);
  }
}
async function cancelListing(row: Row): Promise<void> {
  const productId = String(row.product_id);
  const pending = pendingStatusTasks.value.get(productId);
  if (!pending) return;
  setStatusOperationLoading(productId, true);
  try {
    await cancelCommerceOperation(pending.confirmationId);
    const next = new Map(pendingStatusTasks.value);
    next.delete(productId);
    pendingStatusTasks.value = next;
    row.listing_result = "已取消";
    notice.value = `${productId}：已取消待确认任务，未修改 Mock 平台数据。`;
  } catch (caught) {
    notice.value = caught instanceof Error ? caught.message : "取消任务失败";
  } finally {
    setStatusOperationLoading(productId, false);
  }
}

watch([lowOnly, inventoryPageSize], () => (inventoryPage.value = 1));
watch(draftPageSize, () => (draftPage.value = 1));
watch(selectedShopId, () => {
  replenishmentResult.value = null;
  replenishmentError.value = "";
  void loadCurrentShop();
});
onMounted(() => void loadCurrentShop());
</script>

<template>
  <PageContainer>
    <header class="heading heading--actions">
      <SpButton variant="secondary" @click="loadCurrentShop"
        ><template #icon><RefreshCw :size="16" /></template>重新加载当前店铺</SpButton
      >
    </header>
    <p :class="['data-status', `data-status--${dataStatus}`]" role="status">
      {{ dataMessage }}
    </p>
    <section class="metrics">
      <SpCard padding="md"
        ><strong>{{ rows.length }}</strong
        ><span>库存记录</span></SpCard
      ><SpCard padding="md"
        ><strong>{{ lowCount }}</strong
        ><span>低库存预警</span></SpCard
      ><SpCard padding="md"
        ><strong>{{ listedCount }}</strong
        ><span>Mock 已上架</span></SpCard
      ><SpCard padding="md"
        ><strong>{{ healthyListedCount }}</strong
        ><span>健康且已上架</span></SpCard
      ><SpCard padding="md"
        ><strong>{{ selected.size }}</strong
        ><span>已选择 SKU</span></SpCard
      >
    </section>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <SpCard class="replenishment-agent" padding="lg">
      <template #header>
        <div class="toolbar">
          <div>
            <strong>库存健康与补货决策</strong>
            <p>根据当前店铺近期订单销量、可用库存和安全库存生成可解释建议。</p>
          </div>
          <SpButton
            :loading="replenishmentLoading"
            :disabled="dataStatus !== 'backend' || selectedShopId === 'all'"
            @click="analyzeReplenishment"
            >生成补货建议</SpButton
          >
        </div>
      </template>
      <div class="agent-controls">
        <label>
          分析周期（天）
          <input v-model.number="analysisDays" type="number" min="1" max="365" />
        </label>
        <label>
          采购提前期（天）
          <input v-model.number="leadTimeDays" type="number" min="1" max="180" />
        </label>
        <label>
          安全系数
          <input v-model.number="safetyFactor" type="number" min="1" max="3" step="0.1" />
        </label>
      </div>
      <div class="agent-presets" aria-label="补货分析演示参数">
        <span>演示预设：</span>
        <SpButton size="sm" variant="ghost" @click="applyReplenishmentPreset(90, 14, 1.2)"
          >日常需求</SpButton
        >
        <SpButton size="sm" variant="ghost" @click="applyReplenishmentPreset(90, 30, 1.5)"
          >活动备货</SpButton
        >
        <SpButton size="sm" variant="ghost" @click="applyReplenishmentPreset(90, 60, 2)"
          >旺季压力测试</SpButton
        >
      </div>
      <p v-if="replenishmentError" class="agent-error" role="alert">
        {{ replenishmentError }}
      </p>
      <template v-if="replenishmentResult">
        <div class="agent-summary">
          <span>已分析 {{ replenishmentResult.summary.analyzed_skus }} 个 SKU</span>
          <span>建议补货 {{ replenishmentResult.summary.replenishment_skus }} 个</span>
          <span>严重风险 {{ replenishmentResult.summary.critical_skus }} 个</span>
          <span>建议合计 {{ replenishmentResult.summary.recommended_units }} 件</span>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>商品 / SKU</th>
                <th>当前库存</th>
                <th>近 {{ replenishmentResult.analysis_days }} 天销量</th>
                <th>日均销量</th>
                <th>可售天数</th>
                <th>目标库存</th>
                <th>建议补货</th>
                <th>风险</th>
                <th>依据</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in replenishmentResult.recommendations" :key="item.sku_id">
                <td>
                  <strong>{{ item.product_title }}</strong>
                  <small>{{ item.seller_sku }}</small>
                </td>
                <td>{{ item.available_stock }}</td>
                <td>{{ item.units_sold }}</td>
                <td>{{ item.average_daily_sales }}</td>
                <td>{{ item.days_of_supply ?? "无近期销量" }}</td>
                <td>{{ item.target_stock }}</td>
                <td>
                  <strong>{{ item.recommended_quantity }}</strong>
                </td>
                <td>
                  <StatusBadge
                    :status="item.risk_level === 'critical' ? 'failed' : 'pending'"
                    :label="item.risk_level === 'critical' ? '严重' : '预警'"
                  />
                </td>
                <td class="reason">{{ item.reason }}</td>
              </tr>
              <tr v-if="replenishmentResult.recommendations.length === 0">
                <td colspan="9">当前店铺暂无需要补货的 SKU。</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="agent-footnote">
          {{ replenishmentResult.formula_version }} ·
          {{ replenishmentResult.is_mock_data ? "Mock 数据分析" : "混合来源数据" }} ·
          本结果只提供决策建议，不会直接修改库存。
        </p>
      </template>
      <p v-else-if="!replenishmentLoading" class="agent-empty">
        选择参数并生成建议后，可在这里查看逐 SKU 的销量证据和补货数量。
      </p>
    </SpCard>
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
              <th>后端 Mock 状态</th>
              <th>本次预演</th>
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
              <td>
                <StatusBadge
                  :status="backendStatusTone(draft.status)"
                  :label="backendStatusLabel(draft.status)"
                />
              </td>
              <td>{{ draft.listing_result || "尚未预演" }}</td>
              <td>
                <div v-if="pendingStatusTasks.has(String(draft.product_id))" class="batch">
                  <SpButton
                    size="sm"
                    :loading="statusOperationLoading.has(String(draft.product_id))"
                    @click="confirmListing(draft)"
                    >确认执行</SpButton
                  >
                  <SpButton
                    size="sm"
                    variant="ghost"
                    :disabled="statusOperationLoading.has(String(draft.product_id))"
                    @click="cancelListing(draft)"
                    >取消</SpButton
                  >
                </div>
                <div v-else class="batch">
                  <SpButton
                    v-if="draft.status !== 'active'"
                    size="sm"
                    variant="secondary"
                    :loading="statusOperationLoading.has(String(draft.product_id))"
                    @click="requestListing(draft, true)"
                    >申请 Mock 上架</SpButton
                  >
                  <SpButton
                    v-else
                    size="sm"
                    variant="ghost"
                    :loading="statusOperationLoading.has(String(draft.product_id))"
                    @click="requestListing(draft, false)"
                    >申请 Mock 下架</SpButton
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
              :loading="inventoryOperationLoading"
              @click="requestAdjust(rows.filter((row) => selected.has(String(row.inventory_id))))"
              >申请批量调整</SpButton
            >
            <SpButton
              v-if="pendingInventoryTasks.size"
              size="sm"
              :loading="inventoryOperationLoading"
              @click="confirmInventoryAdjustments"
              >确认 {{ pendingInventoryTasks.size }} 项调整</SpButton
            >
            <SpButton
              v-if="pendingInventoryTasks.size"
              size="sm"
              variant="ghost"
              :disabled="inventoryOperationLoading"
              @click="cancelInventoryAdjustments"
              >取消调整</SpButton
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
                <SpButton
                  size="sm"
                  variant="ghost"
                  :disabled="pendingInventoryTasks.has(String(row.inventory_id))"
                  :loading="inventoryOperationLoading"
                  @click="requestAdjust([row])"
                  >申请调整 {{ amount }}</SpButton
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
        ><div class="toolbar"><strong>库存变更流水（已确认执行）</strong><Boxes :size="18" /></div
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
.heading--actions {
  justify-content: flex-end;
  margin-bottom: var(--sp-space-4);
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
  grid-template-columns: repeat(5, minmax(0, 1fr));
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
.drafts {
  margin-bottom: var(--sp-space-5);
}
.replenishment-agent {
  margin-bottom: var(--sp-space-5);
}
.replenishment-agent p {
  margin: var(--sp-space-1) 0 0;
  color: var(--sp-color-text-secondary);
}
.agent-controls,
.agent-summary,
.agent-presets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-3);
  margin-bottom: var(--sp-space-4);
}
.agent-presets {
  align-items: center;
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-sm);
}
.agent-controls label {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-sm);
}
.agent-summary span {
  padding: var(--sp-space-2) var(--sp-space-3);
  color: var(--sp-color-primary);
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-control);
}
.agent-error {
  padding: var(--sp-space-3);
  color: var(--sp-color-danger) !important;
  background: var(--sp-color-danger-soft);
  border-radius: var(--sp-radius-control);
}
.agent-empty,
.agent-footnote {
  color: var(--sp-color-text-muted) !important;
}
.reason {
  min-width: 360px;
  white-space: normal;
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
@media (min-width: 768px) and (max-width: 1279px) {
  .metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
