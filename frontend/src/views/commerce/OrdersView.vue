<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { FileSpreadsheet, Search, Sparkles, Truck } from "@lucide/vue";
import { storeToRefs } from "pinia";
import * as XLSX from "xlsx";

import logisticsCsv from "../../../../data/demo/shopee_mock/logistics.csv?raw";
import messagesCsv from "../../../../data/demo/shopee_mock/customer_messages.csv?raw";
import sessionsCsv from "../../../../data/demo/shopee_mock/customer_sessions.csv?raw";
import tracksCsv from "../../../../data/demo/shopee_mock/logistics_tracks.csv?raw";
import itemsCsv from "../../../../data/demo/shopee_mock/order_items.csv?raw";
import ordersCsv from "../../../../data/demo/shopee_mock/orders.csv?raw";
import productsCsv from "../../../../data/demo/shopee_mock/products.csv?raw";
import returnsCsv from "../../../../data/demo/shopee_mock/returns_refunds.csv?raw";
import skusCsv from "../../../../data/demo/shopee_mock/skus.csv?raw";
import { loadCommerceDashboardSnapshot } from "@/api/dashboard";
import SpCard from "@/components/base/SpCard.vue";
import SpInput from "@/components/base/SpInput.vue";
import CommercePagination from "@/components/commerce/CommercePagination.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { useAppStore } from "@/stores/app";
import { csvRows, sheetRows } from "@/utils/spreadsheet";

type Row = Record<string, string | number | boolean | null>;
const parse = (csv: string): Row[] => {
  return csvRows(csv) as Row[];
};
const appStore = useAppStore();
const { selectedShopId } = storeToRefs(appStore);
const orderReference = parse(ordersCsv);
const orders = ref<Row[]>([]);
const items = parse(itemsCsv);
const products = parse(productsCsv);
const skus = parse(skusCsv);
const logistics = parse(logisticsCsv);
const tracks = parse(tracksCsv);
const returns = parse(returnsCsv);
const sessions = parse(sessionsCsv);
const messages = parse(messagesCsv);
const query = ref("");
const status = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const selected = ref<Row | null>(null);
const notice = ref("");
const dataStatus = ref<"loading" | "backend" | "error">("loading");
const dataMessage = ref("正在读取当前店铺后端订单…");

async function loadCurrentShop(): Promise<void> {
  dataStatus.value = "loading";
  dataMessage.value = "正在读取当前店铺后端订单…";
  try {
    const snapshot = await loadCommerceDashboardSnapshot(selectedShopId.value);
    orders.value = snapshot.orders.map((order) => {
      const reference = orderReference.find((candidate) => candidate.order_id === order.order_id);
      return { ...reference, ...order };
    });
    selected.value =
      orders.value.find((order) => order.order_id === selected.value?.order_id) ??
      orders.value[0] ??
      null;
    currentPage.value = 1;
    const scope =
      selectedShopId.value === "all" ? "全部模拟店铺" : `来源店铺 ${selectedShopId.value}`;
    dataStatus.value = "backend";
    dataMessage.value = `已连接后端：当前展示${scope}的 ${orders.value.length} 笔订单；商品明细、物流、售后和客服关联来自同一 Mock 数据包。`;
  } catch {
    orders.value = [];
    selected.value = null;
    dataStatus.value = "error";
    dataMessage.value = "后端订单读取失败，未使用本地全量 CSV 冒充当前店铺数据。";
  }
}

const filtered = computed(() => {
  const keyword = query.value.toLowerCase();
  return orders.value.filter(
    (order) =>
      (!keyword ||
        [order.order_id, order.buyer_id].some((value) =>
          String(value).toLowerCase().includes(keyword),
        )) &&
      (!status.value || order.order_status === status.value),
  );
});
const paginated = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filtered.value.slice(start, start + pageSize.value);
});
const orderItems = computed(() =>
  items.filter((item) => item.order_id === selected.value?.order_id),
);
const shipment = computed(() =>
  logistics.find((item) => item.order_id === selected.value?.order_id),
);
const shipmentTracks = computed(() =>
  tracks
    .filter((track) => track.tracking_number === shipment.value?.tracking_number)
    .sort((a, b) => String(b.event_time).localeCompare(String(a.event_time))),
);
const afterSales = computed(() =>
  returns.filter((item) => item.order_id === selected.value?.order_id),
);
const customerSession = computed(() =>
  sessions.find((session) => session.order_id === selected.value?.order_id),
);
const conversationMessages = computed(() =>
  messages.filter((message) => message.session_id === customerSession.value?.session_id),
);
const logisticsException = computed(() => shipment.value?.logistics_status === "exception");
const orderStatusTimeline = computed(() => {
  if (!selected.value) return [];
  return [
    ["订单创建", selected.value.created_at],
    ["支付完成", selected.value.paid_at],
    ["商品发货", selected.value.shipped_at],
    ["订单完成", selected.value.completed_at],
    ["订单取消", selected.value.cancelled_at],
  ].filter((entry) => entry[1]);
});
const exceptionRecords = computed(() =>
  shipmentTracks.value.filter(
    (track) =>
      track.status === "exception" || String(track.description).toLowerCase().includes("exception"),
  ),
);

function productOf(item: Row): Row | undefined {
  return products.find((product) => product.product_id === item.product_id);
}
function skuOf(item: Row): Row | undefined {
  return skus.find((sku) => sku.sku_id === item.sku_id);
}
function aiSuggestion(): string {
  if (afterSales.value.length) return "建议先核对退款退货原因和金额，再生成售后处理回复。";
  if (logisticsException.value)
    return "建议优先核对最新物流轨迹，告知买家异常位置和下一步处理计划。";
  if (customerSession.value)
    return `已关联 ${customerSession.value.intent} 会话，建议结合买家语言生成回复草稿。`;
  return "当前没有关联客服会话，建议仅基于订单与物流事实生成脱敏回复草稿。";
}
function mask(value: unknown): string {
  const text = String(value);
  return text.length <= 4 ? "****" : `${text.slice(0, 2)}****${text.slice(-2)}`;
}
async function importOrders(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const book = XLSX.read(await file.arrayBuffer(), { type: "array" });
  const importedRows = sheetRows(book) as Row[];
  if (importedRows.length) orders.value = importedRows;
  selected.value = orders.value[0] ?? null;
  notice.value = `已导入 ${orders.value.length} 条模拟订单；未写入后端。`;
  input.value = "";
}

watch([query, status, pageSize], () => (currentPage.value = 1));
watch(selectedShopId, () => void loadCurrentShop());
onMounted(() => void loadCurrentShop());
</script>

<template>
  <PageContainer>
    <header class="heading">
      <div>
        <p class="eyebrow">MOCK SHOPEE · 订单与履约</p>
        <h1>订单与履约</h1>
        <p>查看脱敏订单、状态、物流轨迹、异常及售后记录。</p>
      </div>
      <label class="file-button"
        ><FileSpreadsheet :size="16" />导入模拟订单<input
          type="file"
          accept=".csv,.xlsx,.xls"
          @change="importOrders"
      /></label>
    </header>
    <p :class="['data-status', `data-status--${dataStatus}`]" role="status">
      {{ dataMessage }}
    </p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <div class="workspace">
      <SpCard padding="lg"
        ><template #header
          ><div class="filters">
            <SpInput v-model="query" type="search" clearable placeholder="搜索订单号或买家"
              ><template #prefix><Search :size="16" /></template></SpInput
            ><select v-model="status">
              <option value="">全部状态</option>
              <option value="pending">待处理</option>
              <option value="shipped">已发货</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
          </div></template
        >
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>订单</th>
                <th>买家</th>
                <th>金额</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="order in paginated"
                :key="String(order.order_id)"
                :class="{ selected: selected?.order_id === order.order_id }"
                @click="selected = order"
              >
                <td>
                  <strong>{{ order.order_id }}</strong
                  ><small>{{ order.created_at }}</small>
                </td>
                <td>{{ mask(order.buyer_id) }}</td>
                <td>{{ order.currency }} {{ order.total_amount }}</td>
                <td><StatusBadge status="active" :label="String(order.order_status)" /></td>
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
      <SpCard v-if="selected" padding="lg" class="detail"
        ><template #header><strong>订单详情</strong></template>
        <dl>
          <dt>订单号</dt>
          <dd>{{ selected.order_id }}</dd>
          <dt>买家信息</dt>
          <dd>{{ mask(selected.buyer_id) }}（已脱敏）</dd>
          <dt>支付状态</dt>
          <dd>{{ selected.payment_status }}</dd>
          <dt>订单状态</dt>
          <dd>{{ selected.order_status }}</dd>
        </dl>
        <h3>商品明细</h3>
        <ul>
          <li v-for="item in orderItems" :key="String(item.order_item_id)">
            {{ productOf(item)?.title || item.product_id }} ·
            {{ skuOf(item)?.seller_sku || item.sku_id }} × {{ item.quantity }} ·
            {{ selected.currency }} {{ item.subtotal }}
          </li>
        </ul>
        <h3>订单状态流转记录</h3>
        <ol class="timeline">
          <li v-for="[label, timestamp] in orderStatusTimeline" :key="String(label)">
            <strong>{{ label }}</strong
            ><small>{{ timestamp }}</small>
          </li>
          <li>
            <strong>当前状态：{{ selected.order_status }}</strong>
            <small>支付状态：{{ selected.payment_status }}</small>
          </li>
        </ol>
        <h3><Truck :size="17" />物流运单与轨迹</h3>
        <dl v-if="shipment">
          <dt>承运商 / 运单</dt>
          <dd>{{ shipment.carrier }} · {{ shipment.tracking_number }}</dd>
          <dt>预计送达</dt>
          <dd>{{ shipment.estimated_delivery_at || "待更新" }}</dd>
          <dt>物流状态</dt>
          <dd>{{ shipment.logistics_status }}</dd>
          <dt>异常标记</dt>
          <dd>
            {{
              logisticsException
                ? `异常 · ${shipmentTracks[0]?.description || "等待处理记录"}`
                : "无异常"
            }}
          </dd>
        </dl>
        <p v-else>暂无物流运单</p>
        <ol class="timeline">
          <li v-for="track in shipmentTracks" :key="String(track.track_id)">
            <strong>{{ track.status }}</strong> · {{ track.location
            }}<small>{{ track.event_time }} · {{ track.description }}</small>
          </li>
        </ol>
        <h3>物流异常处理记录</h3>
        <p v-if="exceptionRecords.length === 0">当前运单没有异常处理记录。</p>
        <ol v-else class="timeline">
          <li v-for="record in exceptionRecords" :key="String(record.track_id)">
            <strong>{{ record.status }} · {{ record.location }}</strong>
            <small>{{ record.event_time }} · {{ record.description }}</small>
          </li>
        </ol>
        <h3>取消、退款、退货和包裹异常</h3>
        <p v-if="afterSales.length === 0">当前订单暂无售后记录。</p>
        <ul v-else>
          <li v-for="item in afterSales" :key="String(item.return_id)">
            {{ item.request_type }} · {{ item.reason_type }} · {{ item.status }} · {{ item.amount }}
          </li>
        </ul>
        <h3><Sparkles :size="17" />关联客服与 AI 建议</h3>
        <dl v-if="customerSession">
          <dt>会话</dt>
          <dd>{{ customerSession.session_id }} · {{ customerSession.intent }}</dd>
          <dt>语言 / 风险</dt>
          <dd>{{ customerSession.language }} · {{ customerSession.risk_level }}</dd>
        </dl>
        <p v-else>当前订单没有关联客服会话。</p>
        <ul v-if="conversationMessages.length">
          <li v-for="message in conversationMessages.slice(-3)" :key="String(message.message_id)">
            {{ message.sender_type }}：{{ message.content }}
          </li>
        </ul>
        <p><strong>AI 处理建议：</strong>{{ aiSuggestion() }}</p>
      </SpCard>
    </div>
  </PageContainer>
</template>

<style scoped>
.heading,
.filters {
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
small,
.detail p {
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
  grid-template-columns: minmax(0, 1fr) minmax(400px, 1fr);
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
select {
  min-height: 40px;
  padding: 0 var(--sp-space-3);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.table-scroll {
  max-height: 760px;
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
.detail h3 {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  margin: var(--sp-space-6) 0 var(--sp-space-3);
  font-size: var(--sp-font-md);
}
.timeline li {
  margin-bottom: var(--sp-space-3);
}
.timeline small {
  display: block;
  margin-top: 3px;
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
}
</style>
