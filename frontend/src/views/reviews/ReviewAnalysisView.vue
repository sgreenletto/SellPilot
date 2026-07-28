<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { AlertTriangle, FlaskConical, RefreshCw, Search, Sparkles } from "@lucide/vue";
import { FrontendApiError } from "@/api/http";
import {
  createReviewAnalysis,
  listProductReviews,
  listReviewEvidence,
  runReviewAnalysis,
} from "@/api/review-analysis";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import SpSkeleton from "@/components/base/SpSkeleton.vue";
import ReviewTrendChart from "@/components/charts/ReviewTrendChart.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type {
  ProductReview,
  ReviewAnalysisResult,
  ReviewEvidencePage,
} from "@/types/review-analysis";
import type { SiteCode } from "@/types/selection";

const router = useRouter();
const form = reactive({
  productId: "PROD0001",
  site: "sg" as SiteCode,
  language: "",
  minRating: "1",
  maxRating: "5",
  sentiment: "",
  topic: "",
  createdFrom: "",
  createdTo: "",
});
const reviews = ref<ProductReview[]>([]);
const reviewPage = ref(1);
const reviewPageSize = 20;
const hasNextReviewPage = ref(false);
const result = ref<ReviewAnalysisResult | null>(null);
const evidence = ref<ReviewEvidencePage | null>(null);
const evidencePage = ref(1);
const evidenceType = ref("");
const evidenceLabel = ref("");
const selectedReviewId = ref("");
const loading = ref(false);
const analyzing = ref(false);
const error = ref("");
const errorCode = ref("");
const taskStatus = ref("IDLE");
const taskProgress = ref(0);
const taskMessage = ref("尚未创建分析任务");

const siteOptions = ["sg", "my", "ph", "th", "vn", "id"].map((value) => ({
  label: value.toUpperCase(),
  value,
}));
const ratingOptions = ["1", "2", "3", "4", "5"].map((value) => ({ label: `${value} 星`, value }));
const sentimentOptions = [
  { label: "全部情感", value: "" },
  { label: "正面", value: "positive" },
  { label: "中性", value: "neutral" },
  { label: "负面", value: "negative" },
];
const topicOptions = [
  { label: "全部主题", value: "" },
  { label: "产品质量", value: "product_quality" },
  { label: "包装", value: "packaging" },
  { label: "文案不符", value: "description_mismatch" },
  { label: "物流", value: "logistics" },
  { label: "服务", value: "service" },
];
const evidenceTypeOptions = [
  { label: "全部证据", value: "" },
  { label: "主题证据", value: "topic" },
];
const displayedReviews = computed(() =>
  reviews.value.filter(
    (review) =>
      (!form.sentiment || review.sentiment_hint === form.sentiment) &&
      (!form.topic || review.issue_type === form.topic),
  ),
);
const sentimentTotal = computed(() => {
  const item = result.value?.sentiment;
  return item ? item.positive + item.neutral + item.negative : 0;
});
const issueGroups = computed(() => {
  const labels: Record<string, string> = {
    product_quality: "产品",
    packaging: "包装",
    description_mismatch: "文案",
    logistics: "物流",
    service: "服务",
  };
  return Object.entries(labels).map(([key, label]) => ({
    key,
    label,
    count: result.value?.topics.find((item) => item.topic === key)?.count ?? 0,
  }));
});

function handleError(reason: unknown): void {
  const apiError = reason instanceof FrontendApiError ? reason : null;
  error.value = apiError?.message ?? (reason instanceof Error ? reason.message : "操作失败");
  errorCode.value = apiError?.code ?? "UNKNOWN_ERROR";
}
function query() {
  return {
    product_id: form.productId.trim(),
    site: form.site,
    language: form.language.trim() || undefined,
    min_rating: Number(form.minRating),
    max_rating: Number(form.maxRating),
    created_from: form.createdFrom || undefined,
    created_to: form.createdTo || undefined,
    offset: (reviewPage.value - 1) * reviewPageSize,
    limit: reviewPageSize,
  };
}
async function loadReviews(resetPage = true): Promise<void> {
  if (!form.productId.trim()) {
    error.value = "请输入商品 ID";
    return;
  }
  loading.value = true;
  error.value = "";
  errorCode.value = "";
  selectedReviewId.value = "";
  if (resetPage) reviewPage.value = 1;
  try {
    reviews.value = await listProductReviews(query());
    hasNextReviewPage.value = reviews.value.length === reviewPageSize;
  } catch (reason) {
    reviews.value = [];
    handleError(reason);
  } finally {
    loading.value = false;
  }
}
async function changeReviewPage(page: number): Promise<void> {
  if (page < 1) return;
  reviewPage.value = page;
  await loadReviews(false);
}
async function analyze(): Promise<void> {
  if (!form.productId.trim()) return;
  analyzing.value = true;
  error.value = "";
  result.value = null;
  evidence.value = null;
  taskStatus.value = "CREATING";
  taskProgress.value = 0;
  taskMessage.value = "正在创建分析任务";
  try {
    const created = await createReviewAnalysis({
      idempotency_key: `review-ui-${form.productId}-${Date.now()}`,
      product_id: form.productId.trim(),
      site: form.site,
      languages: form.language.trim() ? [form.language.trim()] : [],
      min_rating: Number(form.minRating),
      max_rating: Number(form.maxRating),
      created_from: form.createdFrom || undefined,
      created_to: form.createdTo || undefined,
      batch_size: 100,
      maximum_reviews: 1000,
      max_attempts: 2,
    });
    taskStatus.value = created.status;
    taskProgress.value = 10;
    taskMessage.value = created.duplicate ? "复用已有幂等任务" : "任务已创建，准备运行";
    taskStatus.value = "RUNNING";
    taskProgress.value = 35;
    taskMessage.value = "正在加载评论并运行规则分析";
    result.value = await runReviewAnalysis(created.analysis_id);
    taskStatus.value = result.value.status;
    taskProgress.value = result.value.progress;
    taskMessage.value = result.value.current_step ?? "分析完成";
    evidencePage.value = 1;
    evidence.value = await listReviewEvidence(created.analysis_id, 1);
  } catch (reason) {
    taskStatus.value = "FAILED";
    taskMessage.value = reason instanceof Error ? reason.message : "分析失败";
    handleError(reason);
  } finally {
    analyzing.value = false;
  }
}
async function changeEvidenceType(value: string): Promise<void> {
  evidenceType.value = value;
  evidenceLabel.value = "";
  if (!result.value) return;
  evidencePage.value = 1;
  evidence.value = await listReviewEvidence(result.value.analysis_id, 1, value);
}
async function filterEvidenceLabel(label: string): Promise<void> {
  evidenceType.value = "topic";
  evidenceLabel.value = label;
  if (!result.value) return;
  evidencePage.value = 1;
  evidence.value = await listReviewEvidence(result.value.analysis_id, 1, "topic", label);
}
async function changeEvidencePage(page: number): Promise<void> {
  if (!result.value || page < 1) return;
  evidencePage.value = page;
  evidence.value = await listReviewEvidence(
    result.value.analysis_id,
    page,
    evidenceType.value,
    evidenceLabel.value,
  );
}
function locateReview(reviewId: string): void {
  selectedReviewId.value = reviewId;
  document
    .getElementById(`review-${reviewId}`)
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}
onMounted(loadReviews);
</script>

<template>
  <PageContainer
    eyebrow="REVIEW INTELLIGENCE · MOCK SHOPEE"
    title="评论与产品改良"
    description="用可追溯证据查看情感、主题、痛点和站点趋势。"
  >
    <section class="workbench-hero">
      <div>
        <span class="workbench-hero__eyebrow">REVIEW INTELLIGENCE · MOCK SHOPEE</span>
        <h2>评论洞察工作台</h2>
        <p>从多语言评论中提炼情感、主题、痛点与可追溯证据。</p>
      </div>
      <div class="workbench-hero__facts">
        <span
          ><strong>{{ reviews.length }}</strong> 当前评论</span
        >
        <span
          ><strong>{{ result?.progress ?? 0 }}%</strong> 分析进度</span
        >
        <span><strong>Rule</strong> 当前模式</span>
      </div>
    </section>
    <template #actions
      ><SpBadge tone="info"><FlaskConical :size="14" /> 模拟实验数据</SpBadge></template
    >

    <div v-if="error" class="alert" role="alert">
      <AlertTriangle :size="18" />
      <div>
        <strong>{{ errorCode === "NETWORK_ERROR" ? "后端未连接" : "分析失败" }}</strong>
        <p>{{ error }}</p>
      </div>
      <SpButton
        size="sm"
        variant="secondary"
        @click="errorCode === 'NETWORK_ERROR' ? loadReviews() : analyze()"
        ><template #icon><RefreshCw :size="15" /></template>重试</SpButton
      >
    </div>

    <SpCard class="filters">
      <SpInput v-model="form.productId" label="商品 ID" placeholder="例如 PROD0001" />
      <SpSelect v-model="form.site" label="站点" :options="siteOptions" />
      <SpInput v-model="form.language" label="语言" placeholder="留空为全部语言" />
      <SpSelect v-model="form.minRating" label="最低评分" :options="ratingOptions" />
      <SpSelect v-model="form.maxRating" label="最高评分" :options="ratingOptions" />
      <SpSelect v-model="form.sentiment" label="情感" :options="sentimentOptions" />
      <SpSelect v-model="form.topic" label="主题" :options="topicOptions" />
      <label>开始时间<input v-model="form.createdFrom" type="date" /></label>
      <label>结束时间<input v-model="form.createdTo" type="date" /></label>
      <SpButton :loading="loading" @click="loadReviews"
        ><template #icon><Search :size="16" /></template>筛选评论</SpButton
      >
      <SpButton :loading="analyzing" :disabled="reviews.length === 0" @click="analyze"
        ><template #icon><Sparkles :size="16" /></template>运行分析</SpButton
      >
    </SpCard>

    <SpCard class="task-panel" variant="flat">
      <div class="section-title">
        <div>
          <small>分析任务状态</small>
          <h3>{{ taskStatus }} · {{ taskMessage }}</h3>
        </div>
        <strong>{{ taskProgress }}%</strong>
      </div>
      <div class="task-track"><i :style="{ width: `${taskProgress}%` }"></i></div>
      <ol v-if="result?.steps.length" class="task-steps">
        <li v-for="step in result.steps" :key="step.step_name">
          <span>{{ step.step_name }}</span
          ><strong>{{ step.status }}</strong>
          <small v-if="step.error_message">{{ step.error_message }}</small>
        </li>
      </ol>
    </SpCard>

    <div v-if="analyzing" class="progress" aria-live="polite">
      <SpSkeleton v-for="n in 3" :key="n" height="72px" />
      <p>正在加载评论、分析并保存证据，请稍候…</p>
    </div>
    <template v-else-if="result?.status === 'SUCCEEDED'">
      <section class="summary-grid">
        <SpCard
          ><h3>情感分布</h3>
          <div v-if="result.sentiment" class="sentiments">
            <span>正面 {{ result.sentiment.positive }}</span
            ><span>中性 {{ result.sentiment.neutral }}</span
            ><span>负面 {{ result.sentiment.negative }}</span>
          </div>
          <small
            >共 {{ sentimentTotal }} 条有效评论 ·
            {{ result.analysis_mode === "rule" ? "规则分析" : "已验证模型" }}</small
          ></SpCard
        >
        <SpCard
          ><h3>五类问题</h3>
          <div class="issue-grid">
            <span v-for="item in issueGroups" :key="item.key"
              >{{ item.label }} <strong>{{ item.count }}</strong></span
            >
          </div></SpCard
        >
        <SpCard
          ><h3>高频痛点</h3>
          <button
            v-for="item in result.pain_points.slice(0, 6)"
            :key="item.pain_point"
            class="tag"
            @click="filterEvidenceLabel(item.pain_point)"
          >
            {{ item.pain_point }} · {{ item.negative_count }}
          </button></SpCard
        >
      </section>
      <SpCard
        ><h3>时间与站点趋势</h3>
        <ReviewTrendChart :points="result.trends"
      /></SpCard>
      <SpCard
        ><div class="section-title">
          <h3>代表评论与证据</h3>
          <div class="evidence-actions">
            <SpSelect
              :model-value="evidenceType"
              aria-label="证据类型"
              :options="evidenceTypeOptions"
              @update:model-value="changeEvidenceType"
            />
            <SpBadge v-if="evidenceLabel" variant="info"> 主题：{{ evidenceLabel }} </SpBadge>
            <SpButton
              size="sm"
              variant="secondary"
              @click="router.push({ path: '/market/reviews', query: { panel: 'improvement' } })"
              >进入产品改良（Step 8）</SpButton
            >
          </div>
        </div>
        <div v-if="evidence?.items.length" class="evidence-list">
          <article v-for="item in evidence.items" :key="item.id">
            <button @click="locateReview(item.review_id)">定位评论 {{ item.review_id }}</button
            ><strong>{{ item.label }} · 置信度 {{ Number(item.confidence).toFixed(2) }}</strong>
            <p>{{ item.original_content }}</p>
            <p v-if="item.translated_content">译文：{{ item.translated_content }}</p>
            <small v-else>未提供翻译（当前未接入真实翻译服务）</small>
          </article>
        </div>
        <SpEmptyState v-else title="暂无分析证据" description="当前结果没有可展示的代表评论。" />
        <div v-if="evidence && evidence.total > evidence.page_size" class="pager">
          <SpButton
            size="sm"
            variant="ghost"
            :disabled="evidencePage === 1"
            @click="changeEvidencePage(evidencePage - 1)"
            >上一页</SpButton
          ><span>第 {{ evidencePage }} 页</span
          ><SpButton
            size="sm"
            variant="ghost"
            :disabled="evidencePage * evidence.page_size >= evidence.total"
            @click="changeEvidencePage(evidencePage + 1)"
            >下一页</SpButton
          >
        </div>
      </SpCard>
    </template>

    <SpCard
      ><div class="section-title">
        <h3>评论原文与翻译</h3>
        <span>第 {{ reviewPage }} 页 · {{ displayedReviews.length }} 条</span>
      </div>
      <div v-if="displayedReviews.length" class="review-list">
        <article
          v-for="review in displayedReviews"
          :id="`review-${review.review_id}`"
          :key="review.review_id"
          :class="{ selected: selectedReviewId === review.review_id }"
          tabindex="0"
        >
          <div>
            <strong>{{ review.rating }} 星 · {{ review.language }}</strong
            ><SpBadge tone="info">{{ review.sentiment_hint }}</SpBadge
            ><SpBadge tone="warning">{{ review.issue_type }}</SpBadge>
          </div>
          <p>{{ review.content }}</p>
          <p v-if="review.translated_content">译文：{{ review.translated_content }}</p>
          <small v-else>无翻译 · 当前仅展示数据源已有译文</small>
        </article>
      </div>
      <SpEmptyState
        v-else
        title="暂无评论"
        :description="
          errorCode === 'NETWORK_ERROR'
            ? '后端未连接，无法加载评论。'
            : '请调整商品、站点、评分、语言或时间条件。'
        "
      />
      <div class="pager">
        <SpButton
          size="sm"
          variant="ghost"
          :disabled="reviewPage === 1 || loading"
          @click="changeReviewPage(reviewPage - 1)"
          >上一页</SpButton
        ><span>第 {{ reviewPage }} 页</span
        ><SpButton
          size="sm"
          variant="ghost"
          :disabled="!hasNextReviewPage || loading"
          @click="changeReviewPage(reviewPage + 1)"
          >下一页</SpButton
        >
      </div>
    </SpCard>
  </PageContainer>
</template>

<style scoped>
.workbench-hero {
  display: flex;
  gap: var(--sp-space-6);
  align-items: flex-end;
  justify-content: space-between;
  padding: var(--sp-space-6);
  margin-bottom: var(--sp-space-5);
  color: white;
  background:
    radial-gradient(circle at 88% 0%, rgb(91 164 255 / 45%), transparent 34%),
    linear-gradient(135deg, #102b5c 0%, #244f91 58%, #6755b9 100%);
  border-radius: calc(var(--sp-radius-card) + 4px);
  box-shadow: 0 18px 42px rgb(20 48 94 / 20%);
}
.workbench-hero__eyebrow {
  color: #9fd3ff;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.12em;
}
.workbench-hero h2 {
  margin: 8px 0 6px;
  font-size: clamp(24px, 3vw, 36px);
}
.workbench-hero p {
  margin: 0;
  color: rgb(255 255 255 / 72%);
}
.workbench-hero__facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(90px, 1fr));
  gap: 10px;
}
.workbench-hero__facts span {
  display: grid;
  padding: 12px 16px;
  color: rgb(255 255 255 / 70%);
  font-size: 12px;
  background: rgb(255 255 255 / 10%);
  border: 1px solid rgb(255 255 255 / 15%);
  border-radius: 16px;
}
.workbench-hero__facts strong {
  color: white;
  font-size: 20px;
}
.filters {
  margin-bottom: var(--sp-space-5);
}
.task-panel {
  margin-bottom: var(--sp-space-5);
}
.task-panel h3 {
  margin: 4px 0 0;
}
.task-track {
  height: 8px;
  margin-top: var(--sp-space-3);
  overflow: hidden;
  background: var(--sp-color-surface-hover);
  border-radius: 999px;
}
.task-track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--sp-color-accent-blue), #7766d8);
  border-radius: inherit;
  transition: width 0.3s ease;
}
.task-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-space-3);
  padding: 0;
  margin: var(--sp-space-4) 0 0;
  list-style: none;
}
.task-steps li {
  display: grid;
  gap: 4px;
  padding: var(--sp-space-3);
  background: var(--sp-color-surface);
  border-radius: var(--sp-radius-control);
}
.evidence-actions {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
}
.filters :deep(.sp-card__body) {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: var(--sp-space-4);
  align-items: end;
}
.filters label {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}
.filters input {
  min-height: 40px;
  padding: 0 var(--sp-space-3);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-surface);
}
.alert {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  padding: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
  color: var(--sp-color-danger);
  background: var(--sp-color-danger-soft);
  border-radius: var(--sp-radius-card);
}
.alert div {
  flex: 1;
}
.alert p {
  margin: 4px 0 0;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
}
.sentiments,
.issue-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-3);
}
.sentiments span,
.issue-grid span,
.tag {
  padding: 8px 12px;
  border: 0;
  border-radius: 999px;
  background: var(--sp-color-surface-hover);
}
.tag {
  margin: 0 6px 6px 0;
  cursor: pointer;
}
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-3);
}
.review-list,
.evidence-list {
  display: grid;
  gap: var(--sp-space-3);
}
.review-list article,
.evidence-list article {
  padding: var(--sp-space-4);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-card);
}
.review-list article.selected {
  border-color: var(--sp-color-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-color-accent-blue) 15%, transparent);
}
.review-list article > div {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
}
.evidence-list button {
  margin-right: var(--sp-space-3);
  color: var(--sp-color-primary);
  background: none;
  border: 0;
  cursor: pointer;
}
.pager,
.progress {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: center;
  margin-top: var(--sp-space-4);
}
@media (max-width: 1100px) {
  .filters :deep(.sp-card__body) {
    grid-template-columns: repeat(2, 1fr);
  }
  .workbench-hero {
    align-items: flex-start;
    flex-direction: column;
  }
  .summary-grid {
    grid-template-columns: 1fr;
  }
  .task-steps {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .filters :deep(.sp-card__body) {
    grid-template-columns: 1fr;
  }
  .workbench-hero__facts {
    width: 100%;
    grid-template-columns: 1fr;
  }
  .section-title {
    align-items: flex-start;
    flex-direction: column;
  }
  .evidence-actions {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
