<script setup lang="ts">
import { Bell, Sparkles } from "@lucide/vue";
import { ref } from "vue";

import AiOrb from "@/components/ai/AiOrb.vue";
import MiniHealthChart from "@/components/charts/MiniHealthChart.vue";
import SpAvatar from "@/components/base/SpAvatar.vue";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpIconButton from "@/components/base/SpIconButton.vue";
import SpInput from "@/components/base/SpInput.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import SpSkeleton from "@/components/base/SpSkeleton.vue";
import MetricItem from "@/components/data-display/MetricItem.vue";
import PlatformModeBadge from "@/components/data-display/PlatformModeBadge.vue";
import RiskIndicator from "@/components/data-display/RiskIndicator.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { dashboardMetrics, healthPoints } from "@/mocks/dashboard";

const inputValue = ref("");
const selectedValue = ref("mock");
const selectOptions = [
  { label: "Mock Shopee", value: "mock" },
  { label: "Real Stub", value: "real" },
];

const palette = [
  { id: "bg", name: "背景", className: "swatch-bg" },
  { id: "primary", name: "主色", className: "swatch-primary" },
  { id: "pink", name: "玫红强调", className: "swatch-pink" },
  { id: "blue", name: "亮蓝强调", className: "swatch-blue" },
  { id: "success", name: "成功", className: "swatch-success" },
  { id: "warning", name: "警告", className: "swatch-warning" },
];

const mockPlatform = {
  adapter: "mock" as const,
  configured: true,
  reachable: true,
  capabilities: ["ping"],
  message: "Mock adapter ready",
};
</script>

<template>
  <PageContainer>
    <div class="design-page">
      <header class="intro">
        <SpBadge tone="info">仅开发环境</SpBadge>
        <h1>SellPilot 设计系统</h1>
        <p>公共组件、语义变量与页面开发规范的可视化参考，不代表正式业务页面。</p>
      </header>

      <SpCard padding="lg">
        <template #header><h2>颜色与字体</h2></template>
        <div class="palette">
          <div v-for="color in palette" :key="color.id" class="palette-item">
            <span class="swatch" :class="color.className" />
            <span>{{ color.name }}</span>
          </div>
        </div>
        <div class="type-scale">
          <p class="type-title">页面标题 / 34px</p>
          <p class="type-metric">关键指标 / 31px</p>
          <p class="type-body">正文使用清晰、克制的中英文系统字体栈。</p>
          <p class="type-caption">辅助信息 / 12px</p>
        </div>
      </SpCard>

      <div class="design-grid">
        <SpCard padding="lg">
          <template #header><h2>按钮与状态</h2></template>
          <div class="component-row">
            <SpButton variant="primary">Primary</SpButton>
            <SpButton variant="secondary">Secondary</SpButton>
            <SpButton variant="ghost">Ghost</SpButton>
            <SpButton variant="danger">Danger</SpButton>
            <SpButton loading>加载中</SpButton>
            <SpButton disabled>禁用</SpButton>
            <SpIconButton ariaLabel="通知示例" tooltip="通知示例">
              <Bell :size="18" />
            </SpIconButton>
          </div>
          <div class="component-row">
            <SpBadge tone="neutral">中性</SpBadge>
            <SpBadge tone="primary">主色</SpBadge>
            <SpBadge tone="success">成功</SpBadge>
            <SpBadge tone="warning">警告</SpBadge>
            <SpBadge tone="danger">危险</SpBadge>
            <SpBadge tone="info">信息</SpBadge>
          </div>
        </SpCard>

        <SpCard padding="lg">
          <template #header><h2>输入控件</h2></template>
          <div class="form-grid">
            <SpInput v-model="inputValue" label="搜索" placeholder="输入关键词">
              <template #prefix><Sparkles :size="16" /></template>
            </SpInput>
            <SpSelect
              v-model="selectedValue"
              label="平台模式"
              :options="selectOptions"
              placeholder="请选择"
            />
            <SpInput
              v-model="inputValue"
              label="错误状态"
              error="请输入有效内容"
              placeholder="错误示例"
            />
          </div>
        </SpCard>
      </div>

      <div class="design-grid design-grid-three">
        <SpCard variant="glass" hoverable><strong>Glass Card</strong></SpCard>
        <SpCard variant="solid" hoverable><strong>Solid Card</strong></SpCard>
        <SpCard variant="flat"><strong>Flat Card</strong></SpCard>
      </div>

      <div class="design-grid">
        <SpCard padding="lg">
          <template #header><h2>数据展示</h2></template>
          <div class="component-row">
            <SpAvatar initials="SP" gradient="pink" size="lg" />
            <RiskIndicator :value="4" />
            <PlatformModeBadge :status="mockPlatform" />
            <PlatformModeBadge :status="null" :error="'后端未连接'" />
          </div>
          <MetricItem :metric="dashboardMetrics[0]!" />
        </SpCard>

        <SpCard padding="lg">
          <template #header><h2>间距、圆角与阴影</h2></template>
          <div class="token-samples">
            <span class="space-sample space-small">8</span>
            <span class="space-sample space-medium">24</span>
            <span class="space-sample space-large">48</span>
            <span class="radius-sample">24px 卡片圆角</span>
            <span class="shadow-sample">柔和卡片阴影</span>
          </div>
        </SpCard>
      </div>

      <div class="design-grid">
        <SpCard padding="lg">
          <template #header><h2>空状态与骨架</h2></template>
          <SpEmptyState title="暂无数据" description="接入业务数据后在此展示。">
            <template #action><SpButton size="sm">了解更多</SpButton></template>
          </SpEmptyState>
          <div class="skeleton-row">
            <SpSkeleton variant="circle" />
            <SpSkeleton variant="line" />
            <SpSkeleton variant="card" />
          </div>
        </SpCard>

        <SpCard padding="lg">
          <template #header><h2>AI Orb 与图表容器</h2></template>
          <div class="visual-samples">
            <AiOrb />
            <div class="chart-example">
              <MiniHealthChart :points="healthPoints" />
            </div>
          </div>
        </SpCard>
      </div>
    </div>
  </PageContainer>
</template>

<style scoped>
.design-page {
  display: grid;
  gap: var(--sp-space-6);
}

.intro h1 {
  margin: var(--sp-space-3) 0 var(--sp-space-2);
  font-size: var(--sp-font-page-title);
}

.intro p {
  margin: 0;
  color: var(--sp-color-text-secondary);
}

h2 {
  margin: 0;
  font-size: var(--sp-font-lg);
}

.palette,
.component-row,
.token-samples,
.skeleton-row,
.visual-samples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-space-4);
}

.palette-item {
  display: grid;
  gap: var(--sp-space-2);
  min-width: 90px;
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-sm);
}

.swatch {
  width: 72px;
  height: 48px;
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-control);
  box-shadow: var(--sp-shadow-card);
}

.swatch-bg {
  background: var(--sp-color-bg);
}

.swatch-primary {
  background: var(--sp-color-primary);
}

.swatch-pink {
  background: var(--sp-color-accent-pink);
}

.swatch-blue {
  background: var(--sp-color-accent-blue);
}

.swatch-success {
  background: var(--sp-color-success);
}

.swatch-warning {
  background: var(--sp-color-warning);
}

.type-scale {
  margin-top: var(--sp-space-8);
}

.type-title {
  font-size: var(--sp-font-page-title);
  font-weight: 700;
}

.type-metric {
  font-size: var(--sp-font-metric);
  font-weight: 700;
}

.type-body {
  font-size: var(--sp-font-md);
}

.type-caption {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.design-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-space-6);
}

.design-grid-three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.form-grid {
  display: grid;
  gap: var(--sp-space-4);
}

.token-samples {
  align-items: flex-end;
}

.space-sample,
.radius-sample,
.shadow-sample {
  display: grid;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
  place-items: center;
}

.space-small {
  width: var(--sp-space-8);
  height: var(--sp-space-8);
}

.space-medium {
  width: var(--sp-space-12);
  height: var(--sp-space-12);
}

.space-large {
  width: 72px;
  height: 72px;
}

.radius-sample,
.shadow-sample {
  min-height: 72px;
  padding: var(--sp-space-4);
}

.radius-sample {
  border-radius: var(--sp-radius-card);
}

.shadow-sample {
  background: var(--sp-color-surface);
  box-shadow: var(--sp-shadow-card);
}

.skeleton-row {
  margin-top: var(--sp-space-5);
}

.visual-samples {
  justify-content: space-around;
}

.chart-example {
  width: min(100%, 250px);
  height: 160px;
}

@media (max-width: 900px) {
  .design-grid,
  .design-grid-three {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
