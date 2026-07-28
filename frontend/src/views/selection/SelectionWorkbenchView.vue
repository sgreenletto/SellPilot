<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  AlertTriangle,
  ArrowDownUp,
  Check,
  Download,
  FlaskConical,
  RefreshCw,
  Scale,
  Search,
  SlidersHorizontal,
  Sparkles,
  X,
} from "@lucide/vue";

import {
  compareSelectionProducts,
  createSelectionAnalysis,
  downloadSelectionExport,
  exportSelectionAnalysis,
  listSelectionCandidates,
} from "@/api/selection";
import { FrontendApiError } from "@/api/http";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import SpSkeleton from "@/components/base/SpSkeleton.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type {
  MetricEvidence,
  SelectionAnalysis,
  SelectionAnalysisRequest,
  SelectionCandidate,
  SelectionResult,
  SelectionRiskPreference,
  SelectionSortField,
  SiteCode,
} from "@/types/selection";

const route = useRoute();
const router = useRouter();

const siteOptions = [
  { label: "新加坡 · SGD", value: "sg" },
  { label: "马来西亚 · MYR", value: "my" },
  { label: "菲律宾 · PHP", value: "ph" },
  { label: "泰国 · THB", value: "th" },
  { label: "越南 · VND", value: "vn" },
  { label: "印度尼西亚 · IDR", value: "id" },
];
const riskOptions = [
  { label: "稳健 · 更重利润与履约", value: "conservative" },
  { label: "均衡 · 综合评估", value: "balanced" },
  { label: "增长 · 更重需求与竞争", value: "growth" },
];
const sortOptions = [
  { label: "销量优先", value: "sales_count" },
  { label: "评分优先", value: "rating" },
  { label: "评论数优先", value: "review_count" },
  { label: "价格优先", value: "price" },
];
const categoryCatalog = ref<Record<string, string>>({});

const form = reactive({
  site: queryOption("site", ["sg", "my", "ph", "th", "vn", "id"], "sg") as SiteCode,
  categoryId: queryText("category", "__all__"),
  minPrice: queryText("min_price", ""),
  maxPrice: queryText("max_price", ""),
  costOverride: queryText("cost", ""),
  shippingOverride: queryText("shipping", ""),
  minimumProfit: queryText("profit", "0"),
  minimumMarginPercent: queryText("margin", "0"),
  platformFeePercent: queryText("fee", "0"),
  otherCosts: queryText("other", "0"),
  productWeightKg: queryText("weight", ""),
  riskPreference: queryOption(
    "risk",
    ["conservative", "balanced", "growth"],
    "balanced",
  ) as SelectionRiskPreference,
  sortBy: queryOption(
    "sort",
    ["sales_count", "rating", "review_count", "price", "updated_at"],
    "sales_count",
  ) as SelectionSortField,
});

const candidates = ref<SelectionCandidate[]>([]);
const selectedCandidateIds = ref<string[]>([]);
const analysis = ref<SelectionAnalysis | null>(null);
const selectedResult = ref<SelectionResult | null>(null);
const comparison = ref<SelectionResult[]>([]);
const loadingCandidates = ref(false);
const analyzing = ref(false);
const comparing = ref(false);
const exporting = ref(false);
const message = ref("");
const error = ref("");
const errorCode = ref("");

const fieldErrors = computed(() => {
  const errors: Record<string, string> = {};
  if (invalidNumber(form.minPrice)) errors.minPrice = "请输入有效数字";
  if (invalidNumber(form.maxPrice)) errors.maxPrice = "请输入有效数字";
  if (invalidNumber(form.costOverride)) errors.cost = "请输入有效数字";
  if (invalidNumber(form.shippingOverride)) errors.shipping = "请输入有效数字";
  if (invalidNumber(form.minimumProfit)) errors.minimumProfit = "请输入有效数字";
  if (invalidNumber(form.minimumMarginPercent)) errors.minimumMargin = "请输入有效数字";
  if (invalidNumber(form.platformFeePercent)) errors.platformFee = "请输入有效数字";
  if (invalidNumber(form.otherCosts)) errors.otherCosts = "请输入有效数字";
  if (invalidNumber(form.productWeightKg)) errors.weight = "请输入有效数字";
  const minPrice = optionalNumber(form.minPrice);
  const maxPrice = optionalNumber(form.maxPrice);
  if (minPrice !== undefined && minPrice < 0) errors.minPrice = "最低价格不能小于 0";
  if (maxPrice !== undefined && maxPrice <= 0) errors.maxPrice = "最高价格必须大于 0";
  if (minPrice !== undefined && maxPrice !== undefined && minPrice > maxPrice) {
    errors.maxPrice = "最高价格不能低于最低价格";
  }
  if (
    numberOr(form.minimumMarginPercent, 0) < -100 ||
    numberOr(form.minimumMarginPercent, 0) > 100
  ) {
    errors.minimumMargin = "利润率应在 -100% 到 100% 之间";
  }
  if (numberOr(form.platformFeePercent, 0) < 0 || numberOr(form.platformFeePercent, 0) > 100) {
    errors.platformFee = "平台费率应在 0% 到 100% 之间";
  }
  if (form.productWeightKg && numberOr(form.productWeightKg, 0) <= 0) {
    errors.weight = "重量必须大于 0";
  }
  if (numberOr(form.costOverride, 0) < 0) errors.cost = "产品成本不能小于 0";
  if (numberOr(form.shippingOverride, 0) < 0) errors.shipping = "物流成本不能小于 0";
  if (numberOr(form.otherCosts, 0) < 0) errors.otherCosts = "其他成本不能小于 0";
  return errors;
});

const canAnalyze = computed(
  () =>
    !analyzing.value && candidates.value.length > 0 && Object.keys(fieldErrors.value).length === 0,
);
const compareIds = computed(() =>
  analysis.value
    ? analysis.value.results
        .filter((result) => selectedCandidateIds.value.includes(result.product_id))
        .map((result) => result.product_id)
        .slice(0, 4)
    : [],
);
const backendDisconnected = computed(() => errorCode.value === "NETWORK_ERROR");
const needsAuthentication = computed(() => errorCode.value === "UNAUTHENTICATED");
const categoryOptions = computed(() => [
  { label: "全部类目", value: "__all__" },
  ...Object.entries(categoryCatalog.value)
    .sort(([, left], [, right]) => left.localeCompare(right))
    .map(([value, name]) => ({ label: `${name}（${value}）`, value })),
]);

function queryText(key: string, fallback: string): string {
  const value = route.query[key];
  return typeof value === "string" ? value : fallback;
}

function queryOption(key: string, allowed: string[], fallback: string): string {
  const value = queryText(key, fallback);
  return allowed.includes(value) ? value : fallback;
}

function invalidNumber(value: string): boolean {
  return Boolean(value.trim()) && !Number.isFinite(Number(value));
}

function optionalNumber(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function numberOr(value: string, fallback: number): number {
  return optionalNumber(value) ?? fallback;
}

function clearFeedback(): void {
  error.value = "";
  errorCode.value = "";
  message.value = "";
}

function handleError(reason: unknown): void {
  const apiError =
    reason instanceof FrontendApiError
      ? reason
      : new FrontendApiError({
          code: "UNKNOWN_ERROR",
          message: reason instanceof Error ? reason.message : "操作失败",
          status: 0,
        });
  error.value = apiError.message;
  errorCode.value = apiError.code;
}

function candidateQuery() {
  return {
    site: form.site,
    category_id: form.categoryId === "__all__" ? undefined : form.categoryId,
    min_price: optionalNumber(form.minPrice),
    max_price: optionalNumber(form.maxPrice),
    sort_by: form.sortBy,
    descending: true,
    offset: 0,
    limit: 100,
  };
}

function analysisPayload(): SelectionAnalysisRequest {
  return {
    ...candidateQuery(),
    product_ids: selectedCandidateIds.value.length > 0 ? selectedCandidateIds.value : undefined,
    minimum_profit: numberOr(form.minimumProfit, 0),
    minimum_margin: numberOr(form.minimumMarginPercent, 0) / 100,
    platform_fee_rate: numberOr(form.platformFeePercent, 0) / 100,
    other_costs: numberOr(form.otherCosts, 0),
    cost_override: optionalNumber(form.costOverride),
    shipping_cost_override: optionalNumber(form.shippingOverride),
    product_weight_kg: optionalNumber(form.productWeightKg),
    risk_preference: form.riskPreference,
  };
}

async function loadCandidates(): Promise<void> {
  if (Object.keys(fieldErrors.value).length > 0) return;
  clearFeedback();
  loadingCandidates.value = true;
  analysis.value = null;
  selectedResult.value = null;
  comparison.value = [];
  try {
    candidates.value = await listSelectionCandidates(candidateQuery());
    categoryCatalog.value = candidates.value.reduce<Record<string, string>>(
      (catalog, candidate) => {
        catalog[candidate.category_id] = candidate.category_name;
        return catalog;
      },
      { ...categoryCatalog.value },
    );
    selectedCandidateIds.value = selectedCandidateIds.value.filter((id) =>
      candidates.value.some((candidate) => candidate.product_id === id),
    );
    if (candidates.value.length === 0) message.value = "当前条件下没有候选商品，请调整条件。";
  } catch (reason) {
    candidates.value = [];
    handleError(reason);
  } finally {
    loadingCandidates.value = false;
  }
}

async function runAnalysis(): Promise<void> {
  if (!canAnalyze.value) return;
  clearFeedback();
  analyzing.value = true;
  selectedResult.value = null;
  comparison.value = [];
  try {
    analysis.value = await createSelectionAnalysis(analysisPayload());
    selectedCandidateIds.value = [];
    message.value = `分析完成：${analysis.value.ranked_count} 个入选，${analysis.value.excluded_count} 个因利润条件排除。`;
  } catch (reason) {
    handleError(reason);
  } finally {
    analyzing.value = false;
  }
}

function toggleCandidate(productId: string): void {
  const selected = new Set(selectedCandidateIds.value);
  if (selected.has(productId)) selected.delete(productId);
  else selected.add(productId);
  selectedCandidateIds.value = [...selected];
}

function toggleCompare(productId: string): void {
  const selected = new Set(selectedCandidateIds.value);
  if (selected.has(productId)) selected.delete(productId);
  else if (selected.size < 4) selected.add(productId);
  selectedCandidateIds.value = [...selected];
}

async function compareProducts(): Promise<void> {
  if (!analysis.value || compareIds.value.length < 2) return;
  clearFeedback();
  comparing.value = true;
  try {
    comparison.value = await compareSelectionProducts(analysis.value.task_id, compareIds.value);
  } catch (reason) {
    handleError(reason);
  } finally {
    comparing.value = false;
  }
}

async function exportReport(): Promise<void> {
  if (!analysis.value) return;
  clearFeedback();
  exporting.value = true;
  try {
    const report = await exportSelectionAnalysis(analysis.value.task_id);
    const filename = downloadSelectionExport(report);
    message.value = `Markdown 报告已导出：${filename}`;
  } catch (reason) {
    handleError(reason);
  } finally {
    exporting.value = false;
  }
}

function formatMoney(value: string | undefined, currency: string): string {
  if (value === undefined) return "—";
  return `${currency} ${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
}

function percent(value: string | number): string {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function metricLabel(key: string): string {
  return (
    {
      demand: "需求热度",
      competition: "竞争程度",
      profitability: "利润空间",
      review_quality: "评论质量",
      logistics: "物流风险",
      after_sales: "售后风险",
      factory_fit: "工厂适配",
      total_score: "综合得分",
      profit: "预计利润",
      margin: "利润率",
      data_completeness: "数据完整度",
    }[key] ?? key
  );
}

function localizedExplanation(result: SelectionResult): string {
  const strongest = Object.entries(result.metrics)
    .filter(([, metric]) => metric.score !== null)
    .sort(([, left], [, right]) => Number(right.score) - Number(left.score))[0];
  const strongestText = strongest
    ? `优势最明显的是${metricLabel(strongest[0])}（${Number(strongest[1].score).toFixed(1)} 分）`
    : "目前没有足够的分项数据判断主要优势";
  return `商品机会总分 ${Number(result.total_score).toFixed(1)}，预计利润 ${formatMoney(
    result.profit.profit,
    result.currency,
  )}，利润率 ${percent(result.profit.margin || 0)}；${strongestText}。`;
}

function localizedRisk(risk: string): string {
  const missingMatch = /^missing ([a-z_]+):/.exec(risk);
  if (missingMatch) {
    return `${metricLabel(missingMatch[1] ?? "")}数据缺失，当前评分未计入这一项`;
  }
  const legacyMissingMatch = /^([a-z_]+) data missing$/.exec(risk);
  if (legacyMissingMatch) {
    return `${metricLabel(legacyMissingMatch[1] ?? "")}数据缺失，当前评分未计入这一项`;
  }
  if (risk === "negative profit") return "预计利润为负";
  if (risk === "negative margin") return "预计利润率为负";
  return risk;
}

function cardRisks(result: SelectionResult): string[] {
  return result.risk_warnings.filter(
    (risk) =>
      !risk.startsWith("missing ") &&
      !risk.endsWith(" data missing") &&
      !risk.includes("required source metric is unavailable"),
  );
}

function localizedEvidenceSource(source: string): string {
  if (source.startsWith("deterministic formula"))
    return `确定性评分公式 ${source.split(" ").at(-1)}`;
  if (source === "price minus item, logistics, platform and other costs") {
    return "售价减去商品、物流、平台及其他成本";
  }
  if (source === "profit divided by price") return "利润除以售价";
  if (source === "available scoring dimensions") return "可计算的评分维度";
  return source;
}

function metricScore(metric: MetricEvidence): number {
  return metric.score === null ? 0 : Number(metric.score);
}

function closeDialog(): void {
  selectedResult.value = null;
  comparison.value = [];
}

function handleGlobalKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && (selectedResult.value || comparison.value.length)) {
    closeDialog();
  }
}

function syncQuery(): void {
  void router.replace({
    query: {
      site: form.site,
      category: form.categoryId === "__all__" ? undefined : form.categoryId,
      min_price: form.minPrice || undefined,
      max_price: form.maxPrice || undefined,
      cost: form.costOverride || undefined,
      shipping: form.shippingOverride || undefined,
      profit: form.minimumProfit,
      margin: form.minimumMarginPercent,
      fee: form.platformFeePercent,
      other: form.otherCosts,
      weight: form.productWeightKg || undefined,
      risk: form.riskPreference,
      sort: form.sortBy,
    },
  });
}

watch(form, syncQuery, { deep: true });
onMounted(() => {
  document.addEventListener("keydown", handleGlobalKeydown);
  void loadCandidates();
});
onBeforeUnmount(() => document.removeEventListener("keydown", handleGlobalKeydown));
</script>

<template>
  <PageContainer>
    <header class="page-heading">
      <div class="page-context">
        <SpBadge tone="info" dot>Shopee 模拟实验数据</SpBadge>
        <p>用可追溯的市场数据、利润公式和分项证据筛选候选商品。</p>
      </div>
      <div class="heading-actions">
        <SpButton variant="secondary" :loading="loadingCandidates" @click="loadCandidates">
          <template #icon><RefreshCw :size="16" /></template>
          刷新候选
        </SpButton>
      </div>
    </header>

    <div v-if="error" class="feedback feedback--error" role="alert">
      <AlertTriangle :size="19" />
      <div>
        <strong>{{
          backendDisconnected ? "后端未连接" : needsAuthentication ? "需要登录" : "请求失败"
        }}</strong>
        <p>{{ error }}</p>
      </div>
    </div>
    <p v-if="message" class="feedback feedback--success" role="status">
      <Check :size="18" />{{ message }}
    </p>

    <div class="workbench">
      <aside>
        <SpCard padding="lg">
          <template #header>
            <div class="card-title">
              <span><SlidersHorizontal :size="18" />分析条件</span>
              <SpBadge tone="neutral">URL 已保存</SpBadge>
            </div>
          </template>
          <form class="filters" @submit.prevent="loadCandidates">
            <SpSelect v-model="form.site" label="目标站点" :options="siteOptions" />
            <SpSelect
              v-model="form.categoryId"
              label="商品类目"
              :options="categoryOptions"
              placeholder="请选择类目范围"
            />
            <div class="field-pair">
              <SpInput
                v-model="form.minPrice"
                label="最低价格"
                placeholder="0"
                :error="fieldErrors.minPrice"
              />
              <SpInput
                v-model="form.maxPrice"
                label="最高价格"
                placeholder="不限"
                :error="fieldErrors.maxPrice"
              />
            </div>
            <div class="field-pair">
              <SpInput
                v-model="form.costOverride"
                label="产品成本覆盖（可选）"
                placeholder="使用商品成本"
                :error="fieldErrors.cost"
              />
              <SpInput
                v-model="form.shippingOverride"
                label="物流成本覆盖（可选）"
                placeholder="使用商品运费"
                :error="fieldErrors.shipping"
              />
            </div>
            <p class="field-note">
              留空时使用每个候选商品自身的成本；填写后会用该数值统一重新估算利润。
            </p>
            <div class="field-pair">
              <SpInput
                v-model="form.minimumProfit"
                label="最低利润"
                placeholder="0"
                :error="fieldErrors.minimumProfit"
              />
              <SpInput
                v-model="form.minimumMarginPercent"
                label="最低利润率（%）"
                placeholder="0"
                :error="fieldErrors.minimumMargin"
              />
            </div>
            <div class="field-pair">
              <SpInput
                v-model="form.platformFeePercent"
                label="平台费率（%）"
                placeholder="0"
                :error="fieldErrors.platformFee"
              />
              <SpInput
                v-model="form.otherCosts"
                label="其他单件成本"
                placeholder="0"
                :error="fieldErrors.otherCosts"
              />
            </div>
            <SpInput
              v-model="form.productWeightKg"
              label="商品重量（kg）"
              placeholder="可选，用于记录分析条件"
              :error="fieldErrors.weight"
            />
            <p class="field-note">
              当前模拟数据没有重量运费阶梯；重量会写入任务条件，不伪造评分影响。
            </p>
            <SpSelect v-model="form.riskPreference" label="风险偏好" :options="riskOptions" />
            <SpSelect v-model="form.sortBy" label="候选排序" :options="sortOptions" />
            <SpButton type="submit" variant="secondary" block :loading="loadingCandidates">
              <template #icon><Search :size="16" /></template>
              查询候选
            </SpButton>
            <SpButton block :loading="analyzing" :disabled="!canAnalyze" @click="runAnalysis">
              <template #icon><Sparkles :size="16" /></template>
              {{
                selectedCandidateIds.length
                  ? `分析所选 ${selectedCandidateIds.length} 项`
                  : "分析全部候选"
              }}
            </SpButton>
          </form>
        </SpCard>
      </aside>

      <main class="main-content">
        <SpCard padding="lg">
          <template #header>
            <div class="card-title candidate-heading">
              <span><FlaskConical :size="18" />候选商品</span>
              <span>{{ candidates.length }} 项 · 可选后分析</span>
            </div>
          </template>
          <div v-if="loadingCandidates" class="skeleton-list" aria-label="正在加载候选商品">
            <SpSkeleton v-for="index in 4" :key="index" height="76px" />
          </div>
          <SpEmptyState
            v-else-if="candidates.length === 0"
            title="没有可分析的候选商品"
            description="确认后端已连接并导入 Mock 商品数据，或放宽站点、类目和价格条件。"
          >
            <template #icon><Search :size="24" /></template>
          </SpEmptyState>
          <div v-else class="candidate-grid">
            <label
              v-for="candidate in candidates"
              :key="candidate.product_id"
              :class="[
                'candidate-card',
                { 'candidate-card--selected': selectedCandidateIds.includes(candidate.product_id) },
              ]"
            >
              <input
                type="checkbox"
                :checked="selectedCandidateIds.includes(candidate.product_id)"
                @change="toggleCandidate(candidate.product_id)"
              />
              <span class="candidate-check"><Check :size="14" /></span>
              <span class="candidate-copy">
                <strong>{{ candidate.title }}</strong>
                <small>{{ candidate.category_name }} · {{ candidate.product_id }}</small>
                <span class="candidate-metrics">
                  <span>{{ formatMoney(candidate.price, candidate.currency) }}</span>
                  <span>销量 {{ candidate.sales_count }}</span>
                  <span>评分 {{ candidate.rating }}</span>
                  <span>成本 {{ formatMoney(candidate.cost, candidate.currency) }}</span>
                  <span>物流 {{ formatMoney(candidate.shipping_cost, candidate.currency) }}</span>
                </span>
              </span>
              <SpBadge tone="info">{{ candidate.is_mock_data ? "模拟" : "导入" }}</SpBadge>
            </label>
          </div>
        </SpCard>

        <SpCard v-if="analysis" padding="lg" class="results-card">
          <template #header>
            <div class="results-heading">
              <div>
                <div class="card-title">
                  <span><ArrowDownUp :size="18" />选品结果</span>
                </div>
                <p>
                  评分公式 {{ analysis.formula_version }} ·
                  {{ analysis.generation_mode === "rule_template" ? "规则解释" : "校验生成解释" }}
                </p>
              </div>
              <div class="heading-actions">
                <SpButton
                  variant="secondary"
                  :disabled="compareIds.length < 2"
                  :loading="comparing"
                  @click="compareProducts"
                >
                  <template #icon><Scale :size="16" /></template>
                  对比所选（{{ compareIds.length }}/4）
                </SpButton>
                <SpButton variant="secondary" :loading="exporting" @click="exportReport">
                  <template #icon><Download :size="16" /></template>
                  导出报告
                </SpButton>
              </div>
            </div>
          </template>

          <SpEmptyState
            v-if="analysis.results.length === 0"
            title="没有商品满足利润条件"
            :description="`${analysis.excluded_count} 个候选已被最低利润或利润率条件排除，请调整条件后重新分析。`"
          >
            <template #icon><SlidersHorizontal :size="24" /></template>
          </SpEmptyState>
          <div v-else class="result-list">
            <article v-for="result in analysis.results" :key="result.id" class="result-card">
              <div class="rank" :aria-label="`排名第 ${result.rank}`">#{{ result.rank }}</div>
              <div class="result-main">
                <div class="result-title">
                  <div>
                    <h2>{{ result.title || result.product_id }}</h2>
                    <p>
                      {{ result.product_id }} · 数据完整度 {{ percent(result.data_completeness) }}
                      <SpBadge v-if="result.is_mock_data" tone="info">模拟数据</SpBadge>
                    </p>
                  </div>
                  <strong>{{ Number(result.total_score).toFixed(1) }}<small> / 100</small></strong>
                </div>
                <div class="metric-grid">
                  <div v-for="(metric, key) in result.metrics" :key="key" class="metric">
                    <span
                      ><b>{{ metricLabel(String(key)) }}</b
                      ><em>{{ metric.score ?? "缺失" }}</em></span
                    >
                    <div
                      class="metric-track"
                      :aria-label="`${metricLabel(String(key))} ${metric.score ?? '数据缺失'}`"
                    >
                      <i :style="{ width: `${metricScore(metric)}%` }"></i>
                    </div>
                  </div>
                </div>
                <p class="explanation">{{ localizedExplanation(result) }}</p>
                <div v-if="cardRisks(result).length" class="risk-list">
                  <SpBadge v-for="risk in cardRisks(result)" :key="risk" tone="warning">
                    {{ localizedRisk(risk) }}
                  </SpBadge>
                </div>
                <div class="result-actions">
                  <label class="compare-check">
                    <input
                      type="checkbox"
                      :checked="selectedCandidateIds.includes(result.product_id)"
                      :disabled="
                        !selectedCandidateIds.includes(result.product_id) &&
                        selectedCandidateIds.length >= 4
                      "
                      @change="toggleCompare(result.product_id)"
                    />
                    加入对比
                  </label>
                  <SpButton size="sm" variant="ghost" @click="selectedResult = result"
                    >查看详情</SpButton
                  >
                </div>
              </div>
            </article>
          </div>
        </SpCard>
      </main>
    </div>

    <div
      v-if="selectedResult"
      class="drawer-backdrop"
      role="presentation"
      @click.self="selectedResult = null"
    >
      <aside class="detail-drawer" role="dialog" aria-modal="true" aria-label="选品详情">
        <header>
          <div>
            <p class="eyebrow">选品详情</p>
            <h2>{{ selectedResult.title || selectedResult.product_id }}</h2>
          </div>
          <button
            type="button"
            class="close-button"
            aria-label="关闭详情"
            @click="selectedResult = null"
          >
            <X :size="20" />
          </button>
        </header>
        <section class="detail-summary">
          <div>
            <span>综合得分</span><strong>{{ selectedResult.total_score }}</strong>
          </div>
          <div>
            <span>预计利润</span
            ><strong>{{
              formatMoney(selectedResult.profit.profit, selectedResult.currency)
            }}</strong>
          </div>
          <div>
            <span>利润率</span><strong>{{ percent(selectedResult.profit.margin || 0) }}</strong>
          </div>
          <div>
            <span>完整度</span><strong>{{ percent(selectedResult.data_completeness) }}</strong>
          </div>
        </section>
        <section>
          <h3>推荐解释</h3>
          <p>{{ localizedExplanation(selectedResult) }}</p>
          <dl>
            <template v-for="item in selectedResult.explanation.evidence" :key="item.metric">
              <dt>{{ metricLabel(item.metric) }}</dt>
              <dd>
                <strong>{{ item.value }}</strong
                ><small>{{ localizedEvidenceSource(item.source) }}</small>
              </dd>
            </template>
          </dl>
        </section>
        <section>
          <h3>风险与缺失数据</h3>
          <ul v-if="selectedResult.risk_warnings.length">
            <li v-for="risk in selectedResult.risk_warnings" :key="risk">
              {{ localizedRisk(risk) }}
            </li>
          </ul>
          <p v-else>未发现额外风险提示。</p>
        </section>
      </aside>
    </div>

    <div
      v-if="comparison.length"
      class="drawer-backdrop"
      role="presentation"
      @click.self="comparison = []"
    >
      <section class="compare-dialog" role="dialog" aria-modal="true" aria-label="候选商品对比">
        <header>
          <div>
            <h2>候选商品对比</h2>
          </div>
          <button type="button" class="close-button" aria-label="关闭对比" @click="comparison = []">
            <X :size="20" />
          </button>
        </header>
        <div class="compare-scroll">
          <table>
            <thead>
              <tr>
                <th>指标</th>
                <th v-for="item in comparison" :key="item.id">{{ item.title }}</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th>排名</th>
                <td v-for="item in comparison" :key="item.id">#{{ item.rank }}</td>
              </tr>
              <tr>
                <th>综合得分</th>
                <td v-for="item in comparison" :key="item.id">{{ item.total_score }}</td>
              </tr>
              <tr>
                <th>预计利润</th>
                <td v-for="item in comparison" :key="item.id">
                  {{ formatMoney(item.profit.profit, item.currency) }}
                </td>
              </tr>
              <tr>
                <th>利润率</th>
                <td v-for="item in comparison" :key="item.id">
                  {{ percent(item.profit.margin || 0) }}
                </td>
              </tr>
              <tr v-for="key in Object.keys(comparison[0]?.metrics || {})" :key="key">
                <th>{{ metricLabel(key) }}</th>
                <td v-for="item in comparison" :key="item.id">
                  {{ item.metrics[key]?.score ?? "缺失" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </PageContainer>
</template>

<style scoped>
.page-heading,
.heading-actions,
.card-title,
.results-heading,
.result-title,
.result-actions,
.detail-drawer header,
.compare-dialog header {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: space-between;
}
.page-heading {
  margin-bottom: var(--sp-space-6);
}
.page-context {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  min-width: 0;
}
.page-context p,
.results-heading p,
.result-title p,
.field-note {
  color: var(--sp-color-text-secondary);
}
.eyebrow {
  color: var(--sp-color-accent-blue) !important;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  letter-spacing: 0.1em;
}
.workbench {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: var(--sp-space-5);
  align-items: start;
}
.workbench > aside {
  position: sticky;
  top: var(--sp-space-4);
  max-height: 70dvh;
  padding-right: var(--sp-space-2);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.main-content {
  display: grid;
  gap: var(--sp-space-5);
  max-height: 70dvh;
  min-width: 0;
  padding-right: var(--sp-space-2);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.workbench > aside,
.main-content {
  scrollbar-color: var(--sp-border-strong) transparent;
  scrollbar-width: thin;
}
.filters {
  display: grid;
  gap: var(--sp-space-4);
}
.field-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-space-3);
}
.field-note {
  margin-top: calc(var(--sp-space-3) * -1);
  font-size: var(--sp-font-xs);
}
.card-title > span {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  font-weight: 750;
}
.candidate-heading > span:last-child {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 500;
}
.candidate-grid,
.result-list,
.skeleton-list {
  display: grid;
  gap: var(--sp-space-3);
}
.candidate-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.candidate-card {
  position: relative;
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  min-width: 0;
  padding: var(--sp-space-4);
  cursor: pointer;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-card-small);
  transition:
    border-color var(--sp-transition-fast),
    background var(--sp-transition-fast);
}
.candidate-card:focus-within,
.candidate-card--selected {
  background: var(--sp-color-accent-blue-soft);
  border-color: var(--sp-color-accent-blue);
}
.candidate-card > input {
  position: absolute;
  opacity: 0;
}
.candidate-check {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  width: 22px;
  height: 22px;
  color: transparent;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-space-2);
}
.candidate-card--selected .candidate-check {
  color: var(--sp-color-text-inverse);
  background: var(--sp-color-primary);
}
.candidate-copy {
  display: grid;
  flex: 1;
  gap: var(--sp-space-1);
  min-width: 0;
}
.candidate-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candidate-copy small {
  color: var(--sp-color-text-muted);
}
.candidate-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-3);
  margin-top: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}
.results-card {
  margin-bottom: var(--sp-space-8);
}
.result-card {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: var(--sp-space-4);
  padding: var(--sp-space-5);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-card-small);
}
.rank {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  color: var(--sp-color-primary);
  font-weight: 800;
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-card-small);
}
.result-main {
  min-width: 0;
}
.result-title h2 {
  margin: 0;
  font-size: var(--sp-font-md);
}
.result-title > strong {
  color: var(--sp-color-primary);
  font-size: var(--sp-font-xl);
}
.result-title > strong small {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--sp-space-3) var(--sp-space-5);
  margin: var(--sp-space-5) 0;
}
.metric {
  display: grid;
  gap: var(--sp-space-2);
}
.metric > span {
  display: flex;
  justify-content: space-between;
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}
.metric em {
  color: var(--sp-color-text);
  font-style: normal;
  font-weight: 700;
}
.metric-track {
  height: 7px;
  overflow: hidden;
  background: var(--sp-color-bg-deep);
  border-radius: var(--sp-radius-pill);
}
.metric-track i {
  display: block;
  height: 100%;
  background: var(--sp-color-accent-blue);
  border-radius: inherit;
}
.explanation {
  padding: var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface-strong);
  border-left: 3px solid var(--sp-color-accent-purple);
  border-radius: var(--sp-radius-control);
}
.risk-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
}
.result-actions {
  margin-top: var(--sp-space-4);
}
.compare-check {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  color: var(--sp-color-text-secondary);
  cursor: pointer;
}
.feedback {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  padding: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
  border-radius: var(--sp-radius-control);
}
.feedback p {
  margin: var(--sp-space-1) 0 0;
}
.feedback--error {
  color: var(--sp-color-danger);
  background: var(--sp-color-accent-pink-soft);
}
.feedback--success {
  color: var(--sp-color-success);
  background: color-mix(in srgb, var(--sp-color-success) 12%, var(--sp-color-surface-strong));
}
.drawer-backdrop {
  position: fixed;
  z-index: 40;
  inset: 0;
  display: flex;
  justify-content: flex-end;
  padding: var(--sp-space-4);
  background: var(--sp-color-overlay);
  backdrop-filter: blur(5px);
}
.detail-drawer,
.compare-dialog {
  width: min(620px, 100%);
  height: 100%;
  padding: var(--sp-space-6);
  overflow-y: auto;
  background: var(--sp-color-surface-strong);
  border-radius: var(--sp-radius-card);
  box-shadow: var(--sp-shadow-shell);
}
.detail-drawer h2,
.compare-dialog h2 {
  margin: var(--sp-space-1) 0;
}
.close-button {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  color: var(--sp-color-text-secondary);
  cursor: pointer;
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-pill);
}
.detail-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--sp-space-3);
  margin: var(--sp-space-6) 0;
}
.detail-summary div {
  display: grid;
  gap: var(--sp-space-2);
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-card-small);
}
.detail-summary span,
.detail-drawer small {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.detail-drawer section + section {
  margin-top: var(--sp-space-6);
}
.detail-drawer dl {
  display: grid;
  grid-template-columns: minmax(100px, 160px) 1fr;
  margin: 0;
}
.detail-drawer dt,
.detail-drawer dd {
  padding: var(--sp-space-3);
  margin: 0;
  border-bottom: 1px solid var(--sp-border-soft);
}
.detail-drawer dd {
  display: grid;
}
.compare-dialog {
  width: min(1000px, 100%);
  height: auto;
  max-height: 90vh;
  margin: auto;
}
.compare-scroll {
  margin-top: var(--sp-space-5);
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  min-width: 140px;
  padding: var(--sp-space-3);
  text-align: left;
  border-bottom: 1px solid var(--sp-border-soft);
}
th {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
@media (max-width: 1100px) {
  .workbench {
    grid-template-columns: 1fr;
  }
  .workbench > aside {
    position: static;
  }
  .workbench > aside,
  .main-content {
    max-height: none;
    padding-right: 0;
    overflow-y: visible;
    overscroll-behavior: auto;
    scrollbar-gutter: auto;
  }
}
@media (max-width: 767px) {
  .page-heading,
  .results-heading,
  .result-title {
    align-items: stretch;
    flex-direction: column;
  }
  .page-context {
    align-items: flex-start;
    flex-direction: column;
  }
  .heading-actions {
    flex-wrap: wrap;
  }
  .heading-actions > * {
    flex: 1 1 auto;
  }
  .candidate-grid,
  .field-pair,
  .metric-grid {
    grid-template-columns: 1fr;
  }
  .result-card {
    grid-template-columns: 1fr;
  }
  .detail-summary {
    grid-template-columns: 1fr 1fr;
  }
  .drawer-backdrop {
    padding: 0;
  }
  .detail-drawer,
  .compare-dialog {
    border-radius: 0;
  }
}
</style>
