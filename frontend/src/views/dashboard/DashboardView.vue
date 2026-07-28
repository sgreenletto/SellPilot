<script setup lang="ts">
import {
  CheckCircle2,
  ChevronRight,
  Clock,
  PackageCheck,
  TrendingUp,
} from "@lucide/vue"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import SpButton from "@/components/base/SpButton.vue"
import DashboardTrendChart from "@/components/charts/DashboardTrendChart.vue"
import StatusBadge from "@/components/data-display/StatusBadge.vue"
import PageContainer from "@/components/layout/PageContainer.vue"
import {
  fetchFunnelData,
  fetchInventory,
  fetchOrders,
  fetchProducts,
  fetchTasks,
} from "@/api/dashboard"
import type { InventoryItem, Order, Product } from "@/types/commerce"
import type { MetricCardData, TrendDataset, TrendType } from "@/types/dashboard"

const router = useRouter()

// ---- 加载状态 ----

const loading = ref(true)

// ---- 动态数据 ----

const products = ref<Product[]>([])
const orders = ref<Order[]>([])
const inventory = ref<InventoryItem[]>([])
const metricCards = ref<MetricCardData[]>([])
const taskTotal = ref(0)
const alertItems = ref<
  { id: string; type: "danger" | "warning" | "info"; title: string; description: string; linkTo: string; linkLabel: string; timestamp: string }[]
>([])

// ---- 趋势切换 ----

const trendType = ref<TrendType>("funnel")

const trendTabs: { key: TrendType; label: string }[] = [
  { key: "funnel", label: "商品运营漏斗" },
  { key: "orders", label: "订单趋势" },
  { key: "popularity", label: "商品热度" },
]

const trendDatasets = ref<Record<string, TrendDataset>>({})

const currentDataset = computed(
  () =>
    trendDatasets.value[trendType.value] ?? {
      categories: [],
      series: [],
    },
)

// ---- 加载全部数据 ----

const loadError = ref("")

async function loadAll() {
  loading.value = true
  loadError.value = ""
  try {
    const [prods, ords, inv, tasks] = await Promise.all([
      fetchProducts({ limit: 100 }),
      fetchOrders({ limit: 100 }),
      fetchInventory({ limit: 200 }),
      fetchTasks({ page_size: 1 }),
    ])
    products.value = prods
    orders.value = ords
    inventory.value = inv
    taskTotal.value = tasks.total

    // 构建指标卡
    const lowStock = inv.filter((i) => i.stock_status === "low_stock").length
    metricCards.value = [
      { id: "total-products", label: "商品总数", value: prods.length, suffix: "SKU", trend: undefined, icon: "package", tone: "navy", linkTo: "/products" },
      { id: "low-stock", label: "低库存 SKU", value: lowStock, suffix: "项", trend: undefined, icon: "alert", tone: "pink", linkTo: "/products/listing-inventory" },
      { id: "total-orders", label: "模拟订单数", value: ords.length, suffix: "单", trend: undefined, icon: "trend", tone: "blue", linkTo: "/orders" },
      { id: "active-products", label: "激活商品", value: prods.filter((p) => p.status === "active").length, suffix: "SKU", trend: undefined, icon: "check", tone: "green", linkTo: "/products" },
      { id: "pending-tasks", label: "任务总数", value: tasks.total, suffix: "项", trend: undefined, icon: "check", tone: "purple", linkTo: "/tasks" },
    ]

    // 漏斗数据
    const funnel = await fetchFunnelData()
    trendDatasets.value.funnel = {
      categories: funnel.map((f) => f.label),
      series: [{ name: "商品数量", data: funnel.map((f) => f.count), color: "blue" }],
    }

    // 订单趋势（按状态分组）
    const statusCounts: Record<string, number> = {}
    ords.forEach((o) => {
      statusCounts[o.order_status] = (statusCounts[o.order_status] ?? 0) + 1
    })
    trendDatasets.value.orders = {
      categories: Object.keys(statusCounts),
      series: [{ name: "订单数", data: Object.values(statusCounts), color: "blue" }],
    }

    // 商品热度（按销量 Top 6）
    const topProducts = [...prods].sort((a, b) => b.sales_count - a.sales_count).slice(0, 6)
    trendDatasets.value.popularity = {
      categories: topProducts.map((p) => p.title.slice(0, 8)),
      series: [
        { name: "销量", data: topProducts.map((p) => p.sales_count), color: "blue" },
        { name: "评论数", data: topProducts.map((p) => p.review_count), color: "pink" },
      ],
    }

    // 异常提醒
    const alerts: typeof alertItems.value = []
    inv.filter((i) => i.stock_status === "low_stock" || i.stock_status === "out_of_stock").slice(0, 2)
      .forEach((i) => {
        alerts.push({
          id: `alert-inv-${i.inventory_id}`,
          type: "danger",
          title: "低库存预警",
          description: `SKU ${i.sku_id} 库存状态: ${i.stock_status}，可用 ${i.available_stock}，预留 ${i.reserved_stock}`,
          linkTo: "/products/listing-inventory",
          linkLabel: "前往补货",
          timestamp: "实时",
        })
      })
    if (tasks.total > 0) {
      alerts.push({
        id: "alert-tasks",
        type: "warning",
        title: "待处理任务",
        description: `当前共有 ${tasks.total} 个任务待处理`,
        linkTo: "/tasks",
        linkLabel: "查看任务",
        timestamp: "实时",
      })
    }
    alertItems.value = alerts
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "未知错误"
    loadError.value = `数据加载失败：${msg}`
    console.error("[Dashboard] loadAll failed:", err)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

// ---- 指标卡图标 ----

const iconMap: Record<string, typeof TrendingUp> = {
  trend: TrendingUp,
  package: PackageCheck,
  alert: TrendingUp,
  check: CheckCircle2,
}

// ---- 快捷跳转 ----

function goTo(path: string) {
  void router.push(path)
}

// ---- 分区活动列表（基于 API 数据） ----

interface ActivityItem {
  id: string
  action: string
  target: string
  status: "completed" | "pending"
  timestamp: string
}

const taskActivities = computed<ActivityItem[]>(() => {
  const items: ActivityItem[] = []
  const lowStockItems = inventory.value.filter(
    (i) => i.stock_status === "low_stock",
  )
  if (lowStockItems.length > 0) {
    items.push({
      id: "task-low-stock",
      action: "库存预警",
      target: `${lowStockItems.length} 个 SKU 库存偏低`,
      status: "pending",
      timestamp: "实时",
    })
  }
  if (taskTotal.value > 0) {
    items.push({
      id: "task-pending",
      action: "待处理",
      target: `${taskTotal.value} 个任务`,
      status: "pending",
      timestamp: "实时",
    })
  }
  return items
})

const systemActivities = computed<ActivityItem[]>(() => [
  {
    id: "sys-products",
    action: "数据加载",
    target: `${products.value.length} 个商品已同步`,
    status: "completed",
    timestamp: "实时",
  },
  {
    id: "sys-orders",
    action: "数据加载",
    target: `${orders.value.length} 个订单已同步`,
    status: "completed",
    timestamp: "实时",
  },
])
</script>

<template>
  <PageContainer>
    <div class="dashboard">
      <!-- 错误提示 -->
      <div v-if="loadError" class="dash-error">
        <span>⚠️ {{ loadError }}</span>
        <SpButton size="sm" variant="secondary" @click="loadAll">重试</SpButton>
      </div>

      <!-- ==================== 1. 顶部指标卡 ==================== -->
      <section class="metrics-row" aria-label="核心指标">
        <button
          v-for="metric in metricCards"
          :key="metric.id"
          type="button"
          :class="['metric-card', `metric-card--${metric.tone}`]"
          @click="goTo(metric.linkTo ?? '/dashboard')"
        >
          <span class="metric-card__icon" aria-hidden="true">
            <component :is="iconMap[metric.icon]" :size="19" />
          </span>
          <div class="metric-card__body">
            <span class="metric-card__label">{{ metric.label }}</span>
            <div class="metric-card__value">
              <strong>{{ metric.value.toLocaleString("zh-CN") }}</strong>
              <span v-if="metric.suffix" class="metric-card__suffix">{{ metric.suffix }}</span>
            </div>
            <span v-if="metric.trend != null" :class="['metric-card__trend', { 'metric-card__trend--up': metric.trend > 0, 'metric-card__trend--down': metric.trend < 0 }]">
              <ArrowUp v-if="metric.trend > 0" :size="12" />
              <ArrowDown v-else-if="metric.trend < 0" :size="12" />
              <Minus v-else :size="12" />
              {{ formatTrend(metric.trend) || "持平" }}
            </span>
          </div>
        </button>
      </section>

      <!-- ==================== 2. 主图表 + 异常提醒 双栏 ==================== -->
      <div class="dashboard-main">
        <!-- 主图表卡片 -->
        <section class="dash-card chart-card">
          <header class="dash-card__header">
            <div class="chart-card__tabs" role="tablist" :aria-label="'趋势类型切换'">
              <button
                v-for="tab in trendTabs"
                :key="tab.key"
                type="button"
                role="tab"
                :aria-selected="trendType === tab.key"
                :class="['chart-card__tab', { 'chart-card__tab--active': trendType === tab.key }]"
                @click="trendType = tab.key"
              >
                {{ tab.label }}
              </button>
            </div>
          </header>
          <DashboardTrendChart :dataset="currentDataset" :trend-type="trendType" />

          <!-- 漏斗阶段数值（仅在漏斗视图展示） -->
          <div v-if="trendType === 'funnel'" class="funnel-stats">
            <div v-for="(val, idx) in currentDataset.categories" :key="idx" class="funnel-stat-item">
              <strong>{{ (currentDataset.series[0]?.data[idx] ?? 0).toLocaleString("zh-CN") }}</strong>
              <span>{{ val }}</span>
            </div>
          </div>
        </section>

        <!-- 异常提醒 & 今日待办 -->
        <aside class="dash-card alerts-card" aria-label="异常提醒与今日待办">
          <header class="dash-card__header">
            <h3 class="dash-card__title">异常提醒 &amp; 今日待办</h3>
          </header>
          <ul class="alerts-list">
            <li v-for="item in alertItems" :key="item.id" :class="['alert-item', `alert-item--${item.type}`]">
              <span class="alert-item__dot" aria-hidden="true"></span>
              <div class="alert-item__body">
                <p class="alert-item__title">{{ item.title }}</p>
                <p class="alert-item__desc">{{ item.description }}</p>
                <div class="alert-item__meta">
                  <Clock :size="12" />
                  <span>{{ item.timestamp }}</span>
                </div>
              </div>
              <SpButton size="sm" variant="ghost" @click="goTo(item.linkTo)">
                {{ item.linkLabel }}
                <template #icon><ChevronRight :size="15" /></template>
              </SpButton>
            </li>
          </ul>
        </aside>
      </div>

      <!-- ==================== 3. 最近动态 ==================== -->
      <section class="dash-card activity-card" aria-label="最近动态">
        <header class="dash-card__header">
          <h3 class="dash-card__title">最近动态</h3>
        </header>
        <div class="activity-grid">
          <!-- 最近任务 -->
          <div class="activity-col">
            <p class="activity-col__label">最近任务</p>
            <ul class="activity-list">
              <li v-for="act in taskActivities" :key="act.id" class="activity-item">
                <span class="activity-item__icon">
                  <Clock :size="15" />
                </span>
                <div class="activity-item__body">
                  <span class="activity-item__action">{{ act.action }}</span>
                  <span class="activity-item__target">{{ act.target }}</span>
                </div>
                <StatusBadge
                  :status="act.status === 'completed' ? 'active' : 'pending'"
                  :label="act.status === 'completed' ? '已完成' : '待处理'"
                />
                <span class="activity-item__time">{{ act.timestamp }}</span>
              </li>
            </ul>
          </div>
          <!-- 最近系统操作 -->
          <div class="activity-col">
            <p class="activity-col__label">系统操作记录</p>
            <ul class="activity-list">
              <li v-for="act in systemActivities" :key="act.id" class="activity-item">
                <span class="activity-item__icon activity-item__icon--system">
                  <CheckCircle2 :size="15" />
                </span>
                <div class="activity-item__body">
                  <span class="activity-item__action">{{ act.action }}</span>
                  <span class="activity-item__target">{{ act.target }}</span>
                </div>
                <StatusBadge status="active" label="成功" />
                <span class="activity-item__time">{{ act.timestamp }}</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  </PageContainer>
</template>

<style scoped>
/* ==================== Dashboard Layout ==================== */

.dashboard {
  display: grid;
  gap: var(--sp-space-6);
  min-width: 0;
}

.dash-error {
  display: flex;
  gap: var(--sp-space-4);
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-space-4) var(--sp-space-5);
  background: color-mix(in srgb, var(--sp-color-danger) 8%, #ffffff);
  border: 1px solid color-mix(in srgb, var(--sp-color-danger) 22%, transparent);
  border-radius: 16px;
  font-size: var(--sp-font-sm);
  color: var(--sp-color-danger);
  font-weight: 600;
}

/* ==================== Shared Card ==================== */

.dash-card {
  min-width: 0;
  background: #ffffff;
  border: 1px solid rgba(62, 79, 105, 0.06);
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(64, 82, 112, 0.06);
}

.dash-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-4);
  padding: var(--sp-space-5) var(--sp-space-6) 0;
  min-width: 0;
}

.dash-card__title {
  font-size: var(--sp-font-md);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--sp-color-text);
  margin: 0;
}

/* ==================== 1. Metrics Row ==================== */

.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--sp-space-4);
  min-width: 0;
}

.metric-card {
  display: flex;
  gap: var(--sp-space-4);
  align-items: flex-start;
  min-width: 0;
  padding: var(--sp-space-5);
  text-align: left;
  cursor: pointer;
  background: #ffffff;
  border: 1px solid rgba(62, 79, 105, 0.06);
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(64, 82, 112, 0.06);
  transition: box-shadow var(--sp-transition-fast), transform var(--sp-transition-fast);
}

.metric-card:hover {
  box-shadow: 0 8px 28px rgba(64, 82, 112, 0.12);
  transform: translateY(-2px);
}

.metric-card__icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  margin-top: 2px;
}

.metric-card--navy .metric-card__icon {
  color: var(--sp-color-primary);
  background: color-mix(in srgb, var(--sp-color-primary) 10%, #ffffff);
}

.metric-card--pink .metric-card__icon {
  color: var(--sp-color-accent-pink);
  background: var(--sp-color-accent-pink-soft);
}

.metric-card--blue .metric-card__icon {
  color: var(--sp-color-accent-blue);
  background: var(--sp-color-accent-blue-soft);
}

.metric-card--purple .metric-card__icon {
  color: var(--sp-color-accent-purple);
  background: color-mix(in srgb, var(--sp-color-accent-purple) 14%, #ffffff);
}

.metric-card--green .metric-card__icon {
  color: var(--sp-color-success);
  background: color-mix(in srgb, var(--sp-color-success) 12%, #ffffff);
}

.metric-card__body {
  display: grid;
  gap: var(--sp-space-1);
  flex: 1;
  min-width: 0;
}

.metric-card__label {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 600;
}

.metric-card__value {
  display: flex;
  gap: var(--sp-space-1);
  align-items: baseline;
}

.metric-card__value strong {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.035em;
  color: var(--sp-color-text);
  line-height: 1.1;
}

.metric-card__suffix {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 600;
}

.metric-card__trend {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  font-size: var(--sp-font-xs);
  font-weight: 650;
  color: var(--sp-color-text-muted);
}

.metric-card__trend--up {
  color: var(--sp-color-success);
}

.metric-card__trend--down {
  color: var(--sp-color-accent-pink);
}

/* ==================== 2. Main: Chart + Alerts ==================== */

.dashboard-main {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(340px, 1fr);
  gap: var(--sp-space-6);
  min-width: 0;
}

/* Chart card */

.chart-card {
  padding-bottom: var(--sp-space-5);
  min-width: 0;
}

.chart-card__tabs {
  display: flex;
  gap: var(--sp-space-1);
  flex-wrap: wrap;
  overflow-x: auto;
  padding-bottom: var(--sp-space-1);
}

.chart-card__tab {
  flex: 0 0 auto;
  padding: var(--sp-space-2) var(--sp-space-4);
  font-size: var(--sp-font-xs);
  font-weight: 600;
  color: var(--sp-color-text-muted);
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--sp-radius-pill);
  transition: color var(--sp-transition-fast), background var(--sp-transition-fast);
  white-space: nowrap;
}

.chart-card__tab:hover {
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface-muted);
}

.chart-card__tab--active {
  color: var(--sp-color-primary);
  background: color-mix(in srgb, var(--sp-color-primary) 7%, transparent);
  border-color: color-mix(in srgb, var(--sp-color-primary) 12%, transparent);
}

/* Funnel stats row */

.funnel-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  padding: 0 var(--sp-space-6);
  margin-top: var(--sp-space-4);
}

.funnel-stat-item {
  display: grid;
  gap: var(--sp-space-1);
  padding: 0 var(--sp-space-4);
  border-left: 1px solid var(--sp-border-soft);
}

.funnel-stat-item:first-child {
  border-left: 0;
}

.funnel-stat-item strong {
  font-size: var(--sp-font-xl);
  font-weight: 640;
  letter-spacing: -0.04em;
  color: var(--sp-color-text);
}

.funnel-stat-item span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

/* Alerts card */

.alerts-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.alerts-list {
  display: grid;
  gap: 0;
  flex: 1;
  padding: var(--sp-space-3) var(--sp-space-5) var(--sp-space-5);
  list-style: none;
  margin: 0;
}

.alert-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--sp-space-3);
  align-items: flex-start;
  padding: var(--sp-space-4);
  border-radius: 14px;
  transition: background var(--sp-transition-fast);
}

.alert-item:hover {
  background: var(--sp-color-surface-hover);
}

.alert-item + .alert-item {
  border-top: 1px solid var(--sp-border-soft);
}

.alert-item__dot {
  display: block;
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: var(--sp-radius-pill);
  flex: 0 0 auto;
}

.alert-item--danger .alert-item__dot {
  background: var(--sp-color-accent-pink);
}

.alert-item--warning .alert-item__dot {
  background: var(--sp-color-warning);
}

.alert-item--info .alert-item__dot {
  background: var(--sp-color-accent-blue);
}

.alert-item__body {
  display: grid;
  gap: var(--sp-space-1);
  min-width: 0;
}

.alert-item__title {
  font-size: var(--sp-font-sm);
  font-weight: 700;
  color: var(--sp-color-text);
  margin: 0;
}

.alert-item__desc {
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
  margin: 0;
  line-height: 1.5;
}

.alert-item__meta {
  display: flex;
  gap: var(--sp-space-1);
  align-items: center;
  color: var(--sp-color-text-muted);
  font-size: 11px;
  margin-top: var(--sp-space-1);
}

/* ==================== 3. Recent Activity ==================== */

.activity-card {
  padding-bottom: var(--sp-space-5);
}

.activity-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-space-6);
  padding: var(--sp-space-3) var(--sp-space-6) var(--sp-space-5);
  min-width: 0;
}

.activity-col__label {
  font-size: var(--sp-font-xs);
  font-weight: 700;
  color: var(--sp-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 var(--sp-space-3) var(--sp-space-4);
}

.activity-list {
  display: grid;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.activity-item {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  padding: var(--sp-space-3) var(--sp-space-4);
  border-radius: 14px;
  transition: background var(--sp-transition-fast);
  min-width: 0;
}

.activity-item:hover {
  background: var(--sp-color-surface-hover);
}

.activity-item__icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border-radius: 11px;
  color: var(--sp-color-primary);
  background: color-mix(in srgb, var(--sp-color-primary) 8%, #ffffff);
}

.activity-item__icon--system {
  color: var(--sp-color-success);
  background: color-mix(in srgb, var(--sp-color-success) 10%, #ffffff);
}

.activity-item__body {
  display: grid;
  gap: 1px;
  flex: 1;
  min-width: 0;
}

.activity-item__action {
  font-size: var(--sp-font-xs);
  font-weight: 650;
  color: var(--sp-color-text);
}

.activity-item__target {
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-item__time {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  flex: 0 0 auto;
  white-space: nowrap;
}

/* ==================== Responsive ==================== */

@media (max-width: 1439px) {
  .metrics-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1279px) {
  .dashboard-main {
    grid-template-columns: 1fr;
  }

  .activity-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1023px) {
  .metrics-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .funnel-stats {
    padding: 0 var(--sp-space-4);
  }

  .funnel-stat-item {
    padding-inline: var(--sp-space-2);
  }
}

@media (max-width: 767px) {
  .dashboard {
    gap: var(--sp-space-4);
  }

  .metrics-row {
    grid-template-columns: 1fr;
  }

  .metric-card__value strong {
    font-size: 24px;
  }

  .chart-card__tabs {
    gap: 0;
  }

  .chart-card__tab {
    padding: var(--sp-space-2) var(--sp-space-3);
    font-size: 11px;
  }

  .dash-card__header {
    padding: var(--sp-space-4) var(--sp-space-4) 0;
  }

  .funnel-stats {
    padding: 0 var(--sp-space-3);
  }

  .funnel-stat-item strong {
    font-size: var(--sp-font-lg);
  }

  .alerts-list {
    padding: var(--sp-space-2) var(--sp-space-3) var(--sp-space-4);
  }

  .activity-grid {
    padding: var(--sp-space-2) var(--sp-space-4) var(--sp-space-4);
  }
}
</style>
