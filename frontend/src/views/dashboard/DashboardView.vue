<script setup lang="ts">
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Clock,
  MessageCircleMore,
  Minus,
  PackageCheck,
  TrendingUp,
} from "@lucide/vue"
import { computed, ref } from "vue"
import { useRouter } from "vue-router"

import SpButton from "@/components/base/SpButton.vue"
import DashboardTrendChart from "@/components/charts/DashboardTrendChart.vue"
import StatusBadge from "@/components/data-display/StatusBadge.vue"
import PageContainer from "@/components/layout/PageContainer.vue"
import {
  alertItems,
  recentActivities,
  topMetrics,
  trendDatasets,
} from "@/mocks/dashboard"
import type { TrendType } from "@/types/dashboard"

const router = useRouter()

// ---- 趋势切换 ----

const trendType = ref<TrendType>("funnel")

const trendTabs: { key: TrendType; label: string }[] = [
  { key: "funnel", label: "商品运营漏斗" },
  { key: "orders", label: "订单趋势" },
  { key: "popularity", label: "商品热度" },
  { key: "sentiment", label: "评论情绪分布" },
  { key: "service", label: "客服问题趋势" },
]

const currentDataset = computed(() => trendDatasets[trendType.value])

// ---- 指标卡图标 ----

const iconMap: Record<string, typeof TrendingUp> = {
  trend: TrendingUp,
  message: MessageCircleMore,
  package: PackageCheck,
  alert: AlertTriangle,
  check: CheckCircle2,
}

// ---- 快捷跳转 ----

function goTo(path: string) {
  void router.push(path)
}

// ---- 格式化趋势数字 ----

function formatTrend(v: number | undefined): string {
  if (v == null || v === 0) return ""
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`
}

// ---- 分区活动列表（避免模板中重复 filter） ----

const taskActivities = computed(() =>
  recentActivities.filter((a) => a.type === "task"),
)

const systemActivities = computed(() =>
  recentActivities.filter((a) => a.type === "system"),
)
</script>

<template>
  <PageContainer>
    <div class="dashboard">
      <!-- ==================== 1. 顶部指标卡 ==================== -->
      <section class="metrics-row" aria-label="核心指标">
        <button
          v-for="metric in topMetrics"
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
                  <BarChart3 v-if="act.status === 'completed'" :size="15" />
                  <Clock v-else :size="15" />
                </span>
                <div class="activity-item__body">
                  <span class="activity-item__action">{{ act.action }}</span>
                  <span class="activity-item__target">{{ act.target }}</span>
                </div>
                <StatusBadge
                  :status="act.status === 'completed' ? 'active' : act.status === 'pending' ? 'pending' : 'failed'"
                  :label="act.status === 'completed' ? '已完成' : act.status === 'pending' ? '待处理' : act.status === 'processing' ? '处理中' : '失败'"
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
                  <CheckCircle2 v-if="act.status === 'completed'" :size="15" />
                  <Clock v-else :size="15" />
                </span>
                <div class="activity-item__body">
                  <span class="activity-item__action">{{ act.action }}</span>
                  <span class="activity-item__target">{{ act.target }}</span>
                </div>
                <StatusBadge
                  :status="act.status === 'completed' ? 'active' : 'pending'"
                  :label="act.status === 'completed' ? '成功' : '处理中'"
                />
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
