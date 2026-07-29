<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { AlertTriangle, RefreshCw, Search, Sparkles } from "@lucide/vue";
import { FrontendApiError } from "@/api/http";
import {
  createReviewAnalysis,
  exportReviewAnalysis,
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
  keyword: "",
  site: "sg" as SiteCode,
  language: "all",
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
const evidenceLabel = ref("");
const selectedReviewId = ref("");
const loading = ref(false);
const analyzing = ref(false);
const exporting = ref(false);
const error = ref("");
const errorCode = ref("");

const siteOptions = ["sg", "my", "ph", "th", "vn", "id"].map((value) => ({
  label: value.toUpperCase(),
  value,
}));
const ratingOptions = ["1", "2", "3", "4", "5"].map((value) => ({ label: `${value} 星`, value }));
const languageOptions = [
  { label: "全部语言", value: "all" },
  { label: "英语", value: "English" },
  { label: "菲律宾语", value: "Filipino" },
  { label: "印度尼西亚语", value: "Indonesian" },
  { label: "马来语", value: "Malay" },
  { label: "泰语", value: "Thai" },
  { label: "越南语", value: "Vietnamese" },
];
const sentimentOptions = [
  { label: "全部情感", value: "" },
  { label: "正面", value: "positive" },
  { label: "中性", value: "neutral" },
  { label: "负面", value: "negative" },
];
const topicOptions = [
  { label: "全部方面", value: "" },
  { label: "产品质量", value: "product_quality" },
  { label: "包装", value: "packaging" },
  { label: "描述不符", value: "description_mismatch" },
  { label: "物流", value: "logistics" },
  { label: "服务", value: "service" },
];
const topicLabels: Record<string, string> = {
  product_quality: "产品质量",
  packaging: "包装",
  description_mismatch: "描述不符",
  logistics: "物流",
  service: "服务",
  material: "材料",
  size_specification: "尺寸规格",
  wrong_or_missing_item: "错发漏发",
  other: "其他",
  no_clear_issue: "无明确问题",
};
const languageLabels: Record<string, string> = {
  English: "英语",
  Filipino: "菲律宾语",
  Indonesian: "印度尼西亚语",
  Malay: "马来语",
  Thai: "泰语",
  Vietnamese: "越南语",
  en: "英语",
  tl: "菲律宾语",
  id: "印度尼西亚语",
  ms: "马来语",
  th: "泰语",
  vi: "越南语",
};
const sentimentLabels: Record<string, string> = {
  positive: "正向",
  neutral: "中性",
  negative: "含改进信号",
};
const issueTypeLabels: Record<string, string> = {
  battery: "电池",
  customer_service: "客服",
  logistics: "物流",
  material: "材料",
  none: "无明确问题",
  no_clear_issue: "无明确问题",
  other: "其他问题",
  packaging: "包装",
  product_quality: "产品质量",
  size: "尺寸规格",
  size_specification: "尺寸规格",
  wrong_item: "错发商品",
  wrong_or_missing_item: "错发漏发",
  description_mismatch: "描述不符",
  service: "服务",
};
const keywordLabels: Record<string, string> = {
  quality: "质量",
  finish: "做工",
  broken: "损坏",
  defect: "缺陷",
  damaged: "损坏",
  kualitas: "质量",
  rosak: "损坏",
  คุณภาพ: "质量",
  เสีย: "损坏",
  "chất lượng": "质量",
  hỏng: "损坏",
  packaging: "包装",
  package: "包装",
  box: "包装盒",
  kemasan: "包装",
  bungkusan: "包装",
  บรรจุ: "包装",
  hộp: "包装盒",
  "đóng gói": "包装",
  "not as described": "与描述不符",
  "does not match the product description": "与描述不符",
  "doesn't match the product description": "与描述不符",
  "does not match description": "与描述不符",
  "different from": "与描述不符",
  "tidak sesuai": "与描述不符",
  "tak sama": "与描述不符",
  ไม่ตรง: "与描述不符",
  "không giống": "与描述不符",
  delivery: "配送",
  shipping: "物流",
  late: "配送延迟",
  courier: "快递",
  pengiriman: "配送",
  penghantaran: "配送",
  huli: "配送",
  จัดส่ง: "配送",
  ส่งช้า: "配送延迟",
  "giao hàng": "配送",
  service: "服务",
  seller: "商家",
  reply: "回复",
  support: "售后支持",
  layanan: "服务",
  perkhidmatan: "服务",
  serbisyo: "服务",
  บริการ: "服务",
  "dịch vụ": "服务",
  material: "材料",
  plastic: "塑料",
  fabric: "面料",
  bahan: "材料",
  materyal: "材料",
  วัสดุ: "材料",
  "chất liệu": "材料",
  size: "尺寸",
  small: "尺寸偏小",
  large: "尺寸偏大",
  measurement: "尺寸规格",
  ukuran: "尺寸",
  saiz: "尺寸",
  sukat: "尺寸",
  ขนาด: "尺寸",
  "kích thước": "尺寸",
  "wrong item": "错发商品",
  "missing item": "漏发商品",
  incomplete: "配件不全",
  "salah barang": "错发商品",
  kurang: "漏发商品",
  "maling item": "错发商品",
  ผิดชิ้น: "错发商品",
  thiếu: "漏发商品",
  "sai hàng": "错发商品",
};
const localizedLanguage = (value: string) => languageLabels[value] ?? value;
const localizedSentiment = (value: string) => sentimentLabels[value] ?? value;
const localizedIssueType = (value: string) => issueTypeLabels[value] ?? value;
const localizedKeyword = (value: string) => keywordLabels[value.toLocaleLowerCase()] ?? value;
function evidenceTopicText(label: string, sentiment: string | null | undefined): string {
  if (sentiment === "negative") {
    return `改进 · ${topicLabels[label] ?? label}`;
  }
  return `提及 · ${topicLabels[label] ?? label}`;
}
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
const qualitySummary = computed(() => {
  const quality = result.value?.quality;
  if (!quality) return "";
  const reasonLabels: Record<string, string> = {
    duplicate: "重复",
    empty: "空内容",
    emoji_only: "仅表情",
    spam: "垃圾内容",
  };
  const reasons = Object.entries(quality.flag_counts ?? {})
    .filter(([key, count]) => key in reasonLabels && count > 0)
    .map(([key, count]) => `${reasonLabels[key]} ${count} 条`);
  const excluded = quality.excluded_count
    ? `，排除 ${quality.excluded_count} 条${reasons.length ? `（${reasons.join("、")}）` : ""}`
    : "";
  return `筛选到 ${quality.received_count} 条，纳入分析 ${quality.included_count} 条${excluded}`;
});
const hasComparableTrend = computed(() => (result.value?.trends.length ?? 0) > 1);
const groupedEvidence = computed(() => {
  const grouped = new Map<
    string,
    NonNullable<typeof evidence.value>["items"][number] & { labels: string[] }
  >();
  for (const item of evidence.value?.items ?? []) {
    const current = grouped.get(item.review_id);
    if (current) {
      if (!current.labels.includes(item.label)) current.labels.push(item.label);
      continue;
    }
    grouped.set(item.review_id, { ...item, labels: [item.label] });
  }
  return [...grouped.values()]
    .filter((item) => item.sentiment === "negative")
    .map((item) => {
      const text = `${item.original_content} ${item.translated_content ?? ""}`.toLocaleLowerCase();
      const explicitlyAligned =
        text.includes("matches the photo") ||
        text.includes("works as described") ||
        text.includes("与图片一致") ||
        text.includes("符合描述");
      return {
        ...item,
        labels: item.labels.filter(
          (label) => label !== "description_mismatch" || !explicitlyAligned,
        ),
      };
    });
});
const visibleTopicLabels = computed(
  () => new Set(groupedEvidence.value.flatMap((item) => item.labels)),
);
const displayedPainPoints = computed(() =>
  (result.value?.pain_points ?? []).filter((item) => visibleTopicLabels.value.has(item.pain_point)),
);
const displayedTopics = computed(() =>
  (result.value?.topics ?? []).filter((item) => item.topic !== "no_clear_issue").slice(0, 6),
);
const displayedKeywords = computed(() => (result.value?.keywords ?? []).slice(0, 8));
const judgementByReviewId = computed(
  () => new Map((result.value?.judgements ?? []).map((item) => [item.review_id, item])),
);
function reviewSentiment(review: ProductReview): string {
  return judgementByReviewId.value.get(review.review_id)?.sentiment ?? review.sentiment_hint;
}
function reviewTopics(review: ProductReview): string {
  const topics = judgementByReviewId.value.get(review.review_id)?.topics;
  return topics?.length
    ? topics.map((topic) => localizedIssueType(topic)).join("、")
    : localizedIssueType(review.issue_type);
}

function handleError(reason: unknown): void {
  const apiError = reason instanceof FrontendApiError ? reason : null;
  error.value = apiError?.message ?? (reason instanceof Error ? reason.message : "操作失败");
  errorCode.value = apiError?.code ?? "UNKNOWN_ERROR";
}
function query() {
  const selectedLanguage = form.language === "all" ? "" : form.language;
  return {
    product_id: form.productId.trim(),
    keyword: form.keyword.trim() || undefined,
    site: form.site,
    language: selectedLanguage || undefined,
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
  try {
    const selectedLanguage = form.language === "all" ? "" : form.language;
    const created = await createReviewAnalysis({
      idempotency_key: `review-ui-${form.productId}-${Date.now()}`,
      product_id: form.productId.trim(),
      keyword: form.keyword.trim() || undefined,
      site: form.site,
      languages: selectedLanguage ? [selectedLanguage] : [],
      min_rating: Number(form.minRating),
      max_rating: Number(form.maxRating),
      created_from: form.createdFrom || undefined,
      created_to: form.createdTo || undefined,
      batch_size: 100,
      maximum_reviews: 1000,
      max_attempts: 2,
    });
    result.value = await runReviewAnalysis(created.analysis_id);
    evidencePage.value = 1;
    evidence.value = await listReviewEvidence(created.analysis_id, 1);
  } catch (reason) {
    handleError(reason);
  } finally {
    analyzing.value = false;
  }
}
async function exportReport(): Promise<void> {
  if (!result.value) return;
  exporting.value = true;
  try {
    const exported = await exportReviewAnalysis(result.value.analysis_id);
    const blob = new Blob([exported.content], {
      type: `${exported.media_type};charset=utf-8`,
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = exported.filename;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (reason) {
    handleError(reason);
  } finally {
    exporting.value = false;
  }
}
async function changeEvidenceTopic(value: string): Promise<void> {
  evidenceLabel.value = value;
  if (!result.value) return;
  evidencePage.value = 1;
  evidence.value = await listReviewEvidence(
    result.value.analysis_id,
    1,
    value ? "topic" : "",
    value,
  );
}
async function filterEvidenceLabel(label: string): Promise<void> {
  await changeEvidenceTopic(label);
}
async function changeEvidencePage(page: number): Promise<void> {
  if (!result.value || page < 1) return;
  evidencePage.value = page;
  evidence.value = await listReviewEvidence(
    result.value.analysis_id,
    page,
    evidenceLabel.value ? "topic" : "",
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
    eyebrow="市场与选品 / 评论分析"
    title="评论与产品改良"
    description="筛选评论，查看情感、涉及方面、改进信号和对应原文。"
  >
    <template #actions><SpBadge tone="info">Mock Shopee · 规则分析</SpBadge></template>

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

    <SpCard class="filters" variant="solid">
      <div class="section-title">
        <div>
          <h2>选择评论范围</h2>
          <p>情感与涉及方面只筛选下方列表；分析范围由商品、关键词、站点、语言、评分和日期决定。</p>
        </div>
      </div>
      <div class="filter-grid">
        <SpInput v-model="form.productId" label="商品 ID" placeholder="例如 PROD0001" />
        <SpInput v-model="form.keyword" label="评论关键词" placeholder="搜索原文或中文译文" />
        <SpSelect v-model="form.site" label="站点" :options="siteOptions" />
        <SpSelect
          v-model="form.language"
          label="语言"
          placeholder="请选择语言"
          :options="languageOptions"
        />
        <SpSelect v-model="form.minRating" label="最低评分" :options="ratingOptions" />
        <SpSelect v-model="form.maxRating" label="最高评分" :options="ratingOptions" />
        <SpSelect v-model="form.sentiment" label="列表情感" :options="sentimentOptions" />
        <SpSelect v-model="form.topic" label="涉及方面" :options="topicOptions" />
        <label>开始日期<input v-model="form.createdFrom" type="date" /></label>
        <label>结束日期<input v-model="form.createdTo" type="date" /></label>
      </div>
      <div class="filter-actions">
        <span>当前页 {{ displayedReviews.length }} 条；单次分析最多读取 1,000 条匹配评论。</span>
        <SpButton :loading="loading" variant="secondary" @click="loadReviews()">
          <template #icon><Search :size="16" /></template>刷新评论
        </SpButton>
        <SpButton :loading="analyzing" :disabled="reviews.length === 0" @click="analyze">
          <template #icon><Sparkles :size="16" /></template>分析当前范围
        </SpButton>
      </div>
    </SpCard>

    <div v-if="analyzing" class="progress" aria-live="polite">
      <span class="progress__spinner"></span>
      <div>
        <strong>正在分析评论</strong>
        <p>加载评论、执行规则分析并保存证据…</p>
      </div>
    </div>
    <template v-else-if="result?.status === 'SUCCEEDED'">
      <section class="result-heading">
        <div>
          <small>评论分析结果</small>
          <h2>{{ result.product_id }} 评论概览</h2>
        </div>
        <div class="result-heading__actions">
          <SpButton :loading="exporting" variant="secondary" @click="exportReport">
            导出分析报告
          </SpButton>
          <SpButton
            variant="secondary"
            @click="
              router.push({
                path: '/market/reviews/improvement',
                query: { analysis_id: result.analysis_id },
              })
            "
            >生成产品改良报告</SpButton
          >
        </div>
      </section>
      <SpCard class="pain-card" variant="solid">
        <div class="section-title">
          <div>
            <h3>改进信号</h3>
            <p>按问题方向汇总，可点击查看对应评论原文。</p>
          </div>
          <strong class="signal-count">
            {{ result.sentiment?.negative ?? 0 }} / {{ sentimentTotal }} 条有效评论
          </strong>
        </div>
        <p v-if="qualitySummary" class="quality-summary">{{ qualitySummary }}</p>
        <div v-if="displayedPainPoints.length" class="pain-list">
          <button
            v-for="item in displayedPainPoints.slice(0, 6)"
            :key="item.pain_point"
            @click="filterEvidenceLabel(item.pain_point)"
          >
            <span>{{ topicLabels[item.pain_point] ?? item.pain_point }}</span
            ><strong>{{ item.negative_count }} 条</strong>
          </button>
        </div>
        <SpEmptyState
          v-else
          title="当前没有改进信号"
          description="所选评论中没有低评分或明确缺点表达，因此不会生成改良建议。"
        />
      </SpCard>
      <SpCard class="analysis-summary" variant="solid">
        <div class="section-title">
          <div>
            <h3>评论分析摘要</h3>
            <p>按需求保留情感分类、评论主题和高频关键词；主题只表示评论谈到了什么。</p>
          </div>
        </div>
        <div class="analysis-summary__grid">
          <section>
            <h4>情感分类</h4>
            <div class="sentiment-summary">
              <span
                ><strong>{{ result.sentiment?.positive ?? 0 }}</strong> 正向</span
              >
              <span
                ><strong>{{ result.sentiment?.neutral ?? 0 }}</strong> 中性</span
              >
              <span
                ><strong>{{ result.sentiment?.negative ?? 0 }}</strong> 含改进信号</span
              >
            </div>
          </section>
          <section>
            <h4>评论主题</h4>
            <div v-if="displayedTopics.length" class="summary-tags">
              <span v-for="item in displayedTopics" :key="item.topic">
                {{ topicLabels[item.topic] ?? item.topic }} · {{ item.count }}
              </span>
            </div>
            <small v-else>未识别到明确主题</small>
          </section>
          <section>
            <h4>高频关键词</h4>
            <div v-if="displayedKeywords.length" class="summary-tags">
              <span v-for="item in displayedKeywords" :key="item.keyword">
                {{ localizedKeyword(item.keyword) }} · {{ item.review_count }} 条
              </span>
            </div>
            <small v-else>当前范围没有高频关键词</small>
          </section>
        </div>
      </SpCard>
      <SpCard v-if="hasComparableTrend" class="trend-card" variant="solid">
        <div class="section-title">
          <div>
            <h3>时间与站点趋势</h3>
            <p>按月份和站点汇总评论量、负面评论与平均评分。</p>
          </div>
        </div>
        <ReviewTrendChart :points="result.trends" />
      </SpCard>
      <SpCard class="evidence-card" variant="solid">
        <div class="section-title">
          <div>
            <h3>改进证据</h3>
            <p>仅展示含明确缺点的评论；同一评论的多个改进方向合并展示。</p>
          </div>
          <button v-if="evidenceLabel" class="clear-filter" @click="changeEvidenceTopic('')">
            清除“{{ topicLabels[evidenceLabel] ?? evidenceLabel }}”筛选
          </button>
        </div>
        <div v-if="groupedEvidence.length" class="evidence-table">
          <article v-for="item in groupedEvidence" :key="item.review_id">
            <div class="evidence-table__meta">
              <button @click="locateReview(item.review_id)">{{ item.review_id }}</button>
              <span>{{ item.rating }} 星</span><span>{{ localizedLanguage(item.language) }}</span>
              <em v-if="item.sentiment === 'negative'">含改进信号</em>
            </div>
            <div class="evidence-table__content">
              <p>{{ item.original_content }}</p>
              <small>{{
                item.translated_content ? `译文：${item.translated_content}` : "数据源未提供译文"
              }}</small>
            </div>
            <div class="evidence-table__topics">
              <span v-for="label in item.labels" :key="label">{{
                evidenceTopicText(label, item.sentiment)
              }}</span>
              <span v-if="!item.labels.length">未识别明确方面</span>
            </div>
          </article>
        </div>
        <SpEmptyState
          v-else
          title="暂无匹配证据"
          description="当前分析结果没有可展示的代表评论。"
        />
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

    <SpCard class="reviews-card" variant="solid"
      ><div class="section-title">
        <div>
          <h3>评论原文</h3>
          <p>用于核对筛选范围和分析结果。</p>
        </div>
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
            <strong>{{ review.rating }} 星 · {{ localizedLanguage(review.language) }}</strong
            ><SpBadge tone="info">{{ localizedSentiment(reviewSentiment(review)) }}</SpBadge
            ><SpBadge tone="warning">{{ reviewTopics(review) }}</SpBadge>
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
.filters {
  margin-bottom: var(--sp-space-5);
}
.filters :deep(.sp-card__body) {
  display: block;
}
.filter-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(150px, 1fr));
  gap: var(--sp-space-4);
  align-items: end;
  margin-top: var(--sp-space-5);
}
.filter-grid label {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}
.filter-grid input {
  min-height: 40px;
  padding: 0 var(--sp-space-3);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-surface);
}
.filter-actions {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: flex-end;
  padding-top: var(--sp-space-5);
  margin-top: var(--sp-space-5);
  border-top: 1px solid var(--sp-border-soft);
}
.filter-actions > span {
  margin-right: auto;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.alert {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  padding: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
  color: var(--sp-color-danger);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-color-danger);
  border-radius: var(--sp-radius-card);
}
.alert div {
  flex: 1;
}
.alert p {
  margin: 4px 0 0;
}
.result-heading {
  display: flex;
  gap: var(--sp-space-5);
  align-items: end;
  justify-content: space-between;
  margin: var(--sp-space-8) 0 var(--sp-space-4);
}
.result-heading h2,
.section-title h2,
.section-title h3 {
  margin: 0;
}
.result-heading p,
.section-title p {
  margin: var(--sp-space-1) 0 0;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-sm);
}
.signal-count {
  color: var(--sp-color-primary);
  font-size: var(--sp-font-lg);
  white-space: nowrap;
}
.quality-summary {
  margin: var(--sp-space-2) 0 0;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-sm);
}
.result-heading__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.pain-list {
  display: grid;
  gap: var(--sp-space-2);
  margin-top: var(--sp-space-5);
}
.pain-list button {
  display: flex;
  justify-content: space-between;
  padding: var(--sp-space-3);
  color: var(--sp-color-text);
  text-align: left;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
  cursor: pointer;
}
.analysis-summary {
  margin-top: var(--sp-space-4);
}
.analysis-summary__grid {
  display: grid;
  grid-template-columns: 0.8fr 1.1fr 1.1fr;
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-4);
}
.analysis-summary__grid section {
  min-width: 0;
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
}
.analysis-summary__grid h4 {
  margin: 0 0 var(--sp-space-3);
}
.analysis-summary__grid small {
  color: var(--sp-color-text-muted);
}
.sentiment-summary,
.summary-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
}
.sentiment-summary span,
.summary-tags span {
  padding: var(--sp-space-2) var(--sp-space-3);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-pill);
}
.sentiment-summary strong {
  color: var(--sp-color-primary);
}
.trend-card,
.evidence-card,
.reviews-card {
  margin-top: var(--sp-space-4);
}
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-3);
}
.review-list,
.evidence-table {
  display: grid;
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-5);
}
.review-list article,
.evidence-table article {
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
.evidence-table article {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) 180px;
  gap: var(--sp-space-4);
}
.evidence-table__meta {
  display: grid;
  align-content: start;
  gap: var(--sp-space-1);
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.evidence-table__meta button,
.clear-filter {
  color: var(--sp-color-primary);
  background: none;
  border: 0;
  cursor: pointer;
}
.evidence-table__meta button {
  padding: 0;
  font-weight: 700;
  text-align: left;
}
.evidence-table__meta em {
  width: fit-content;
  padding: var(--sp-space-1) var(--sp-space-2);
  color: var(--sp-color-warning);
  font-style: normal;
  font-weight: 700;
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-pill);
}
.evidence-table__content p {
  margin: 0 0 var(--sp-space-2);
}
.evidence-table__topics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
  align-content: start;
}
.evidence-table__topics span {
  padding: var(--sp-space-1) var(--sp-space-2);
  font-size: var(--sp-font-xs);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-pill);
}
.pager,
.progress {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: center;
  margin-top: var(--sp-space-4);
}
.progress {
  padding: var(--sp-space-5);
  background: var(--sp-color-surface);
  border-radius: var(--sp-radius-card);
}
.progress p {
  margin: var(--sp-space-1) 0 0;
  color: var(--sp-color-text-muted);
}
.progress__spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--sp-border-strong);
  border-top-color: var(--sp-color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 1100px) {
  .filter-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .evidence-table article {
    grid-template-columns: 150px minmax(0, 1fr);
  }
  .analysis-summary__grid {
    grid-template-columns: 1fr;
  }
  .evidence-table__topics {
    grid-column: 2;
  }
}
@media (max-width: 640px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
  .filter-actions,
  .result-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .filter-actions > span {
    margin-right: 0;
  }
  .section-title {
    align-items: flex-start;
    flex-direction: column;
  }
  .evidence-table article {
    grid-template-columns: 1fr;
  }
  .evidence-table__topics {
    grid-column: auto;
  }
}
</style>
