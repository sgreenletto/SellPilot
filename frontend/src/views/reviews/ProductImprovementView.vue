<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Download, FileCheck2, RefreshCw, ShieldCheck } from "@lucide/vue";
import { FrontendApiError } from "@/api/http";
import { listReviewEvidence } from "@/api/review-analysis";
import {
  cancelImprovementDraft,
  confirmImprovementDraft,
  exportImprovementReport,
  generateImprovementReport,
  listImprovementDrafts,
  requestImprovementDraft,
  requestImprovementDraftHistoryClear,
  requestImprovementDraftRevision,
  updateImprovementSuggestion,
} from "@/api/product-improvement";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type {
  ConfirmationResult,
  ImprovementDraftItem,
  ImprovementDraftVersion,
  ImprovementReport,
  ImprovementSuggestion,
} from "@/types/product-improvement";
import type { ReviewEvidence } from "@/types/review-analysis";

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
const draftPreviewVisible = ref(false);
const lastRegenerateToken = ref("");
const evidenceByReviewId = ref<Record<string, ReviewEvidence>>({});
const drafts = ref<ImprovementDraftVersion[]>([]);
const activeDraftId = ref("");
const draftEditor = ref<ImprovementDraftItem[]>([]);
const draftEditing = ref(false);
const confirmationPurpose = ref<"create" | "revision" | "clear">("create");
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
      SUCCEEDED: "已创建草稿",
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
const savedDraftSuggestions = computed(() =>
  accepted.value.filter((suggestion) => selected.value.includes(suggestion.id)),
);
const activeDraft = computed(
  () => drafts.value.find((item) => item.id === activeDraftId.value) ?? drafts.value[0] ?? null,
);
const reportSite = computed(() => {
  const value = report.value?.input_conditions.site;
  return typeof value === "string" && ["sg", "my", "ph", "th", "vn", "id"].includes(value)
    ? value
    : "sg";
});
const categoryLabels: Record<string, string> = {
  product_quality: "产品",
  packaging: "包装",
  description_mismatch: "文案",
  logistics: "物流",
  service: "服务",
  material: "产品",
  size_specification: "产品",
  wrong_or_missing_item: "产品",
  other: "其他",
};
const statusLabels = { PROPOSED: "待审查", ACCEPTED: "已采纳", IGNORED: "已忽略" };
const percent = (value: string): string => `${Math.round(Number(value) * 100)}%`;
const cloneDraftItems = (items: ImprovementDraftItem[]): ImprovementDraftItem[] =>
  items.map((item) => ({ title: item.title, description: item.description }));
function suggestionEvidence(suggestion: ImprovementSuggestion): ReviewEvidence[] {
  return (suggestion.evidence_review_ids.items ?? [])
    .map((reviewId) => evidenceByReviewId.value[reviewId])
    .filter((item): item is ReviewEvidence => Boolean(item));
}

async function loadEvidence(analysisIdValue: string): Promise<void> {
  const byId: Record<string, ReviewEvidence> = {};
  let page = 1;
  let total = 0;
  do {
    const response = await listReviewEvidence(analysisIdValue, page, "", "", 100);
    total = response.total;
    for (const item of response.items) {
      byId[item.review_id] ??= item;
    }
    if (response.items.length === 0) break;
    page += 1;
  } while ((page - 1) * 100 < total);
  evidenceByReviewId.value = byId;
}

async function loadDraftHistory(sourceProductId: string): Promise<void> {
  const response = await listImprovementDrafts(sourceProductId);
  drafts.value = response.items;
  if (!drafts.value.some((item) => item.id === activeDraftId.value)) {
    activeDraftId.value = drafts.value[0]?.id ?? "";
  }
  if (activeDraft.value && !draftEditing.value) {
    draftEditor.value = cloneDraftItems(activeDraft.value.items);
  }
}

function handleError(reason: unknown, fallback: string): void {
  if (reason instanceof FrontendApiError) {
    error.value =
      reason.message === "请求超时" ? "AI 生成等待时间过长，请稍后重试。" : reason.message;
    return;
  }
  error.value = fallback;
}

async function generate(forceRegenerate = false): Promise<void> {
  if (!analysisId.value.trim()) {
    error.value = "请从评论分析结果进入，或填写分析 ID。";
    return;
  }
  loading.value = true;
  error.value = "";
  notice.value = "";
  confirmation.value = null;
  try {
    const currentAnalysisId = analysisId.value.trim();
    report.value = await generateImprovementReport(currentAnalysisId, forceRegenerate);
    selected.value = report.value.suggestions
      .filter((item) => item.status === "ACCEPTED")
      .map((item) => item.id);
    try {
      await loadEvidence(currentAnalysisId);
    } catch {
      error.value = "报告已生成，但证据评论暂时加载失败，请稍后重新进入报告。";
    }
    try {
      await loadDraftHistory(report.value.source_product_id);
    } catch {
      notice.value = "报告已生成，但历史改良草稿暂时无法加载。";
    }
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
    confirmationPurpose.value = "create";
    confirmation.value = await requestImprovementDraft(
      report.value.id,
      ids,
      `improvement-${report.value.id}-${Date.now()}`,
      reportSite.value,
    );
    notice.value = "请核对下方范围并确认；确认前不会创建草稿。";
  } catch (reason) {
    handleError(reason, "待确认任务创建失败");
  } finally {
    action.value = "";
  }
}

function selectDraft(draft: ImprovementDraftVersion): void {
  activeDraftId.value = draft.id;
  draftEditor.value = cloneDraftItems(draft.items);
  draftEditing.value = false;
}

function startDraftEditing(): void {
  if (!activeDraft.value) return;
  draftEditor.value = cloneDraftItems(activeDraft.value.items);
  draftEditing.value = true;
}

function cancelDraftEditing(): void {
  if (!activeDraft.value) return;
  draftEditing.value = false;
  draftEditor.value = cloneDraftItems(activeDraft.value.items);
}

async function requestDraftRevision(): Promise<void> {
  if (!activeDraft.value) return;
  if (draftEditor.value.some((item) => !item.title.trim() || !item.description.trim())) {
    error.value = "草稿标题和改良方案不能为空。";
    return;
  }
  action.value = "request-revision";
  error.value = "";
  notice.value = "";
  try {
    confirmationPurpose.value = "revision";
    confirmation.value = await requestImprovementDraftRevision(
      activeDraft.value.id,
      activeDraft.value.version,
      draftEditor.value.map((item) => ({
        title: item.title.trim(),
        description: item.description.trim(),
      })),
      `improvement-revision-${activeDraft.value.id}-${Date.now()}`,
    );
    notice.value = "请确认保存改良草稿新版本；确认前不会写入修改。";
  } catch (reason) {
    handleError(reason, "草稿版本待确认任务创建失败");
  } finally {
    action.value = "";
  }
}

async function requestDraftHistoryClear(): Promise<void> {
  if (!report.value || !drafts.value.length) return;
  action.value = "clear-history";
  error.value = "";
  notice.value = "";
  try {
    confirmationPurpose.value = "clear";
    confirmation.value = await requestImprovementDraftHistoryClear(
      report.value.source_product_id,
      `improvement-clear-${report.value.source_product_id}-${Date.now()}`,
    );
    notice.value = "请确认清空当前商品的草稿历史；确认后新草稿将从 v1 重新编号。";
  } catch (reason) {
    handleError(reason, "清空草稿历史待确认任务创建失败");
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
    draftPreviewVisible.value = true;
    draftEditing.value = false;
    if (report.value) await loadDraftHistory(report.value.source_product_id);
    notice.value =
      confirmationPurpose.value === "clear"
        ? "当前商品的改良草稿历史已清空；下一份草稿将显示为 v1。"
        : confirmationPurpose.value === "revision"
          ? "改良草稿新版本已保存；旧版本仍保留。"
          : "改良草稿已创建并保存；未发布商品，也未修改价格或库存。";
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

function restoreFromRoute(): void {
  const routeAnalysisId = String(route.query.analysis_id ?? "");
  if (routeAnalysisId) analysisId.value = routeAnalysisId;
  const regenerateToken = String(route.query.regenerate ?? "");
  if (regenerateToken && regenerateToken !== lastRegenerateToken.value) {
    lastRegenerateToken.value = regenerateToken;
    const remainingQuery = { ...route.query };
    delete remainingQuery.regenerate;
    void router.replace({ query: remainingQuery });
    void generate(true);
    return;
  }
  if (analysisId.value && !report.value && !loading.value) void generate();
}

onMounted(restoreFromRoute);
onActivated(restoreFromRoute);
</script>

<template>
  <PageContainer
    eyebrow="市场与选品 / 产品改良"
    title="产品改良报告"
    description="把评论证据转为可审查、可编辑、需确认后才能生成草稿的改良方案。"
  >
    <div class="page-actions">
      <SpButton variant="secondary" @click="router.push('/market/reviews')">
        返回评论分析
      </SpButton>
    </div>
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
        <SpButton :loading="loading" @click="generate(true)">
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
            <template #icon><FileCheck2 :size="17" /></template>创建改良商品草稿
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
            <span title="综合评论分类可靠度（60%）、证据数量（25%）和问题覆盖率（15%）计算"
              ><small>结论置信度</small><strong>{{ percent(suggestion.confidence) }}</strong></span
            >
            <span
              ><small>证据评论</small><strong>{{ suggestion.evidence_count }} 条</strong></span
            >
          </div>
          <p class="confidence-note">
            置信度衡量这条改良结论的证据可靠程度，由评论判定可靠度、证据数量和问题覆盖率综合计算。
          </p>
          <div class="suggestion__body">
            <div class="suggestion__editor">
              <label>建议标题<input v-model="suggestion.title" class="title-input" /></label>
              <label>改良方案<textarea v-model="suggestion.description" rows="4"></textarea></label>
              <details v-if="suggestion.evidence_count" class="evidence-reviews">
                <summary>查看 {{ suggestion.evidence_count }} 条证据评论</summary>
                <div v-if="suggestionEvidence(suggestion).length" class="evidence-reviews__list">
                  <article
                    v-for="evidence in suggestionEvidence(suggestion)"
                    :key="evidence.review_id"
                  >
                    <strong>{{ evidence.rating }} 星 · 原评论</strong>
                    <p>{{ evidence.original_content }}</p>
                    <p v-if="evidence.translated_content" class="evidence-reviews__translation">
                      译文：{{ evidence.translated_content }}
                    </p>
                  </article>
                </div>
                <p v-else class="evidence-reviews__empty">评论内容暂未加载。</p>
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

      <SpCard v-if="drafts.length" class="draft-history">
        <header class="draft-history__heading">
          <div>
            <small>持久化草稿</small>
            <h3>产品改良草稿历史</h3>
            <p>在本页查看和编辑；保存修改会新增版本，不覆盖旧版本。</p>
          </div>
          <div class="draft-history__heading-actions">
            <SpBadge variant="info">{{ drafts.length }} 个版本</SpBadge>
            <SpButton
              size="sm"
              variant="secondary"
              :loading="action === 'clear-history'"
              @click="requestDraftHistoryClear"
            >
              清空草稿历史
            </SpButton>
          </div>
        </header>
        <div class="draft-history__body">
          <nav aria-label="改良草稿版本">
            <button
              v-for="(draft, index) in drafts"
              :key="draft.id"
              type="button"
              :class="{ active: activeDraft?.id === draft.id }"
              @click="selectDraft(draft)"
            >
              <strong>v{{ draft.sequence }}</strong>
              <span>{{ index === 0 ? "最新版本" : draft.change_summary }}</span>
            </button>
          </nav>
          <section v-if="activeDraft" class="draft-editor">
            <div class="draft-editor__toolbar">
              <div>
                <strong>{{ activeDraft.source_product_id }} 改良方案</strong>
                <span>{{ activeDraft.site.toUpperCase() }} · Mock</span>
              </div>
              <SpButton
                v-if="activeDraft.id === drafts[0]?.id && !draftEditing"
                size="sm"
                variant="secondary"
                @click="startDraftEditing"
              >
                编辑最新草稿
              </SpButton>
            </div>
            <div v-for="(item, index) in draftEditor" :key="index" class="draft-editor__item">
              <template v-if="draftEditing">
                <label>
                  改良项标题
                  <input v-model="item.title" maxlength="255" />
                </label>
                <label>
                  改良方案
                  <textarea v-model="item.description" rows="4" maxlength="4000"></textarea>
                </label>
              </template>
              <template v-else>
                <strong>{{ item.title }}</strong>
                <p>{{ item.description }}</p>
              </template>
            </div>
            <p v-if="activeDraft.id !== drafts[0]?.id" class="draft-editor__hint">
              这是历史只读版本；如需修改，请选择最新版本。
            </p>
            <div v-if="draftEditing" class="draft-editor__actions">
              <SpButton variant="secondary" @click="cancelDraftEditing"> 取消编辑 </SpButton>
              <SpButton :loading="action === 'request-revision'" @click="requestDraftRevision">
                申请保存新版本
              </SpButton>
            </div>
          </section>
        </div>
      </SpCard>

      <SpCard v-if="confirmation" class="confirmation">
        <div class="confirmation__main">
          <div class="confirmation__icon"><ShieldCheck :size="22" /></div>
          <div class="confirmation__copy">
            <SpBadge :variant="confirmationStatus === 'PENDING' ? 'warning' : 'info'">
              {{ confirmationStatusLabel }}
            </SpBadge>
            <h3>
              {{
                confirmationPurpose === "clear"
                  ? "清空产品改良草稿历史"
                  : confirmationPurpose === "revision"
                    ? "保存改良草稿新版本"
                    : "创建产品改良草稿"
              }}
            </h3>
            <p>{{ confirmation.risk_warning }}</p>
            <p v-if="confirmation.execution_result">
              {{
                confirmationPurpose === "clear"
                  ? "页面历史已清空；底层审计记录保留，后续草稿从 v1 重新编号。"
                  : confirmationPurpose === "revision"
                    ? "新版本已保存，旧版本仍可在本页查看。"
                    : "草稿已保存为产品改良的待编辑版本；任务中心仅保留本次操作记录。"
              }}
            </p>
          </div>
        </div>
        <div class="confirmation__actions">
          <SpButton
            v-if="confirmationStatus === 'PENDING'"
            :loading="action === 'confirm'"
            @click="confirmDraft"
          >
            {{
              confirmationPurpose === "clear"
                ? "确认清空历史"
                : confirmationPurpose === "revision"
                  ? "确认保存新版本"
                  : "确认创建草稿"
            }}
          </SpButton>
          <SpButton
            v-if="confirmationStatus === 'PENDING'"
            variant="secondary"
            :loading="action === 'cancel'"
            @click="cancelDraft"
          >
            取消
          </SpButton>
          <SpButton
            v-if="confirmation.execution_result && confirmationPurpose === 'create'"
            @click="draftPreviewVisible = !draftPreviewVisible"
          >
            {{ draftPreviewVisible ? "收起改良草稿" : "查看改良草稿" }}
          </SpButton>
        </div>
        <section
          v-if="confirmation.execution_result && draftPreviewVisible"
          class="draft-preview"
          aria-label="产品改良草稿"
        >
          <header>
            <div>
              <small>已保存草稿</small>
              <h4>{{ report.source_product_id }} 产品改良方案</h4>
            </div>
            <SpBadge variant="info">{{ reportSite.toUpperCase() }} · Mock</SpBadge>
          </header>
          <ol>
            <li v-for="suggestion in savedDraftSuggestions" :key="suggestion.id">
              <strong>{{ suggestion.title }}</strong>
              <p>{{ suggestion.description }}</p>
            </li>
          </ol>
          <p class="draft-preview__note">
            这是供运营和工厂继续审核的改良方案，不是已发布的商品文案，也不会自动修改商品。
          </p>
        </section>
      </SpCard>
    </template>
  </PageContainer>
</template>

<style scoped>
.page-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--sp-space-4);
}
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
.confidence-note {
  margin: var(--sp-space-2) 0 0;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-sm);
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
.evidence-reviews__list {
  display: grid;
  gap: var(--sp-space-2);
  margin-top: var(--sp-space-3);
}
.evidence-reviews article {
  padding: var(--sp-space-3);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.evidence-reviews article p {
  margin: var(--sp-space-2) 0 0;
  color: var(--sp-color-text);
  line-height: 1.6;
}
.evidence-reviews article .evidence-reviews__translation {
  color: var(--sp-color-text-secondary);
}
.evidence-reviews__empty {
  margin: var(--sp-space-3) 0 0;
  color: var(--sp-color-text-muted);
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
.draft-history {
  margin-top: var(--sp-space-5);
  padding: var(--sp-space-5);
}
.draft-history__heading,
.draft-history__heading-actions,
.draft-editor__toolbar,
.draft-editor__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-3);
}
.draft-history__heading-actions {
  flex: 0 0 auto;
}
.draft-history__heading h3,
.draft-history__heading p {
  margin: 0;
}
.draft-history__heading h3 {
  margin: var(--sp-space-1) 0;
}
.draft-history__heading p,
.draft-editor__toolbar span,
.draft-editor__hint {
  color: var(--sp-color-text-muted);
}
.draft-history__body {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: var(--sp-space-4);
  margin-top: var(--sp-space-4);
}
.draft-history nav {
  display: grid;
  align-content: start;
  gap: var(--sp-space-2);
}
.draft-history nav button {
  display: grid;
  gap: var(--sp-space-1);
  padding: var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.draft-history nav button.active {
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-muted);
  border-color: var(--sp-color-primary);
}
.draft-history nav span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.draft-editor {
  display: grid;
  gap: var(--sp-space-3);
  min-width: 0;
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-control);
}
.draft-editor__toolbar > div {
  display: grid;
  gap: var(--sp-space-1);
}
.draft-editor__item {
  display: grid;
  gap: var(--sp-space-2);
  padding-top: var(--sp-space-3);
  border-top: 1px solid var(--sp-border-soft);
}
.draft-editor__item label {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}
.draft-editor__item p,
.draft-editor__hint {
  margin: 0;
}
.draft-editor__actions {
  justify-content: flex-end;
}
.confirmation {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  margin-top: var(--sp-space-5);
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
  align-items: flex-start;
}
.confirmation__copy {
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
  align-self: center;
  justify-content: flex-end;
}
.draft-preview {
  grid-column: 1 / -1;
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.draft-preview header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-space-3);
}
.draft-preview h4,
.draft-preview p {
  margin: 0;
}
.draft-preview h4 {
  margin-top: var(--sp-space-1);
}
.draft-preview small,
.draft-preview__note {
  color: var(--sp-color-text-muted);
}
.draft-preview ol {
  display: grid;
  gap: var(--sp-space-3);
  padding-left: var(--sp-space-5);
  margin: var(--sp-space-4) 0;
}
.draft-preview li p {
  margin-top: var(--sp-space-1);
  color: var(--sp-color-text-secondary);
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
  .draft-history__body {
    grid-template-columns: 1fr;
  }
  .draft-history nav {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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
    grid-template-columns: 1fr;
  }
  .confirmation__actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
