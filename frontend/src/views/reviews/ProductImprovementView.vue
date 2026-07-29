<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
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
const action = ref("");
const error = ref("");
const notice = ref("");
const linkedAnalysis = computed(() => Boolean(route.query.analysis_id));
const accepted = computed(
  () => report.value?.suggestions.filter((item) => item.status === "ACCEPTED") ?? [],
);
const confirmationStatus = computed(() => confirmation.value?.status.toUpperCase() ?? "");
const confirmationStatusLabel = computed(
  () =>
    ({
      PENDING: "等待确认",
      CONFIRMED: "已确认",
      EXECUTED: "已创建草稿",
      CANCELLED: "已取消",
      CANCELED: "已取消",
      FAILED: "执行失败",
    })[confirmationStatus.value] ?? "处理中",
);
const canRequestDraft = computed(
  () =>
    !action.value &&
    selected.value.some((id) => accepted.value.some((suggestion) => suggestion.id === id)),
);
const categoryLabels: Record<string, string> = {
  product_quality: "产品质量",
  packaging: "包装",
  description_mismatch: "描述不符",
  logistics: "物流履约",
  service: "服务与说明",
  material: "材料",
  size_specification: "尺寸规格",
  wrong_or_missing_item: "错发漏发",
};
const statusLabels = { PROPOSED: "待审查", ACCEPTED: "已采纳", IGNORED: "已忽略" };
const percent = (value: string): string => `${Math.round(Number(value) * 100)}%`;

function handleError(reason: unknown, fallback: string): void {
  if (reason instanceof FrontendApiError) {
    error.value =
      reason.message === "请求超时" ? "AI 生成等待时间过长，请稍后重试。" : reason.message;
    return;
  }
  error.value = fallback;
}

async function generate(): Promise<void> {
  if (!analysisId.value.trim()) {
    error.value = "请从评论分析结果进入，或填写分析 ID。";
    return;
  }
  loading.value = true;
  error.value = "";
  notice.value = "";
  confirmation.value = null;
  try {
    report.value = await generateImprovementReport(analysisId.value.trim());
    selected.value = report.value.suggestions
      .filter((item) => item.status === "ACCEPTED")
      .map((item) => item.id);
  } catch (reason) {
    handleError(reason, "产品改良报告生成失败");
  } finally {
    loading.value = false;
  }
}

async function setStatus(
  suggestion: ImprovementSuggestion,
  status: ImprovementSuggestion["status"],
): Promise<void> {
  action.value = `status:${suggestion.id}`;
  error.value = "";
  notice.value = "";
  try {
    const updated = await updateImprovementSuggestion(suggestion.id, { status });
    Object.assign(suggestion, updated);
    if (status === "ACCEPTED" && !selected.value.includes(suggestion.id)) {
      selected.value.push(suggestion.id);
    }
    if (status === "IGNORED") {
      selected.value = selected.value.filter((id) => id !== suggestion.id);
    }
    notice.value = status === "ACCEPTED" ? "建议已采纳并加入草稿范围。" : "建议已忽略。";
  } catch (reason) {
    handleError(reason, "建议状态更新失败");
  } finally {
    action.value = "";
  }
}

async function saveEdit(suggestion: ImprovementSuggestion): Promise<void> {
  action.value = `edit:${suggestion.id}`;
  error.value = "";
  notice.value = "";
  try {
    const updated = await updateImprovementSuggestion(suggestion.id, {
      title: suggestion.title,
      description: suggestion.description,
    });
    Object.assign(suggestion, updated);
    notice.value = "建议编辑已保存。";
  } catch (reason) {
    handleError(reason, "建议保存失败");
  } finally {
    action.value = "";
  }
}

async function exportReport(): Promise<void> {
  if (!report.value) return;
  action.value = "export";
  error.value = "";
  try {
    const payload = await exportImprovementReport(report.value.id);
    const blob = new Blob([payload.content], {
      type: "text/markdown;charset=utf-8",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = payload.filename;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (reason) {
    handleError(reason, "报告导出失败");
  } finally {
    action.value = "";
  }
}

async function requestDraft(): Promise<void> {
  if (!report.value) return;
  const ids = selected.value.filter((id) =>
    report.value?.suggestions.some((item) => item.id === id && item.status === "ACCEPTED"),
  );
  if (!ids.length) {
    error.value = "请先采纳并选择至少一条建议。";
    return;
  }
  action.value = "request";
  error.value = "";
  notice.value = "";
  try {
    confirmation.value = await requestImprovementDraft(
      report.value.id,
      ids,
      `improvement-${report.value.id}-${Date.now()}`,
    );
    notice.value = "已创建待确认任务，尚未生成任何商品内容草稿。";
  } catch (reason) {
    handleError(reason, "待确认任务创建失败");
  } finally {
    action.value = "";
  }
}

async function confirmDraft(): Promise<void> {
  if (!confirmation.value) return;
  action.value = "confirm";
  error.value = "";
  try {
    confirmation.value = await confirmImprovementDraft(confirmation.value.id);
    notice.value = "确认已执行；仅创建 Mock 商品内容草稿，未发布商品。";
  } catch (reason) {
    handleError(reason, "确认执行失败");
  } finally {
    action.value = "";
  }
}

async function cancelDraft(): Promise<void> {
  if (!confirmation.value) return;
  action.value = "cancel";
  error.value = "";
  try {
    confirmation.value = await cancelImprovementDraft(confirmation.value.id);
    notice.value = "待确认任务已取消，未创建草稿。";
  } catch (reason) {
    handleError(reason, "取消失败");
  } finally {
    action.value = "";
  }
}

onMounted(() => {
  if (analysisId.value) void generate();
});
</script>

<template>
  <PageContainer
    eyebrow="市场与选品 / 产品改良"
    title="产品改良报告"
    description="把评论证据转为可审查、可编辑、需确认后才能生成草稿的改良方案。"
  >
    <div v-if="error && report" class="message message--error" role="alert">{{ error }}</div>
    <div v-if="notice" class="message message--success" role="status">{{ notice }}</div>
    <SpCard v-if="!report" class="generator" variant="solid">
      <div class="generator__copy">
        <div class="generator__icon"><RefreshCw :size="22" /></div>
        <div>
          <small>{{ loading ? "正在生成" : "评论分析已就绪" }}</small>
          <h2>{{ loading ? "正在生成产品改良报告" : "生成产品改良报告" }}</h2>
          <p>仅使用含明确缺点的评论，AI 生成通常需要十几秒。</p>
          <p v-if="error" class="generator__error" role="alert">{{ error }}</p>
        </div>
      </div>
      <div class="generator__action">
        <label v-if="!linkedAnalysis">
          评论分析 ID<input v-model="analysisId" placeholder="粘贴已完成的分析 ID" />
        </label>
        <SpButton :loading="loading" @click="generate">
          {{ error ? "重新生成" : "生成报告" }}
        </SpButton>
      </div>
    </SpCard>

    <template v-if="report">
      <section class="report-heading">
        <div>
          <SpBadge variant="info">
            {{ report.algorithm_version.includes("aliyun-bailian") ? "AI 生成" : "规则生成" }}
          </SpBadge>
          <h2>{{ report.source_product_id }} 改良报告</h2>
        </div>
        <div class="toolbar">
          <SpButton variant="secondary" :loading="action === 'export'" @click="exportReport">
            <template #icon><Download :size="17" /></template>导出工厂改良报告
          </SpButton>
          <SpButton
            :loading="action === 'request'"
            :disabled="!canRequestDraft"
            @click="requestDraft"
          >
            <template #icon><FileCheck2 :size="17" /></template>提交草稿确认
          </SpButton>
        </div>
      </section>
      <section class="summary">
        <SpCard variant="solid">
          <strong>{{ report.summary.sample_size ?? 0 }}</strong>
          <span>有效评论</span>
        </SpCard>
        <SpCard variant="solid">
          <strong>{{ report.suggestions.length }}</strong>
          <span>改良建议</span>
        </SpCard>
        <SpCard variant="solid">
          <strong>{{ accepted.length }}</strong>
          <span>已采纳</span>
        </SpCard>
      </section>

      <SpCard v-if="!report.suggestions.length" class="no-suggestions" variant="solid">
        <div class="no-suggestions__mark">0</div>
        <div>
          <h3>当前分析没有可生成的改良建议</h3>
          <p>当前评论中没有识别到具体改进信号。可调整评论范围后重新分析。</p>
        </div>
        <SpButton variant="secondary" @click="router.push('/market/reviews')"
          >返回评论分析</SpButton
        >
      </SpCard>
      <section v-else class="suggestions">
        <SpCard
          v-for="suggestion in report.suggestions"
          :key="suggestion.id"
          class="suggestion"
          variant="solid"
        >
          <header>
            <SpBadge :variant="suggestion.priority <= 2 ? 'warning' : 'info'">
              优先级 P{{ suggestion.priority }}
            </SpBadge>
            <strong>{{ categoryLabels[suggestion.category] ?? suggestion.category }}</strong>
            <span class="suggestion__status">{{ statusLabels[suggestion.status] }}</span>
          </header>
          <div class="suggestion__metrics" aria-label="建议依据">
            <span
              ><small>问题频率</small
              ><strong>{{ percent(suggestion.frequency_rate) }}</strong></span
            >
            <span
              ><small>严重程度</small><strong>{{ percent(suggestion.severity) }}</strong></span
            >
            <span
              ><small>结论置信度</small><strong>{{ percent(suggestion.confidence) }}</strong></span
            >
            <span
              ><small>证据评论</small><strong>{{ suggestion.evidence_count }} 条</strong></span
            >
          </div>
          <div class="suggestion__body">
            <div class="suggestion__editor">
              <label>建议标题<input v-model="suggestion.title" class="title-input" /></label>
              <label>改良方案<textarea v-model="suggestion.description" rows="4"></textarea></label>
              <details v-if="suggestion.evidence_review_ids.items?.length" class="evidence-reviews">
                <summary>查看 {{ suggestion.evidence_count }} 条证据评论编号</summary>
                <div>
                  <span v-for="reviewId in suggestion.evidence_review_ids.items" :key="reviewId">
                    {{ reviewId }}
                  </span>
                </div>
              </details>
            </div>
          </div>
          <footer>
            <SpButton
              size="sm"
              variant="secondary"
              :loading="action === `edit:${suggestion.id}`"
              @click="saveEdit(suggestion)"
            >
              保存编辑
            </SpButton>
            <SpButton
              size="sm"
              :loading="action === `status:${suggestion.id}`"
              @click="setStatus(suggestion, 'ACCEPTED')"
            >
              采纳
            </SpButton>
            <SpButton
              size="sm"
              variant="ghost"
              :disabled="Boolean(action)"
              @click="setStatus(suggestion, 'IGNORED')"
            >
              忽略
            </SpButton>
            <label v-if="suggestion.status === 'ACCEPTED'" class="select">
              <input v-model="selected" type="checkbox" :value="suggestion.id" />
              纳入草稿范围
            </label>
          </footer>
        </SpCard>
      </section>

      <SpCard v-if="confirmation" class="confirmation">
        <div class="confirmation__main">
          <div class="confirmation__icon"><ShieldCheck :size="22" /></div>
          <div>
            <SpBadge :variant="confirmationStatus === 'PENDING' ? 'warning' : 'info'">
              {{ confirmationStatusLabel }}
            </SpBadge>
            <h3>创建商品内容草稿</h3>
            <p>{{ confirmation.risk_warning }}</p>
            <p v-if="confirmation.execution_result">草稿已创建，可前往任务中心查看。</p>
          </div>
        </div>
        <div class="confirmation__actions">
          <SpButton
            v-if="confirmationStatus === 'PENDING'"
            :loading="action === 'confirm'"
            @click="confirmDraft"
          >
            确认创建草稿
          </SpButton>
          <SpButton
            v-if="confirmationStatus === 'PENDING'"
            variant="secondary"
            :loading="action === 'cancel'"
            @click="cancelDraft"
          >
            取消
          </SpButton>
          <SpButton variant="ghost" @click="router.push('/tasks')">前往任务中心</SpButton>
        </div>
      </SpCard>
    </template>
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
  justify-content: space-between;
  margin-bottom: var(--sp-space-6);
  padding: var(--sp-space-5);
}
.generator__copy,
.generator__action {
  display: flex;
  align-items: center;
  gap: var(--sp-space-4);
}
.generator__copy {
  min-width: 0;
}
.generator__icon {
  display: grid;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  color: var(--sp-color-primary);
  background: var(--sp-color-primary-soft);
  border-radius: var(--sp-radius-control);
  place-items: center;
}
.generator__action label {
  width: min(420px, 42vw);
}
.generator h2,
.generator p {
  margin: var(--sp-space-1) 0 0;
}
.generator p,
.report-heading p {
  color: var(--sp-color-text-muted);
}
.generator .generator__error {
  color: var(--sp-color-danger);
  font-weight: 650;
}
input,
textarea {
  width: 100%;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  padding: var(--sp-space-3);
  background: var(--sp-color-surface);
  color: var(--sp-color-text);
}
.summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: var(--sp-space-5) 0;
}
.summary strong,
.summary span {
  display: block;
}
.summary strong {
  font-size: 1.7rem;
}
.report-heading {
  display: flex;
  gap: var(--sp-space-5);
  align-items: end;
  justify-content: space-between;
}
.report-heading h2 {
  margin: var(--sp-space-3) 0 0;
}
.toolbar {
  justify-content: flex-end;
}
.suggestions {
  display: grid;
  gap: var(--sp-space-4);
  margin-top: var(--sp-space-5);
}
.suggestion header,
.suggestion footer {
  flex-wrap: wrap;
}
.suggestion header {
  padding-bottom: var(--sp-space-4);
  border-bottom: 1px solid var(--sp-border-soft);
}
.suggestion__status {
  margin-left: auto;
  font-weight: 700;
}
.suggestion__body {
  margin: var(--sp-space-5) 0;
}
.suggestion__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-4);
}
.suggestion__metrics span {
  display: grid;
  gap: var(--sp-space-1);
  padding: var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.suggestion__metrics small {
  color: var(--sp-color-text-muted);
}
.evidence-reviews {
  padding: var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.evidence-reviews summary {
  color: var(--sp-color-primary);
  font-weight: 700;
  cursor: pointer;
}
.evidence-reviews div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
  margin-top: var(--sp-space-3);
}
.evidence-reviews span {
  padding: var(--sp-space-1) var(--sp-space-2);
  background: var(--sp-color-surface);
  border-radius: var(--sp-radius-pill);
}
.suggestion__editor {
  display: grid;
  gap: var(--sp-space-4);
}
.suggestion__editor label,
.generator label {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}
.suggestion p {
  color: var(--sp-color-text-secondary);
}
.title-input {
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
.no-suggestions {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--sp-space-5);
  align-items: center;
}
.no-suggestions h3 {
  margin: 0;
}
.no-suggestions p {
  max-width: 760px;
  color: var(--sp-color-text-secondary);
}
.no-suggestions__mark {
  display: grid;
  width: 64px;
  height: 64px;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-2xl);
  font-weight: 750;
  place-items: center;
  background: var(--sp-color-surface-muted);
  border-radius: 50%;
}
.confirmation {
  margin-top: var(--sp-space-5);
  justify-content: space-between;
  padding: var(--sp-space-5);
}
.confirmation__main,
.confirmation__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-space-4);
}
.confirmation__main {
  min-width: 0;
}
.confirmation__main h3 {
  margin: var(--sp-space-2) 0 var(--sp-space-1);
}
.confirmation__main p {
  margin: 0;
  color: var(--sp-color-text-secondary);
}
.confirmation__icon {
  display: grid;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-control);
  place-items: center;
}
.confirmation__actions {
  flex: 0 0 auto;
}
.message {
  padding: var(--sp-space-3) var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
  border-radius: var(--sp-radius-control);
}
.message--error {
  color: var(--sp-color-danger);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-color-danger);
}
@media (max-width: 900px) {
  .suggestion__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.message--success {
  color: var(--sp-color-success);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-color-success);
}
@media (max-width: 900px) {
  .suggestion__body {
    grid-template-columns: 1fr;
  }
  .generator {
    align-items: stretch;
    flex-direction: column;
  }
  .generator__action {
    justify-content: flex-end;
  }
  .report-heading,
  .no-suggestions {
    align-items: stretch;
    grid-template-columns: 1fr;
  }
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .summary {
    grid-template-columns: 1fr;
  }
  .toolbar,
  .report-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .toolbar :deep(.sp-button),
  .confirmation__actions :deep(.sp-button) {
    width: 100%;
  }
  .confirmation {
    align-items: stretch;
    flex-direction: column;
  }
  .confirmation__actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
