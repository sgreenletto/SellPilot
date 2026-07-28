<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  CheckCircle2,
  FileText,
  History,
  RefreshCw,
  Save,
  ShieldAlert,
  Sparkles,
} from "@lucide/vue";
import { FrontendApiError } from "@/api/http";
import {
  cancelContentDraft,
  confirmContentDraft,
  exportContentVersion,
  generateContent,
  listContentVersions,
  regenerateContentField,
  requestContentDraft,
  requestVersionRestore,
} from "@/api/content-generation";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpInput from "@/components/base/SpInput.vue";
import SpSelect from "@/components/base/SpSelect.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type {
  ContentConfirmation,
  ContentGeneration,
  ContentVersion,
} from "@/types/content-generation";

const productId = ref("PROD0001");
const site = ref("sg");
const language = ref("en");
const audience = ref("general");
const sellingPoints = ref("");
const keywords = ref("");
const generation = ref<ContentGeneration | null>(null);
const confirmation = ref<ContentConfirmation | null>(null);
const versions = ref<ContentVersion[]>([]);
const compareIds = ref<string[]>([]);
const loading = ref(false);
const dirty = ref(false);
const error = ref("");
const notice = ref("");
const actionLoading = ref(false);
const regeneratingSection = ref<ContentSection | null>(null);
const siteOptions = [
  { label: "SG", value: "sg" },
  { label: "MY", value: "my" },
  { label: "PH", value: "ph" },
  { label: "TH", value: "th" },
  { label: "VN", value: "vn" },
  { label: "ID", value: "id" },
  { label: "TW", value: "tw" },
  { label: "BR", value: "br" },
];
const languageOptions = ["en", "zh-CN", "zh-TW", "ms", "id", "th", "vi", "tl", "pt-BR"].map(
  (value) => ({ label: value, value }),
);
const content = computed(() => generation.value?.result.content);
const quality = computed(() => generation.value?.result.quality);
const qualityRunLabel = computed(() => {
  const attempts = quality.value?.attempts ?? 1;
  return attempts === 1 ? "已检查 1 次" : `模型已自动修正 ${attempts - 1} 次`;
});
const compared = computed(() =>
  versions.value.filter((item) => compareIds.value.includes(item.id)),
);
type ContentSection = "title" | "bullet_points" | "description" | "marketing_copy" | "faq";
const sectionLabels: Record<ContentSection, string> = {
  title: "商品标题",
  bullet_points: "核心卖点",
  description: "商品详情",
  marketing_copy: "营销短文案",
  faq: "常见问题",
};
const generationRequest = () => ({
  product_id: productId.value.trim(),
  site: site.value,
  target_language: language.value,
  audience: audience.value,
  selling_points: sellingPoints.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean),
  keywords: keywords.value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean),
  max_attempts: 3,
});
const warnUnsaved = (event: BeforeUnloadEvent) => {
  if (!dirty.value) return;
  event.preventDefault();
  event.returnValue = "";
};
onMounted(() => window.addEventListener("beforeunload", warnUnsaved));
onBeforeUnmount(() => window.removeEventListener("beforeunload", warnUnsaved));

async function runGeneration(): Promise<void> {
  const isRegeneration = generation.value !== null;
  loading.value = true;
  error.value = "";
  notice.value = generation.value ? "正在重新生成全部内容，请稍候…" : "正在生成并检查内容，请稍候…";
  try {
    generation.value = await generateContent(generationRequest());
    dirty.value = false;
    confirmation.value = null;
    const actionLabel = isRegeneration ? "全部内容已重新生成" : "内容已生成";
    notice.value = generation.value.result.quality.passed
      ? `${actionLabel}，质量检查通过（循环 ${generation.value.result.quality.attempts}/3）`
      : `${actionLabel}，仍有 ${
          [
            ...generation.value.result.quality.fact_issues,
            ...generation.value.result.quality.compliance_issues,
            ...(generation.value.result.quality.seo_issues ?? []),
            ...(generation.value.result.quality.localization_issues ?? []),
            ...generation.value.result.quality.completeness_issues,
          ].length
        } 项需要调整`;
  } catch (reason) {
    error.value = reason instanceof FrontendApiError ? reason.message : "内容生成失败";
    notice.value = "";
  } finally {
    loading.value = false;
  }
}
async function regenerateSection(section: ContentSection): Promise<void> {
  if (!generation.value || !content.value) return;
  regeneratingSection.value = section;
  error.value = "";
  notice.value = `正在重新生成${sectionLabels[section]}，其他字段会保留…`;
  try {
    const refreshed = await regenerateContentField(generationRequest(), section);
    generation.value.task_id = refreshed.task_id;
    generation.value.invocation_id = refreshed.invocation_id;
    generation.value.provider = refreshed.provider;
    generation.value.model_name = refreshed.model_name;
    generation.value.result.content[section] = refreshed.value as never;
    generation.value.result.quality = refreshed.quality;
    dirty.value = true;
    confirmation.value = null;
    notice.value = `${sectionLabels[section]}已重新生成，保存前将复核全部内容`;
  } catch (reason) {
    error.value = reason instanceof FrontendApiError ? reason.message : "单项重新生成失败";
    notice.value = "";
  } finally {
    regeneratingSection.value = null;
  }
}
async function requestDraft(): Promise<void> {
  if (!generation.value) return;
  actionLoading.value = true;
  error.value = "";
  try {
    confirmation.value = await requestContentDraft(
      generation.value,
      `content-${generation.value.task_id}-${Date.now()}`,
    );
    dirty.value = false;
  } catch (reason) {
    error.value =
      reason instanceof FrontendApiError
        ? reason.message
        : "当前编辑内容未通过服务端事实与质量复核";
  } finally {
    actionLoading.value = false;
  }
}
async function confirmDraft(): Promise<void> {
  if (!confirmation.value) return;
  confirmation.value = await confirmContentDraft(confirmation.value.id);
  const id = confirmation.value.execution_result?.content_id;
  if (id) versions.value = (await listContentVersions(id)).items;
  dirty.value = false;
}
async function cancelDraft(): Promise<void> {
  if (confirmation.value) confirmation.value = await cancelContentDraft(confirmation.value.id);
}
async function restore(version: ContentVersion): Promise<void> {
  confirmation.value = await requestVersionRestore(
    version.content_id,
    version.id,
    `restore-${version.id}-${Date.now()}`,
  );
}
async function exportVersion(version: ContentVersion): Promise<void> {
  try {
    const exported = await exportContentVersion(version.content_id, version.id);
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
    error.value = reason instanceof FrontendApiError ? reason.message : "内容版本导出失败";
  }
}

function confirmationStatusLabel(status: string): string {
  return (
    {
      pending: "等待确认",
      succeeded: "已保存",
      cancelled: "已取消",
      failed: "保存失败",
    }[status] ?? status
  );
}

function formatVersionTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatChangeSummary(value: string): string {
  if (value.includes("aliyun_bailian")) return "AI 多语言内容生成";
  if (value.includes("offline_template")) return "离线模板内容生成";
  if (value.startsWith("Restore version")) return "基于历史版本新建草稿";
  return value;
}

function formatQualityIssue(issue: string): string {
  const mappings: Array<[RegExp, string]> = [
    [/^missing protected fact: (.+)$/, "缺少商品事实：$1"],
    [/^missing requested keyword: (.+)$/, "未覆盖指定关键词：$1"],
    [/^unsupported factual keyword: (.+)$/, "关键词缺少商品事实支持：$1"],
    [/^unsupported claim: (.+)$/, "存在未经商品事实支持的宣称：$1"],
    [/^unsupported technical fact: (.+)$/, "存在未经商品事实支持的技术参数：$1"],
    [/^forbidden claim: (.+)$/, "包含禁用或夸大表述：$1"],
    [/^title exceeds site limit: (.+)$/, "标题超过当前模拟站点限制：$1 个字符"],
    [/^duplicate generated keywords$/, "生成关键词存在重复"],
    [/^title does not contain a requested keyword$/, "标题未自然包含任一指定关键词"],
    [/^title does not contain a target-market keyword$/, "标题未自然包含目标市场关键词"],
    [/^keyword stuffing: (.+)$/, "关键词疑似堆砌：$1"],
    [/^content is not localized to Chinese$/, "正文未有效本地化为中文"],
    [/^content is not localized to Thai$/, "正文未有效本地化为泰语"],
    [/^keyword not localized: (.+)$/, "建议关键词未使用目标语言：$1"],
    [/^missing SKU content: (.+)$/, "缺少 SKU 文案：$1"],
    [/^target language does not match the request$/, "输出语言与目标语言不一致"],
    [/^requested keywords are not fully covered$/, "指定关键词未完全覆盖"],
  ];
  for (const [pattern, replacement] of mappings) {
    if (pattern.test(issue)) return issue.replace(pattern, replacement);
  }
  return issue;
}

function qualitySuggestion(issue: string): string {
  if (issue.startsWith("unsupported factual keyword:")) {
    return "请删除该词，或先在商品资料中补充可核验参数；不要让模型自行推断。";
  }
  if (issue.startsWith("keyword not localized:")) {
    return "这是最终投放关键词；除品牌、型号和 USB-C 等技术标准外，应使用目标市场语言。";
  }
  if (issue.startsWith("missing requested keyword:")) {
    return "确认关键词与商品相关后，可重新生成或在文案中自然补充。";
  }
  if (
    issue === "title does not contain a requested keyword" ||
    issue === "title does not contain a target-market keyword"
  ) {
    return "将一个最重要且相关的关键词自然写入标题。";
  }
  if (issue.startsWith("unsupported claim:") || issue.startsWith("unsupported technical fact:")) {
    return "删除该表述，或先补充能够证明它的商品事实。";
  }
  if (issue.startsWith("missing protected fact:")) {
    return "把这项已核验规格补充到卖点、详情、FAQ 或 SKU 文案中。";
  }
  return "修改对应内容后，再创建草稿；服务端会重新检查。";
}
</script>

<template>
  <PageContainer
    eyebrow="CONTENT WORKSHOP · STRUCTURED OUTPUT"
    title="多语言内容工坊"
    description="基于商品事实生成、检查、编辑、比较并经人工确认保存内容版本。"
  >
    <div v-if="error" class="error" role="alert">
      <ShieldAlert :size="19" />
      <div>
        <strong>生成失败</strong><span>{{ error }}</span>
      </div>
    </div>
    <div v-if="notice" class="notice" role="status" aria-live="polite">
      <RefreshCw v-if="loading || regeneratingSection" :size="17" class="notice-spinner" />
      <CheckCircle2 v-else :size="17" />
      <span>{{ notice }}</span>
    </div>

    <section class="configuration-shell">
      <div class="configuration-main">
        <div class="section-heading">
          <div class="section-icon"><FileText :size="20" /></div>
          <div>
            <h3>生成参数</h3>
            <p>选择商品、市场与内容方向</p>
          </div>
        </div>
        <div class="configuration-grid">
          <SpInput v-model="productId" label="商品 ID" placeholder="例如 PROD0001" />
          <SpSelect v-model="site" label="目标站点" :options="siteOptions" />
          <SpSelect v-model="language" label="目标语言" :options="languageOptions" />
          <SpInput v-model="audience" label="目标受众" placeholder="例如 urban professionals" />
          <SpInput
            v-model="sellingPoints"
            class="field-wide"
            label="核心卖点"
            placeholder="多个卖点用逗号分隔"
          />
          <SpInput
            v-model="keywords"
            class="field-wide"
            label="目标关键词"
            placeholder="多个关键词用逗号分隔"
          />
        </div>
        <div class="configuration-actions">
          <span>生成仅使用已验证商品事实，不会修改商品或库存。</span>
          <SpButton :loading="loading" @click="runGeneration">
            <Sparkles :size="17" />生成并检查
          </SpButton>
        </div>
      </div>
    </section>
    <template v-if="generation && content && quality">
      <section class="status-row result-status">
        <SpBadge :tone="quality.passed ? 'success' : 'danger'">{{
          quality.passed ? "质量检查通过" : "质量检查失败"
        }}</SpBadge>
        <span>{{ qualityRunLabel }}</span>
        <span v-if="dirty" class="dirty-status">内容已修改，保存时将重新检查</span>
      </section>
      <section class="result-layout">
        <div class="editor-surface">
          <div class="editor-header">
            <div>
              <span class="result-kicker">LOCALIZED LISTING</span>
              <h3>商品内容编辑器</h3>
            </div>
            <span class="language-chip">{{ content.target_language }}</span>
          </div>

          <label class="editor-field">
            <span
              ><strong>商品标题</strong>
              <span class="field-tools"
                ><small>{{ content.title.length }}/200</small
                ><button
                  type="button"
                  :disabled="regeneratingSection !== null"
                  @click="regenerateSection('title')"
                >
                  <RefreshCw :size="13" />{{
                    regeneratingSection === "title" ? "生成中…" : "重新生成"
                  }}
                </button></span
              ></span
            >
            <textarea v-model="content.title" rows="2" @input="dirty = true"></textarea>
          </label>
          <label class="editor-field">
            <span
              ><strong>核心卖点</strong>
              <span class="field-tools"
                ><small>每行一条</small
                ><button
                  type="button"
                  :disabled="regeneratingSection !== null"
                  @click="regenerateSection('bullet_points')"
                >
                  <RefreshCw :size="13" />{{
                    regeneratingSection === "bullet_points" ? "生成中…" : "重新生成"
                  }}
                </button></span
              ></span
            >
            <textarea
              :value="content.bullet_points.join('\n')"
              rows="5"
              @input="
                content.bullet_points = ($event.target as HTMLTextAreaElement).value.split('\n');
                dirty = true;
              "
            ></textarea>
          </label>
          <label class="editor-field">
            <span
              ><strong>商品详情</strong>
              <span class="field-tools"
                ><small>支持人工编辑</small
                ><button
                  type="button"
                  :disabled="regeneratingSection !== null"
                  @click="regenerateSection('description')"
                >
                  <RefreshCw :size="13" />{{
                    regeneratingSection === "description" ? "生成中…" : "重新生成"
                  }}
                </button></span
              ></span
            >
            <textarea v-model="content.description" rows="6" @input="dirty = true"></textarea>
          </label>
          <label class="editor-field">
            <span
              ><strong>营销短文案</strong
              ><span class="field-tools"
                ><small>{{ content.marketing_copy.length }}/1000</small
                ><button
                  type="button"
                  :disabled="regeneratingSection !== null"
                  @click="regenerateSection('marketing_copy')"
                >
                  <RefreshCw :size="13" />{{
                    regeneratingSection === "marketing_copy" ? "生成中…" : "重新生成"
                  }}
                </button></span
              ></span
            >
            <textarea v-model="content.marketing_copy" rows="3" @input="dirty = true"></textarea>
          </label>
          <label class="editor-field">
            <span
              ><strong>目标市场关键词</strong
              ><small>跟随目标语言；逗号分隔，保存前检查覆盖与堆砌</small></span
            >
            <textarea
              :value="content.keywords.join('，')"
              rows="2"
              @input="
                content.keywords = ($event.target as HTMLTextAreaElement).value
                  .split(/[,，]/)
                  .map((item) => item.trim())
                  .filter(Boolean);
                dirty = true;
              "
            ></textarea>
          </label>

          <div class="structured-grid">
            <section class="structured-block">
              <div class="structured-heading">
                <strong>常见问题</strong>
                <button
                  type="button"
                  :disabled="regeneratingSection !== null"
                  @click="regenerateSection('faq')"
                >
                  <RefreshCw :size="13" />{{
                    regeneratingSection === "faq" ? "生成中…" : "重新生成"
                  }}
                </button>
              </div>
              <div v-if="content.faq.length" class="faq-list">
                <article v-for="(item, index) in content.faq" :key="index">
                  <header>
                    <b>Q{{ index + 1 }}</b>
                    <span>常见问题 {{ index + 1 }}</span>
                  </header>
                  <div>
                    <label>
                      <span>问题</span>
                      <input v-model="item.question" aria-label="FAQ 问题" @input="dirty = true" />
                    </label>
                    <label>
                      <span>回答</span>
                      <textarea
                        v-model="item.answer"
                        rows="3"
                        aria-label="FAQ 答案"
                        @input="dirty = true"
                      ></textarea>
                    </label>
                  </div>
                </article>
              </div>
              <p v-else class="muted-empty">当前没有生成 FAQ</p>
            </section>
            <section class="structured-block">
              <div class="structured-heading">
                <strong>SKU 文案</strong><span>{{ content.sku_content.length }} 项</span>
              </div>
              <div v-if="content.sku_content.length" class="sku-list">
                <article v-for="(item, index) in content.sku_content" :key="index">
                  <header>
                    <span>SKU {{ index + 1 }}</span>
                    <strong>{{ item.sku || `SKU ${index + 1}` }}</strong>
                  </header>
                  <textarea
                    v-model="item.description"
                    rows="4"
                    aria-label="SKU 文案"
                    @input="dirty = true"
                  ></textarea>
                </article>
              </div>
              <p v-else class="muted-empty">该商品暂无可用 SKU 文案事实</p>
            </section>
          </div>
        </div>

        <aside class="quality-panel">
          <div class="quality-heading">
            <div>
              <span>保存前检查</span>
              <small>自动核对商品事实、合规与字段完整性</small>
            </div>
            <SpBadge :tone="dirty ? 'warning' : quality.passed ? 'success' : 'danger'">
              {{ dirty ? "待复核" : quality.passed ? "已通过" : "有问题" }}
            </SpBadge>
          </div>
          <div class="quality-summary" :class="{ passed: quality.passed }">
            <CheckCircle2 v-if="quality.passed" :size="28" />
            <ShieldAlert v-else :size="28" />
            <div>
              <strong>{{ dirty ? "待复核" : quality.passed ? "检查通过" : "需要调整" }}</strong>
              <span>{{
                dirty
                  ? "点击创建草稿后，系统会先重新检查你修改过的内容"
                  : quality.passed
                    ? "自动检查未发现问题，保存前仍请确认商品参数准确"
                    : "请先处理下方问题，再创建商品草稿"
              }}</span>
            </div>
          </div>
          <div class="check-list">
            <div :class="{ issue: quality.fact_issues.length }">
              <span>事实一致性</span
              ><strong>{{
                quality.fact_issues.length ? `${quality.fact_issues.length} 项` : "通过"
              }}</strong>
            </div>
            <div :class="{ issue: quality.compliance_issues.length }">
              <span>平台合规</span
              ><strong>{{
                quality.compliance_issues.length ? `${quality.compliance_issues.length} 项` : "通过"
              }}</strong>
            </div>
            <div :class="{ issue: quality.seo_issues?.length }">
              <span>站内关键词</span
              ><strong>{{
                quality.seo_issues?.length ? `${quality.seo_issues.length} 项` : "通过"
              }}</strong>
            </div>
            <div :class="{ issue: quality.localization_issues?.length }">
              <span>语言本地化</span
              ><strong>{{
                quality.localization_issues?.length
                  ? `${quality.localization_issues.length} 项`
                  : "通过"
              }}</strong>
            </div>
            <div :class="{ issue: quality.completeness_issues.length }">
              <span>内容完整度</span
              ><strong>{{
                quality.completeness_issues.length
                  ? `${quality.completeness_issues.length} 项`
                  : "通过"
              }}</strong>
            </div>
          </div>
          <div
            v-if="
              quality.fact_issues.length ||
              quality.compliance_issues.length ||
              quality.seo_issues?.length ||
              quality.localization_issues?.length ||
              quality.completeness_issues.length
            "
            class="issue-details"
          >
            <article
              v-for="issue in [
                ...quality.fact_issues,
                ...quality.compliance_issues,
                ...(quality.seo_issues ?? []),
                ...(quality.localization_issues ?? []),
                ...quality.completeness_issues,
              ]"
              :key="issue"
            >
              <strong>{{ formatQualityIssue(issue) }}</strong>
              <span>{{ qualitySuggestion(issue) }}</span>
            </article>
          </div>
          <div class="keyword-notes">
            <section v-if="generation.keywords.length">
              <strong>用户指定词</strong>
              <div class="keyword-chips">
                <span v-for="item in generation.keywords" :key="`request-${item}`">{{ item }}</span>
              </div>
            </section>
            <section v-if="content.keywords.length">
              <strong>目标市场关键词 · {{ content.target_language }}</strong>
              <div class="keyword-chips">
                <span v-for="item in content.keywords" :key="`market-${item}`">{{ item }}</span>
              </div>
            </section>
            <section v-if="content.keyword_suggestions_zh?.length">
              <strong>中文选词建议</strong>
              <div class="keyword-chips suggestion">
                <span v-for="item in content.keyword_suggestions_zh" :key="`zh-${item}`">{{
                  item
                }}</span>
              </div>
            </section>
          </div>
          <div class="result-actions">
            <SpButton :disabled="!quality.passed" :loading="actionLoading" @click="requestDraft">
              <Save :size="17" />{{ dirty ? "复核并创建待确认" : "创建草稿待确认" }}
            </SpButton>
            <SpButton
              variant="secondary"
              :loading="loading"
              :disabled="regeneratingSection !== null"
              @click="runGeneration"
            >
              <RefreshCw :size="16" />{{ loading ? "正在重新生成…" : "重新生成全部内容" }}
            </SpButton>
          </div>
        </aside>
      </section>
      <SpCard v-if="confirmation" class="confirmation">
        <div class="confirmation-copy">
          <div class="confirmation-icon"><Save :size="19" /></div>
          <div>
            <span class="confirmation-kicker">草稿保存确认</span>
            <h3>{{ confirmationStatusLabel(confirmation.status) }}</h3>
            <p>{{ confirmation.risk_warning }}</p>
          </div>
        </div>
        <div v-if="confirmation.status === 'pending'" class="confirmation-actions">
          <SpButton @click="confirmDraft"><Save :size="16" />确认保存新版本</SpButton>
          <SpButton variant="secondary" @click="cancelDraft">暂不保存</SpButton>
        </div>
        <SpBadge v-else :tone="confirmation.status === 'succeeded' ? 'success' : 'warning'">
          {{ confirmationStatusLabel(confirmation.status) }}
        </SpBadge>
      </SpCard>
      <SpCard v-if="versions.length" class="versions-card"
        ><div class="versions-heading">
          <div><History :size="18" /><strong>版本历史</strong></div>
          <span>勾选两个版本可对比；历史版本可复制为新的待确认草稿</span>
        </div>
        <article v-for="version in versions" :key="version.id" class="version">
          <label class="version-selector"
            ><input
              v-model="compareIds"
              type="checkbox"
              :value="version.id"
              :disabled="compareIds.length >= 2 && !compareIds.includes(version.id)"
            /><span>v{{ version.version }}</span></label
          >
          <div class="version-summary">
            <strong>{{ version.title }}</strong>
            <span
              >{{ formatVersionTime(version.created_at) }} ·
              {{ formatChangeSummary(version.change_summary) }}</span
            >
          </div>
          <div class="version-actions">
            <SpButton size="sm" variant="ghost" @click="exportVersion(version)"
              >导出 Markdown</SpButton
            >
            <SpButton size="sm" variant="ghost" @click="restore(version)"
              >以此版本新建草稿</SpButton
            >
          </div>
        </article>
        <div v-if="compared.length === 2" class="comparison">
          <article v-for="version in compared" :key="version.id">
            <header>v{{ version.version }} · {{ version.change_summary }}</header>
            <dl>
              <div>
                <dt>标题</dt>
                <dd>{{ version.title }}</dd>
              </div>
              <div>
                <dt>卖点</dt>
                <dd>{{ version.bullet_points.items.join("；") }}</dd>
              </div>
              <div>
                <dt>详情</dt>
                <dd>{{ version.description }}</dd>
              </div>
              <div>
                <dt>营销文案</dt>
                <dd>{{ version.marketing_copy }}</dd>
              </div>
              <div>
                <dt>FAQ</dt>
                <dd>
                  {{
                    version.faq?.items
                      .map((item) => `${item.question ?? ""}：${item.answer ?? ""}`)
                      .join("\n") || "—"
                  }}
                </dd>
              </div>
              <div>
                <dt>SKU 文案</dt>
                <dd>
                  {{
                    version.sku_content?.items
                      .map((item) => `${item.sku ?? ""}：${item.description ?? ""}`)
                      .join("\n") || "—"
                  }}
                </dd>
              </div>
              <div>
                <dt>关键词</dt>
                <dd>{{ version.keywords?.items.join("、") || "—" }}</dd>
              </div>
              <div>
                <dt>事实检查</dt>
                <dd>{{ JSON.stringify(version.fact_check_result) }}</dd>
              </div>
              <div>
                <dt>合规检查</dt>
                <dd>{{ JSON.stringify(version.compliance_result) }}</dd>
              </div>
            </dl>
          </article>
        </div></SpCard
      >
    </template>
    <SpCard v-else class="empty-workspace">
      <div class="empty-illustration"><Sparkles :size="30" /></div>
      <SpEmptyState
        title="准备创建第一版商品内容"
        description="填写上方参数并点击“生成并检查”，结构化内容将在这里展开。"
      />
    </SpCard>
  </PageContainer>
</template>

<style scoped>
.status-row,
.actions {
  display: flex;
  align-items: center;
  gap: var(--sp-space-4);
  flex-wrap: wrap;
}
.version-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.configuration-shell {
  margin-bottom: var(--sp-space-5);
}
.configuration-main {
  padding: 26px;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-card);
  background: var(--sp-color-surface);
  box-shadow: var(--sp-shadow-card);
}
.section-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
}
.section-heading h3,
.section-heading p {
  margin: 0;
}
.section-heading h3 {
  font-size: 18px;
}
.section-heading p {
  margin-top: 3px;
  color: var(--sp-color-text-muted);
  font-size: 12px;
}
.section-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: var(--sp-color-text-inverse);
  border-radius: 13px;
  background: var(--sp-color-primary);
}
.configuration-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}
.field-wide {
  grid-column: 1 / -1;
}
textarea {
  box-sizing: border-box;
  width: 100%;
  min-height: 46px;
  padding: 11px 14px;
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  outline: none;
  background: var(--sp-color-surface-strong);
  color: var(--sp-color-text);
  transition: 0.18s ease;
}
textarea:focus {
  border-color: var(--sp-color-accent-blue);
  background: var(--sp-color-surface);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--sp-color-accent-blue) 16%, transparent);
}
.configuration-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid var(--sp-border-soft);
}
.configuration-actions > span {
  color: var(--sp-color-text-muted);
  font-size: 12px;
}
.result-status {
  padding: 12px 16px;
  border: 1px solid var(--sp-border-strong);
  border-radius: 16px;
  background: var(--sp-color-surface);
}
.dirty-status {
  color: var(--sp-color-warning);
}
.status-row {
  margin: var(--sp-space-5) 0;
}
.result-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: var(--sp-space-5);
  align-items: stretch;
  height: min(820px, calc(100vh - 150px));
  min-height: 560px;
  overflow: hidden;
}
.editor-surface,
.quality-panel {
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-card);
  background: var(--sp-color-surface);
  box-shadow: var(--sp-shadow-card);
}
.editor-surface {
  padding: 26px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 19px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--sp-border-soft);
}
.editor-header h3,
.editor-header span {
  margin: 0;
}
.editor-header h3 {
  margin-top: 4px;
  font-size: 21px;
}
.result-kicker {
  color: var(--sp-color-info);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.11em;
}
.language-chip {
  padding: 8px 12px;
  color: var(--sp-color-info);
  font-size: 12px;
  font-weight: 800;
  border-radius: 10px;
  background: var(--sp-color-accent-blue-soft);
}
.editor-field {
  display: grid;
  gap: 9px;
  margin-bottom: 18px;
}
.editor-field > span {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.editor-field > span strong {
  color: var(--sp-color-text);
  font-size: 13px;
}
.editor-field > span small {
  color: var(--sp-color-text-muted);
  font-size: 11px;
}
.field-tools {
  display: inline-flex;
  gap: var(--sp-space-3);
  align-items: center;
}
.field-tools button,
.structured-heading button {
  display: inline-flex;
  gap: var(--sp-space-1);
  align-items: center;
  padding: var(--sp-space-1) var(--sp-space-2);
  color: var(--sp-color-info);
  font-size: var(--sp-font-xs);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: var(--sp-radius-control);
}
.field-tools button:hover,
.structured-heading button:hover {
  background: var(--sp-color-accent-blue-soft);
}
.field-tools button:disabled,
.structured-heading button:disabled {
  cursor: wait;
  opacity: 0.55;
}
.editor-field textarea {
  resize: vertical;
  line-height: 1.65;
}
.structured-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 16px;
}
.structured-block {
  min-height: 0;
  padding: 18px;
  border: 1px solid var(--sp-border-strong);
  border-radius: 17px;
  background: var(--sp-color-surface-strong);
}
.structured-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.structured-heading strong {
  font-size: 14px;
}
.structured-heading span {
  color: var(--sp-color-text-muted);
  font-size: 11px;
}
.faq-list,
.sku-list {
  display: grid;
  gap: 10px;
}
.faq-list article {
  display: grid;
  gap: var(--sp-space-3);
  padding: var(--sp-space-3);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-surface);
}
.faq-list article header,
.sku-list article header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.faq-list b {
  display: grid;
  width: 30px;
  height: 26px;
  place-items: center;
  color: var(--sp-color-info);
  font-size: 11px;
  border-radius: 9px;
  background: var(--sp-color-accent-blue-soft);
}
.faq-list header span,
.sku-list header span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.faq-list article > div {
  display: grid;
  gap: var(--sp-space-3);
}
.faq-list label {
  display: grid;
  gap: 6px;
}
.faq-list label > span {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 700;
}
.faq-list input,
.faq-list textarea,
.sku-list textarea {
  width: 100%;
  padding: var(--sp-space-2) var(--sp-space-3);
  color: var(--sp-color-text);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  outline: none;
}
.faq-list input:focus,
.faq-list textarea:focus,
.sku-list textarea:focus {
  border-color: var(--sp-color-accent-blue);
}
.sku-list textarea {
  min-height: 116px;
  line-height: 1.65;
  resize: vertical;
}
.sku-list article {
  display: grid;
  gap: var(--sp-space-3);
  padding: var(--sp-space-3);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-surface);
}
.sku-list strong {
  font-size: 12px;
}
.sku-list span,
.muted-empty {
  color: var(--sp-color-text-muted);
  font-size: 12px;
}
.quality-panel {
  position: relative;
  padding: 20px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
.quality-heading {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: var(--sp-space-4);
  margin-bottom: var(--sp-space-4);
  border-bottom: 1px solid var(--sp-border-soft);
}
.quality-heading > div {
  min-width: 0;
}
.quality-heading :deep(.sp-badge) {
  flex: 0 0 auto;
  white-space: nowrap;
}
.quality-heading span,
.quality-heading small {
  display: block;
}
.quality-heading > div > span {
  color: var(--sp-color-text);
  font-size: var(--sp-font-md);
  font-weight: 750;
}
.quality-heading small {
  margin-top: var(--sp-space-1);
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  line-height: 1.45;
}
.quality-summary {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  padding: var(--sp-space-3);
  color: var(--sp-color-danger);
  border-radius: var(--sp-radius-card-small);
  background: color-mix(in srgb, var(--sp-color-danger) 10%, var(--sp-color-surface));
}
.quality-summary.passed {
  color: var(--sp-color-success);
  background: color-mix(in srgb, var(--sp-color-success) 10%, var(--sp-color-surface));
}
.quality-summary strong,
.quality-summary span {
  display: block;
}
.quality-summary strong {
  font-size: var(--sp-font-sm);
}
.quality-summary span {
  margin-top: var(--sp-space-1);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  line-height: 1.5;
}
.check-list {
  display: grid;
  gap: 8px;
  margin-top: var(--sp-space-4);
}
.check-list > div {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  color: var(--sp-color-text-secondary);
  font-size: 12px;
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-surface-strong);
}
.check-list strong {
  color: var(--sp-color-success);
}
.check-list .issue strong {
  color: var(--sp-color-danger);
}
.issue-details {
  margin-top: var(--sp-space-3);
  padding: var(--sp-space-3);
  color: var(--sp-color-danger);
  font-size: var(--sp-font-xs);
  border: 1px solid color-mix(in srgb, var(--sp-color-danger) 24%, transparent);
  border-radius: var(--sp-radius-control);
  background: color-mix(in srgb, var(--sp-color-danger) 7%, var(--sp-color-surface));
}
.issue-details article,
.issue-details strong,
.issue-details span {
  display: block;
}
.issue-details article {
  margin: 0;
  line-height: 1.5;
}
.issue-details article + article {
  padding-top: var(--sp-space-2);
  margin-top: var(--sp-space-2);
  border-top: 1px solid color-mix(in srgb, var(--sp-color-danger) 16%, transparent);
}
.issue-details span {
  margin-top: 2px;
  color: var(--sp-color-text-secondary);
}
.keyword-notes {
  display: grid;
  gap: var(--sp-space-3);
  margin: var(--sp-space-4) 0 0;
}
.keyword-notes section {
  display: grid;
  gap: 7px;
}
.keyword-notes section > strong {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
}
.keyword-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.keyword-chips span {
  padding: 5px 8px;
  color: var(--sp-color-text-secondary);
  font-size: 11px;
  line-height: 1.2;
  border: 1px solid var(--sp-border-soft);
  border-radius: 999px;
  background: var(--sp-color-surface-strong);
}
.keyword-chips.suggestion span {
  color: var(--sp-color-info);
  border-color: color-mix(in srgb, var(--sp-color-info) 20%, transparent);
  background: var(--sp-color-accent-blue-soft);
}
.result-actions {
  display: grid;
  gap: 9px;
  margin-top: 20px;
}
.result-actions :deep(button) {
  width: 100%;
}
.configuration-actions :deep(.sp-button > span),
.result-actions :deep(.sp-button > span) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  white-space: nowrap;
}
.configuration-actions :deep(.sp-button svg),
.result-actions :deep(.sp-button svg) {
  flex: 0 0 auto;
}
.confirmation {
  margin-top: var(--sp-space-4);
  padding: var(--sp-space-5);
}
.confirmation :deep(.sp-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-5);
}
.confirmation-copy {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-space-3);
}
.confirmation-icon {
  display: grid;
  flex: 0 0 42px;
  height: 42px;
  place-items: center;
  color: var(--sp-color-info);
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-accent-blue-soft);
}
.confirmation-kicker {
  color: var(--sp-color-info);
  font-size: var(--sp-font-xs);
  font-weight: 750;
}
.confirmation h3 {
  margin: 2px 0 var(--sp-space-1);
}
.confirmation p {
  margin: 0;
  color: var(--sp-color-text-secondary);
}
.confirmation-actions {
  display: flex;
  flex: 0 0 auto;
  gap: var(--sp-space-2);
}
.confirmation-actions :deep(.sp-button > span),
.version-actions :deep(.sp-button > span) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  white-space: nowrap;
}
.confirmation-actions :deep(svg),
.version-actions :deep(svg) {
  flex: 0 0 auto;
}
.versions-card {
  margin-top: var(--sp-space-6);
}
.actions {
  justify-content: flex-end;
  margin: var(--sp-space-4) 0;
}
.version {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) auto;
  gap: var(--sp-space-4);
  align-items: center;
  padding: var(--sp-space-4);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-card-small);
  background: var(--sp-color-surface-strong);
}
.version + .version {
  margin-top: var(--sp-space-2);
}
.version-selector {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  font-weight: 750;
}
.version-summary {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.version-summary strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.version-summary span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.versions-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-space-3);
}
.versions-heading > div {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
}
.versions-heading > span {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-space-3);
  overflow: auto;
}
.comparison article {
  min-width: 0;
  padding: var(--sp-space-4);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-card-small);
  background: var(--sp-color-surface-muted);
}
.comparison header {
  margin-bottom: var(--sp-space-3);
  font-weight: 700;
}
.comparison dl,
.comparison dl div {
  display: grid;
  gap: var(--sp-space-2);
}
.comparison dl {
  margin: 0;
}
.comparison dl div {
  grid-template-columns: 72px minmax(0, 1fr);
  padding-top: var(--sp-space-2);
  border-top: 1px solid var(--sp-border-soft);
}
.comparison dt {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
.comparison dd {
  margin: 0;
  overflow-wrap: anywhere;
  line-height: 1.55;
  white-space: pre-wrap;
}
.error {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  max-width: min(420px, calc(100vw - var(--sp-space-8)));
  color: var(--sp-color-danger);
  border: 1px solid color-mix(in srgb, var(--sp-color-danger) 30%, transparent);
  border-radius: 15px;
  background: color-mix(in srgb, var(--sp-color-danger) 8%, var(--sp-color-surface));
  margin: 0 0 var(--sp-space-4) auto;
}
.error strong,
.error span {
  display: block;
}
.error span {
  margin-top: 2px;
  font-size: 13px;
}
.notice {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  padding: var(--sp-space-3) var(--sp-space-4);
  max-width: min(440px, calc(100vw - var(--sp-space-8)));
  color: var(--sp-color-info);
  font-size: var(--sp-font-sm);
  border: 1px solid color-mix(in srgb, var(--sp-color-info) 24%, transparent);
  border-radius: var(--sp-radius-control);
  background: color-mix(in srgb, var(--sp-color-info) 7%, var(--sp-color-surface));
  box-shadow: var(--sp-shadow-card);
  margin: 0 0 var(--sp-space-4) auto;
}
.notice-spinner {
  animation: sp-content-spin 0.85s linear infinite;
}
@keyframes sp-content-spin {
  to {
    transform: rotate(360deg);
  }
}
.empty-workspace {
  min-height: 250px;
  display: grid;
  place-items: center;
  align-content: center;
}
.empty-illustration {
  display: grid;
  width: 68px;
  height: 68px;
  margin-bottom: -20px;
  place-items: center;
  color: var(--sp-color-info);
  border-radius: 22px;
  background: var(--sp-color-accent-blue-soft);
}
@media (max-width: 900px) {
  .configuration-actions {
    align-items: flex-start;
    flex-direction: column;
  }
  .configuration-grid,
  .result-layout,
  .structured-grid,
  .comparison {
    grid-template-columns: 1fr;
  }
  .field-wide {
    grid-column: auto;
  }
  .quality-panel {
    position: static;
  }
  .result-layout {
    height: auto;
    min-height: 0;
    overflow: visible;
  }
  .editor-surface,
  .quality-panel {
    overflow: visible;
  }
  .confirmation :deep(.sp-card__body) {
    align-items: stretch;
    flex-direction: column;
  }
  .confirmation-actions,
  .confirmation-actions :deep(button) {
    width: 100%;
  }
  .version {
    grid-template-columns: 1fr;
  }
}
</style>
