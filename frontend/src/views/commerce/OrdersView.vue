<script setup lang="ts">
import { computed, ref } from "vue";
import { FileSpreadsheet, Search, Sparkles, Truck } from "@lucide/vue";
import * as XLSX from "xlsx";

import logisticsCsv from "../../../../data/demo/shopee_mock/logistics.csv?raw";
import tracksCsv from "../../../../data/demo/shopee_mock/logistics_tracks.csv?raw";
import itemsCsv from "../../../../data/demo/shopee_mock/order_items.csv?raw";
import ordersCsv from "../../../../data/demo/shopee_mock/orders.csv?raw";
import returnsCsv from "../../../../data/demo/shopee_mock/returns_refunds.csv?raw";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpInput from "@/components/base/SpInput.vue";
import StatusBadge from "@/components/data-display/StatusBadge.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

type Row = Record<string, string | number>;
const parse = (csv: string): Row[] => {
  const book = XLSX.read(csv, { type: "string" });
  const sheet = book.Sheets[book.SheetNames[0] ?? ""];
  return sheet ? XLSX.utils.sheet_to_json<Row>(sheet, { defval: "" }) : [];
};
const orders = ref(parse(ordersCsv));
const items = parse(itemsCsv);
const logistics = parse(logisticsCsv);
const tracks = parse(tracksCsv);
const returns = parse(returnsCsv);
const query = ref("");
const status = ref("");
const selected = ref<Row | null>(orders.value[0] ?? null);
const notice = ref("");

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
const orderItems = computed(() =>
  items.filter((item) => item.order_id === selected.value?.order_id),
);
const shipment = computed(() =>
  logistics.find((item) => item.order_id === selected.value?.order_id),
);
const shipmentTracks = computed(() =>
  tracks
    .filter((track) => track.logistics_id === shipment.value?.logistics_id)
    .sort((a, b) => String(b.event_time).localeCompare(String(a.event_time))),
);
const afterSales = computed(() =>
  returns.filter((item) => item.order_id === selected.value?.order_id),
);
function mask(value: unknown): string {
  const text = String(value);
  return text.length <= 4 ? "****" : `${text.slice(0, 2)}****${text.slice(-2)}`;
}
async function importOrders(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const book = XLSX.read(await file.arrayBuffer(), { type: "array" });
  const sheet = book.Sheets[book.SheetNames[0] ?? ""];
  if (sheet) orders.value = XLSX.utils.sheet_to_json<Row>(sheet, { defval: "" });
  selected.value = orders.value[0] ?? null;
  notice.value = `已导入 ${orders.value.length} 条模拟订单；未写入后端。`;
  input.value = "";
}
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
                v-for="order in filtered"
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
            {{ item.product_title }} · {{ item.sku_name }} × {{ item.quantity }} ·
            {{ item.currency }} {{ item.subtotal }}
          </li>
        </ul>
        <h3>状态流转与变更记录</h3>
        <p>创建 → {{ selected.payment_status }} → {{ selected.order_status }}</p>
        <h3><Truck :size="17" />物流运单与轨迹</h3>
        <dl v-if="shipment">
          <dt>承运商 / 运单</dt>
          <dd>{{ shipment.carrier }} · {{ shipment.tracking_number }}</dd>
          <dt>预计送达</dt>
          <dd>{{ shipment.estimated_delivery_at || "待更新" }}</dd>
          <dt>异常标记</dt>
          <dd>
            {{ shipment.exception_type || "无异常" }} ·
            {{ shipment.exception_note || "暂无处理记录" }}
          </dd>
        </dl>
        <p v-else>暂无物流运单</p>
        <ol class="timeline">
          <li v-for="track in shipmentTracks" :key="String(track.track_id)">
            <strong>{{ track.status }}</strong> · {{ track.location
            }}<small>{{ track.event_time }} · {{ track.description }}</small>
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
        <p>
          客服会话接口尚未提供订单关联字段。建议：优先核对物流异常与售后状态，再生成脱敏回复草稿。
        </p>
        <SpButton variant="secondary" disabled>打开关联会话（待接口）</SpButton>
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
