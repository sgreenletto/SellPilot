<script setup lang="ts">
import { ElMessage } from "element-plus";
import { ref } from "vue";

import AiOrb from "@/components/ai/AiOrb.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import MiniHealthChart from "@/components/charts/MiniHealthChart.vue";
import type { HealthPoint } from "@/types/dashboard";

interface Props {
  score: number;
  summary: string;
  points: HealthPoint[];
}

const props = defineProps<Props>();
const period = ref("month");
const periodOptions = [
  { label: "本月", value: "month" },
  { label: "本季度", value: "quarter" },
];

function showReportNotice() {
  ElMessage({
    message: "报告生成功能将在 AI 运营模块中接入",
    type: "info",
  });
}
</script>

<template>
  <SpCard class="ai-copilot-card" padding="lg">
    <template #header>
      <div class="ai-copilot-card__title">
        <span>SellPilot</span>
        <strong>AI 运营助手</strong>
      </div>
    </template>

    <AiOrb size="md" />

    <div class="ai-copilot-card__divider"></div>

    <div class="ai-copilot-card__health-head">
      <div>
        <span>运营健康度</span>
        <strong>{{ props.score }}</strong>
      </div>
      <SpSelect v-model="period" :options="periodOptions" placeholder="数据周期" />
    </div>
    <p>{{ props.summary }}</p>
    <MiniHealthChart :points="props.points" />

    <template #footer>
      <SpButton block size="lg" @click="showReportNotice">生成运营报告</SpButton>
    </template>
  </SpCard>
</template>

<style scoped>
.ai-copilot-card {
  height: 100%;
}

.ai-copilot-card__title {
  display: flex;
  gap: var(--sp-space-2);
  align-items: baseline;
  font-size: var(--sp-font-lg);
}

.ai-copilot-card__title span {
  color: var(--sp-color-accent-pink);
  font-size: var(--sp-font-xs);
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ai-copilot-card__divider {
  height: 1px;
  margin: var(--sp-space-5) 0;
  background: var(--sp-border-soft);
}

.ai-copilot-card__health-head {
  display: flex;
  gap: var(--sp-space-4);
  align-items: center;
  justify-content: space-between;
}

.ai-copilot-card__health-head > div {
  display: grid;
}

.ai-copilot-card__health-head span,
.ai-copilot-card p {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.ai-copilot-card__health-head strong {
  font-size: var(--sp-font-metric);
  font-weight: 680;
  letter-spacing: -0.04em;
}

.ai-copilot-card p {
  margin-top: var(--sp-space-1);
}
</style>
