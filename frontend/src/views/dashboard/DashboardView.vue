<script setup lang="ts">
import { ref } from "vue";

import AiCopilotCard from "@/components/ai/AiCopilotCard.vue";
import OperationsFunnelChart from "@/components/charts/OperationsFunnelChart.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import MetricStrip from "@/components/data-display/MetricStrip.vue";
import RiskOperationsTable from "@/components/data-display/RiskOperationsTable.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { dashboardMetrics, funnelStages, healthPoints, riskOperations } from "@/mocks/dashboard";

const selectedPeriod = ref("week");
const periodOptions = [
  { label: "本周", value: "week" },
  { label: "本月", value: "month" },
  { label: "本季度", value: "quarter" },
];
</script>

<template>
  <PageContainer>
    <div class="dashboard-grid">
      <SpCard class="funnel-card" padding="lg">
        <template #header>
          <div class="card-heading">
            <div>
              <p class="eyebrow">MOCK OPERATIONS</p>
              <h2>商品运营漏斗</h2>
            </div>
            <SpSelect
              v-model="selectedPeriod"
              aria-label="选择漏斗数据周期"
              class="period-select"
              :options="periodOptions"
            />
          </div>
        </template>

        <OperationsFunnelChart :stages="funnelStages" />
        <MetricStrip :metrics="dashboardMetrics" />
      </SpCard>

      <AiCopilotCard
        class="copilot-card"
        :points="healthPoints"
        :score="82"
        summary="本周整体运营状态稳定"
      />

      <SpCard class="risk-card" padding="lg">
        <template #header>
          <div class="card-heading">
            <div>
              <p class="eyebrow">ATTENTION REQUIRED</p>
              <h2>高风险运营事项</h2>
            </div>
            <SpButton size="sm" variant="ghost">查看全部</SpButton>
          </div>
        </template>

        <RiskOperationsTable :items="riskOperations" />
      </SpCard>
    </div>
  </PageContainer>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(310px, 0.9fr);
  gap: var(--sp-space-6);
}

.funnel-card,
.copilot-card {
  min-width: 0;
}

.risk-card {
  grid-column: 1 / -1;
  min-width: 0;
}

.card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-4);
}

.card-heading h2 {
  margin: 0;
  font-size: var(--sp-font-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.eyebrow {
  margin: 0 0 var(--sp-space-1);
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 700;
  letter-spacing: 0.11em;
}

.period-select {
  width: 112px;
}

@media (max-width: 1279px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .risk-card {
    grid-column: auto;
  }
}

@media (max-width: 767px) {
  .dashboard-grid {
    gap: var(--sp-space-4);
  }

  .card-heading {
    align-items: flex-start;
  }

  .period-select {
    width: 102px;
  }
}
</style>
