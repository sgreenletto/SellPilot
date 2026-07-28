<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Download, FileCheck2, RefreshCw, ShieldCheck } from "@lucide/vue";
import { FrontendApiError } from "@/api/http";
import {
  cancelImprovementDraft,
  confirmImprovementDraft,
  exportImprovementReport,
  generateImprovementReport,
  requestImprovementDraft,
  updateImprovementSuggestion,
} from "@/api/product-improvement";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type {
  ConfirmationResult,
  ImprovementReport,
  ImprovementSuggestion,
} from "@/types/product-improvement";

const route = useRoute();
const router = useRouter();
const analysisId = ref(String(route.query.analysis_id ?? ""));
const report = ref<ImprovementReport | null>(null);
const confirmation = ref<ConfirmationResult | null>(null);
const selected = ref<string[]>([]);
const loading = ref(false);
const error = ref("");
const accepted = computed(
  () => report.value?.suggestions.filter((item) => item.status === "ACCEPTED") ?? [],
);

async function generate(): Promise<void> {
  if (!analysisId.value.trim()) {
    error.value = "请从评论分析结果进入，或填写分析 ID。";
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    report.value = await generateImprovementReport(analysisId.value.trim());
    selected.value = report.value.suggestions.map((item) => item.id);
  } catch (reason) {
    error.value = reason instanceof FrontendApiError ? reason.message : "产品改良报告生成失败";
  } finally {
    loading.value = false;
  }
}

async function setStatus(
  suggestion: ImprovementSuggestion,
  status: ImprovementSuggestion["status"],
): Promise<void> {
  const updated = await updateImprovementSuggestion(suggestion.id, { status });
  Object.assign(suggestion, updated);
}

async function saveEdit(suggestion: ImprovementSuggestion): Promise<void> {
  const updated = await updateImprovementSuggestion(suggestion.id, {
    title: suggestion.title,
    description: suggestion.description,
  });
  Object.assign(suggestion, updated);
}

async function exportReport(): Promise<void> {
  if (!report.value) return;
  const payload = await exportImprovementReport(report.value.id);
  const blob = new Blob([JSON.stringify(payload.content, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = payload.filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function requestDraft(): Promise<void> {
  if (!report.value) return;
  const ids = selected.value.filter((id) =>
    report.value?.suggestions.some((item) => item.id === id && item.status !== "IGNORED"),
  );
  if (!ids.length) {
    error.value = "请至少选择一条未忽略的建议。";
    return;
  }
  confirmation.value = await requestImprovementDraft(
    report.value.id,
    ids,
    `improvement-${report.value.id}-${Date.now()}`,
  );
}

async function confirmDraft(): Promise<void> {
  if (!confirmation.value) return;
  confirmation.value = await confirmImprovementDraft(confirmation.value.id);
}

async function cancelDraft(): Promise<void> {
  if (!confirmation.value) return;
  confirmation.value = await cancelImprovementDraft(confirmation.value.id);
}
</script>

<template>
  <PageContainer
    eyebrow="PRODUCT IMPROVEMENT · MOCK SHOPEE"
    title="产品改良报告"
    description="把评论证据转为可审查、可编辑、需确认后才能生成草稿的改良方案。"
  >
    <div v-if="error" class="error" role="alert">{{ error }}</div>
    <SpCard class="generator">
      <label>
        评论分析 ID
        <input v-model="analysisId" placeholder="从评论分析结果进入" />
      </label>
      <SpButton :loading="loading" @click="generate">
        <RefreshCw :size="17" />生成改良报告
      </SpButton>
      <SpBadge variant="info">规则算法 · Mock 数据</SpBadge>
    </SpCard>

    <template v-if="report">
      <section class="summary">
        <SpCard>
          <strong>{{ report.summary.sample_size ?? 0 }}</strong>
          <span>评论样本</span>
        </SpCard>
        <SpCard>
          <strong>{{ report.suggestions.length }}</strong>
          <span>改良建议</span>
        </SpCard>
        <SpCard>
          <strong>{{ accepted.length }}</strong>
          <span>已采纳</span>
        </SpCard>
        <SpCard>
          <strong>v{{ report.version }}</strong>
          <span>{{ report.algorithm_version }}</span>
        </SpCard>
      </section>

      <div class="toolbar">
        <SpButton variant="secondary" @click="exportReport">
          <Download :size="17" />导出 JSON 报告
        </SpButton>
        <SpButton @click="requestDraft"> <FileCheck2 :size="17" />创建改良内容草稿 </SpButton>
      </div>

      <section class="suggestions">
        <SpCard v-for="suggestion in report.suggestions" :key="suggestion.id" class="suggestion">
          <header>
            <label class="select">
              <input v-model="selected" type="checkbox" :value="suggestion.id" />
              选择
            </label>
            <SpBadge :variant="suggestion.priority <= 2 ? 'warning' : 'info'">
              P{{ suggestion.priority }}
            </SpBadge>
            <span>频率 {{ Number(suggestion.frequency_rate) * 100 }}%</span>
            <span>置信度 {{ Number(suggestion.confidence) * 100 }}%</span>
          </header>
          <input v-model="suggestion.title" class="title-input" />
          <textarea v-model="suggestion.description" rows="3"></textarea>
          <p>
            证据（{{ suggestion.evidence_count }}）：
            {{ suggestion.evidence_review_ids.items?.join("、") || "无" }}
          </p>
          <small>{{ suggestion.expected_impact?.limitations }}</small>
          <footer>
            <SpButton size="sm" variant="secondary" @click="saveEdit(suggestion)">
              保存编辑
            </SpButton>
            <SpButton size="sm" @click="setStatus(suggestion, 'ACCEPTED')"> 采纳 </SpButton>
            <SpButton size="sm" variant="ghost" @click="setStatus(suggestion, 'IGNORED')">
              忽略
            </SpButton>
            <strong>{{ suggestion.status }}</strong>
          </footer>
        </SpCard>
      </section>

      <SpCard v-if="confirmation" class="confirmation">
        <ShieldCheck :size="28" />
        <div>
          <h3>草稿确认任务：{{ confirmation.status }}</h3>
          <p>{{ confirmation.risk_warning }}</p>
          <p v-if="confirmation.execution_result">执行结果：{{ confirmation.execution_result }}</p>
        </div>
        <SpButton v-if="confirmation.status === 'pending'" @click="confirmDraft">
          明确确认并创建草稿
        </SpButton>
        <SpButton v-if="confirmation.status === 'pending'" variant="secondary" @click="cancelDraft">
          取消
        </SpButton>
        <SpButton variant="ghost" @click="router.push('/tasks')"> 前往任务中心 </SpButton>
      </SpCard>
    </template>
    <SpEmptyState
      v-else
      title="尚未生成改良报告"
      description="请先完成评论分析，再使用分析 ID 生成基于证据的规则报告。"
    />
  </PageContainer>
</template>

<style scoped>
.generator,
.toolbar,
.summary,
.suggestion header,
.suggestion footer,
.confirmation {
  display: flex;
  align-items: center;
  gap: var(--sp-space-4);
}
.generator {
  flex-wrap: wrap;
}
.generator label {
  flex: 1;
  min-width: 240px;
}
input,
textarea {
  width: 100%;
  border: 1px solid var(--sp-color-border);
  border-radius: var(--sp-radius-control);
  padding: var(--sp-space-3);
  background: var(--sp-color-surface);
  color: var(--sp-color-text);
}
.summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: var(--sp-space-5) 0;
}
.summary strong,
.summary span {
  display: block;
}
.summary strong {
  font-size: 1.7rem;
}
.toolbar {
  justify-content: flex-end;
  margin-bottom: var(--sp-space-4);
}
.suggestions {
  display: grid;
  gap: var(--sp-space-4);
}
.suggestion header,
.suggestion footer {
  flex-wrap: wrap;
}
.suggestion p {
  color: var(--sp-color-text-secondary);
}
.title-input {
  margin: var(--sp-space-3) 0;
  font-size: 1.05rem;
  font-weight: 700;
}
.select {
  display: flex;
  align-items: center;
  gap: var(--sp-space-2);
}
.select input {
  width: auto;
}
.confirmation {
  margin-top: var(--sp-space-5);
  flex-wrap: wrap;
}
.confirmation div {
  flex: 1;
}
.error {
  color: var(--sp-color-danger);
  margin-bottom: var(--sp-space-4);
}
@media (max-width: 900px) {
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
