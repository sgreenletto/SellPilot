<script setup lang="ts">
import { computed, ref } from "vue";
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
  generateContent,
  listContentVersions,
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

async function runGeneration(): Promise<void> {
  const isRegeneration = generation.value !== null;
  loading.value = true;
  error.value = "";
  notice.value = generation.value ? "正在重新生成全部内容，请稍候…" : "正在生成并检查内容，请稍候…";
  try {
    generation.value = await generateContent({
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
    dirty.value = false;
    confirmation.value = null;
    const actionLabel = isRegeneration ? "全部内容已重新生成" : "内容已生成";
    notice.value = generation.value.result.quality.passed
      ? `${actionLabel}，质量检查通过（循环 ${generation.value.result.quality.attempts}/3）`
      : `${actionLabel}，仍有 ${
          [
            ...generation.value.result.quality.fact_issues,
            ...generation.value.result.quality.compliance_issues,
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
    const refreshed = await generateContent({
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
    generation.value.task_id = refreshed.task_id;
    generation.value.invocation_id = refreshed.invocation_id;
    generation.value.provider = refreshed.provider;
    generation.value.model_name = refreshed.model_name;
    generation.value.audience = refreshed.audience;
    generation.value.selling_points = refreshed.selling_points;
    generation.value.keywords = refreshed.keywords;
    generation.value.result.content[section] = refreshed.result.content[section] as never;
    generation.value.result.quality = refreshed.result.quality;
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

function formatQualityIssue(issue: string): string {
  const mappings: Array<[RegExp, string]> = [
    [/^missing protected fact: (.+)$/, "缺少商品事实：$1"],
    [/^missing requested keyword: (.+)$/, "未覆盖指定关键词：$1"],
    [/^unsupported claim: (.+)$/, "存在未经商品事实支持的宣称：$1"],
    [/^unsupported technical fact: (.+)$/, "存在未经商品事实支持的技术参数：$1"],
    [/^forbidden claim: (.+)$/, "包含禁用或夸大表述：$1"],
    [/^missing SKU content: (.+)$/, "缺少 SKU 文案：$1"],
    [/^target language does not match the request$/, "输出语言与目标语言不一致"],
    [/^requested keywords are not fully covered$/, "指定关键词未完全覆盖"],
  ];
  for (const [pattern, replacement] of mappings) {
    if (pattern.test(issue)) return issue.replace(pattern, replacement);
  }
  return issue;
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
        <SpBadge tone="info">{{ content.generation_mode }}</SpBadge>
        <span>循环 {{ quality.attempts }}/3</span><span v-if="dirty">人工编辑待服务端复核</span>
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
                  <b>Q{{ index + 1 }}</b>
                  <div>
                    <input v-model="item.question" aria-label="FAQ 问题" @input="dirty = true" />
                    <textarea
                      v-model="item.answer"
                      rows="2"
                      aria-label="FAQ 答案"
                      @input="dirty = true"
                    ></textarea>
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
                  <strong>{{ item.sku || `SKU ${index + 1}` }}</strong>
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
              quality.completeness_issues.length
            "
            class="issue-details"
          >
            <p v-for="issue in quality.fact_issues" :key="`fact-${issue}`">
              {{ formatQualityIssue(issue) }}
            </p>
            <p v-for="issue in quality.compliance_issues" :key="`compliance-${issue}`">
              {{ formatQualityIssue(issue) }}
            </p>
            <p v-for="issue in quality.completeness_issues" :key="`complete-${issue}`">
              {{ formatQualityIssue(issue) }}
            </p>
          </div>
          <div class="keyword-notes">
            <p v-if="generation.keywords.length">
              指定关键词：{{ generation.keywords.join("、") }}
            </p>
            <p v-if="content.keywords.length">生成建议词：{{ content.keywords.join("、") }}</p>
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
      <SpCard v-if="confirmation" class="confirmation"
        ><h3>确认任务：{{ confirmation.status }}</h3>
        <p>{{ confirmation.risk_warning }}</p>
        <SpButton v-if="confirmation.status === 'pending'" @click="confirmDraft"
          >确认保存版本</SpButton
        ><SpButton v-if="confirmation.status === 'pending'" variant="secondary" @click="cancelDraft"
          >取消</SpButton
        ></SpCard
      >
      <SpCard v-if="versions.length" class="versions-card"
        ><div class="versions-heading">
          <div><History :size="18" /><strong>版本历史</strong></div>
          <span>勾选两个版本查看字段差异</span>
        </div>
        <article v-for="version in versions" :key="version.id" class="version">
          <label
            ><input
              v-model="compareIds"
              type="checkbox"
              :value="version.id"
              :disabled="compareIds.length >= 2 && !compareIds.includes(version.id)"
            />v{{ version.version }}</label
          ><span>{{ version.title }}</span
          ><SpButton size="sm" variant="ghost" @click="restore(version)">恢复为新版本</SpButton>
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
.actions,
.confirmation,
.version {
  display: flex;
  align-items: center;
  gap: var(--sp-space-4);
  flex-wrap: wrap;
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
  padding: 14px 18px;
  border: 1px solid var(--sp-border-strong);
  border-radius: 16px;
  background: var(--sp-color-surface);
}
.status-row {
  margin: var(--sp-space-5) 0;
}
.result-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: var(--sp-space-5);
  align-items: start;
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
  min-height: 150px;
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
  display: flex;
  gap: 10px;
}
.faq-list b {
  display: grid;
  flex: 0 0 30px;
  height: 30px;
  place-items: center;
  color: var(--sp-color-info);
  font-size: 11px;
  border-radius: 9px;
  background: var(--sp-color-accent-blue-soft);
}
.faq-list article > div {
  display: grid;
  flex: 1;
  gap: var(--sp-space-2);
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
  min-height: 104px;
  line-height: 1.65;
  resize: vertical;
}
.sku-list article {
  display: grid;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 11px;
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
  position: sticky;
  top: 18px;
  padding: 22px;
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
  padding: var(--sp-space-3);
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
.issue-details p {
  margin: 0;
  line-height: 1.5;
}
.issue-details p + p {
  margin-top: var(--sp-space-1);
}
.keyword-notes {
  margin: var(--sp-space-3) 0 0;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  line-height: 1.5;
}
.keyword-notes p {
  margin: 0;
}
.keyword-notes p + p {
  margin-top: var(--sp-space-1);
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
}
.actions {
  justify-content: flex-end;
  margin: var(--sp-space-4) 0;
}
.version {
  justify-content: space-between;
  border-bottom: 1px solid var(--sp-color-border);
  padding: var(--sp-space-3);
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
  position: fixed;
  top: var(--sp-space-8);
  right: var(--sp-space-8);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  max-width: min(420px, calc(100vw - var(--sp-space-8)));
  color: var(--sp-color-danger);
  border: 1px solid color-mix(in srgb, var(--sp-color-danger) 30%, transparent);
  border-radius: 15px;
  background: color-mix(in srgb, var(--sp-color-danger) 8%, var(--sp-color-surface));
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
  position: fixed;
  right: var(--sp-space-8);
  bottom: var(--sp-space-8);
  z-index: 1000;
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
}
</style>
