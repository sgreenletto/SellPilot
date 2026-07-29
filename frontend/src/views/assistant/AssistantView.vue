<script setup lang="ts">
import { ArrowRight, Bot, CornerDownRight, RefreshCw, ShieldCheck, Sparkles } from "@lucide/vue";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  listAssistantCapabilities,
  planAssistantMessage,
  type AssistantAvailability,
  type AssistantCapability,
  type AssistantPlan,
} from "@/api/assistant";
import { FrontendApiError } from "@/api/http";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import PageContainer from "@/components/layout/PageContainer.vue";

const router = useRouter();
const message = ref("");
const capabilities = ref<AssistantCapability[]>([]);
const plan = ref<AssistantPlan | null>(null);
const loadingCapabilities = ref(false);
const planning = ref(false);
const errorMessage = ref("");

const availabilityLabels: Record<AssistantAvailability, string> = {
  available: "可规划",
  contract_only: "仅契约",
  unavailable: "暂不可用",
};

const availabilityTones: Record<AssistantAvailability, "success" | "warning" | "danger"> = {
  available: "success",
  contract_only: "warning",
  unavailable: "danger",
};

const parameterEntries = computed(() => Object.entries(plan.value?.extracted_parameters ?? {}));

async function loadCapabilities() {
  loadingCapabilities.value = true;
  errorMessage.value = "";
  try {
    capabilities.value = await listAssistantCapabilities();
  } catch (error: unknown) {
    errorMessage.value = safeError(error, "能力目录加载失败");
  } finally {
    loadingCapabilities.value = false;
  }
}

async function createPlan() {
  const normalized = message.value.trim();
  if (!normalized || planning.value) {
    return;
  }
  planning.value = true;
  errorMessage.value = "";
  plan.value = null;
  try {
    plan.value = await planAssistantMessage(normalized);
  } catch (error: unknown) {
    errorMessage.value = safeError(error, "计划生成失败");
  } finally {
    planning.value = false;
  }
}

function useCapability(capability: AssistantCapability) {
  message.value = capability.example_message;
}

async function openBusinessPage(path: string | null) {
  if (path) {
    await router.push(path);
  }
}

function safeError(error: unknown, fallback: string): string {
  if (error instanceof FrontendApiError) {
    if (error.status === 422) {
      return "输入参数不符合计划契约，请检查后重试";
    }
    return error.message;
  }
  return error instanceof Error ? error.message : fallback;
}

function displayValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value);
}

onMounted(loadCapabilities);
</script>

<template>
  <PageContainer>
    <div class="assistant-page">
      <header class="assistant-hero">
        <div>
          <span class="assistant-hero__eyebrow"><Bot :size="15" /> Assistant Foundation</span>
          <h1>AI 运营助手 · 计划模式</h1>
          <p>识别运营意图、检查必要参数并生成受控执行计划，不会在本阶段自动运行任务。</p>
        </div>
        <SpBadge tone="info" dot>Mock 模式</SpBadge>
      </header>

      <div class="mock-notice">
        <ShieldCheck :size="18" />
        <span>计划来自服务端能力目录；不会调用真实 LLM、执行工具或连接真实 Shopee。</span>
      </div>

      <SpCard padding="lg">
        <template #header>
          <div class="section-heading">
            <div>
              <h2>描述你的运营任务</h2>
              <p>不能通过文本指定内部工具；助手只会匹配已冻结的受控能力。</p>
            </div>
            <SpButton
              variant="ghost"
              size="sm"
              :loading="loadingCapabilities"
              @click="loadCapabilities"
            >
              <template #icon><RefreshCw :size="15" /></template>
              刷新能力
            </SpButton>
          </div>
        </template>

        <label class="assistant-composer">
          <span>自然语言输入</span>
          <textarea
            v-model="message"
            data-testid="assistant-message"
            maxlength="2000"
            placeholder="例如：查询订单 ORD000001 的物流"
            @keydown.ctrl.enter.prevent="createPlan"
            @keydown.meta.enter.prevent="createPlan"
          ></textarea>
        </label>
        <div class="composer-footer">
          <span>{{ message.length }} / 2000 · Ctrl/⌘ + Enter 提交</span>
          <SpButton :loading="planning" :disabled="!message.trim()" @click="createPlan">
            <template #icon><Sparkles :size="16" /></template>
            生成计划
          </SpButton>
        </div>

        <p v-if="errorMessage" class="error-state" role="alert">{{ errorMessage }}</p>
      </SpCard>

      <SpCard>
        <template #header>
          <div class="section-heading">
            <div>
              <h2>常用任务</h2>
              <p>入口、可用性和示例均由后端 Capability Registry 返回。</p>
            </div>
            <span>{{ capabilities.length }} 项能力</span>
          </div>
        </template>

        <div v-if="loadingCapabilities" class="capability-loading">正在加载能力目录…</div>
        <div v-else-if="capabilities.length" class="capability-grid">
          <button
            v-for="capability in capabilities"
            :key="capability.capability_key"
            type="button"
            class="capability-card"
            @click="useCapability(capability)"
          >
            <span class="capability-card__top">
              <strong>{{ capability.display_name }}</strong>
              <SpBadge :tone="availabilityTones[capability.availability]">
                {{ availabilityLabels[capability.availability] }}
              </SpBadge>
            </span>
            <span>{{ capability.example_message }}</span>
            <small v-if="capability.unavailable_reason">{{ capability.unavailable_reason }}</small>
          </button>
        </div>
        <p v-else class="empty-state">暂未取得 Assistant 能力目录。</p>
      </SpCard>

      <SpCard v-if="plan" data-testid="assistant-plan" padding="lg">
        <template #header>
          <div class="section-heading">
            <div>
              <span class="assistant-hero__eyebrow"><CornerDownRight :size="14" /> Plan</span>
              <h2>确定性执行计划</h2>
            </div>
            <SpBadge :tone="availabilityTones[plan.availability]">
              {{ availabilityLabels[plan.availability] }}
            </SpBadge>
          </div>
        </template>

        <div class="plan-summary">
          <div>
            <span>识别意图</span>
            <strong>{{ plan.detected_intent }}</strong>
          </div>
          <div>
            <span>选中能力</span>
            <strong>{{ plan.selected_capability || "未匹配" }}</strong>
          </div>
          <div>
            <span>Workflow</span>
            <strong>
              {{
                plan.selected_workflow
                  ? `${plan.selected_workflow.name}@${plan.selected_workflow.version}`
                  : "无"
              }}
            </strong>
          </div>
          <div>
            <span>可执行性</span>
            <strong>{{ plan.can_execute ? "参数完整" : "当前不可执行" }}</strong>
          </div>
        </div>

        <div class="plan-columns">
          <section>
            <h3>提取参数</h3>
            <dl v-if="parameterEntries.length" class="parameter-list">
              <div v-for="[key, value] in parameterEntries" :key="key">
                <dt>{{ key }}</dt>
                <dd>{{ displayValue(value) }}</dd>
              </div>
            </dl>
            <p v-else class="empty-state">没有提取到参数。</p>
          </section>
          <section>
            <h3>缺失参数</h3>
            <div v-if="plan.missing_parameters.length" class="chip-row">
              <SpBadge v-for="parameter in plan.missing_parameters" :key="parameter" tone="warning">
                {{ parameter }}
              </SpBadge>
            </div>
            <p v-else class="success-copy">必要参数已满足。</p>
          </section>
        </div>

        <section class="plan-section">
          <h3>计划步骤与 Tool</h3>
          <ol v-if="plan.steps.length" class="plan-steps">
            <li v-for="step in plan.steps" :key="`${step.order}-${step.name}`">
              <span>{{ step.order }}</span>
              <div>
                <strong>{{ step.name }}</strong>
                <small>{{ step.kind }} · {{ step.summary }}</small>
              </div>
            </li>
          </ol>
          <p v-else class="empty-state">未生成工具步骤，不会调用 Tool。</p>
        </section>

        <section class="risk-panel">
          <div>
            <h3>风险与确认</h3>
            <p>{{ plan.risk_summary }}</p>
            <small>{{ plan.mock_notice }}</small>
          </div>
          <SpBadge :tone="plan.requires_confirmation ? 'warning' : 'success'">
            {{ plan.requires_confirmation ? "需要确认" : "只读计划" }}
          </SpBadge>
        </section>

        <p v-if="plan.unavailable_reason" class="unavailable-state">
          {{ plan.unavailable_reason }}
        </p>

        <div class="plan-footer">
          <p v-if="plan.can_execute">能力契约已就绪；下一阶段将接入统一 Task 执行。</p>
          <p v-else>当前不会创建 Task，也不会自动运行 contract_only 或 unavailable 能力。</p>
          <SpButton
            v-if="plan.target_path"
            variant="secondary"
            @click="openBusinessPage(plan.target_path)"
          >
            前往对应业务页面
            <template #icon><ArrowRight :size="15" /></template>
          </SpButton>
        </div>
      </SpCard>
    </div>
  </PageContainer>
</template>

<style scoped>
.assistant-page {
  display: grid;
  gap: var(--sp-space-6);
}

.assistant-hero,
.section-heading,
.composer-footer,
.capability-card__top,
.risk-panel,
.plan-footer {
  display: flex;
  gap: var(--sp-space-4);
  align-items: center;
  justify-content: space-between;
}

.assistant-hero h1,
.section-heading h2,
.plan-section h3,
.plan-columns h3,
.risk-panel h3 {
  margin: 0;
}

.assistant-hero p,
.section-heading p,
.risk-panel p,
.plan-footer p {
  margin: var(--sp-space-2) 0 0;
  color: var(--sp-color-text-secondary);
}

.assistant-hero__eyebrow {
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  color: var(--sp-color-primary);
  font-size: var(--sp-font-xs);
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.mock-notice,
.risk-panel {
  padding: var(--sp-space-4) var(--sp-space-5);
  color: var(--sp-color-info);
  background: var(--sp-color-accent-blue-soft);
  border: 1px solid color-mix(in srgb, var(--sp-color-info) 18%, transparent);
  border-radius: var(--sp-radius-control);
}

.mock-notice {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
}

.assistant-composer {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}

.assistant-composer textarea {
  min-height: 124px;
  padding: var(--sp-space-4);
  color: var(--sp-color-text);
  resize: vertical;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  outline: none;
}

.assistant-composer textarea:focus {
  background: var(--sp-color-surface-strong);
  border-color: var(--sp-color-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-color-accent-blue) 18%, transparent);
}

.composer-footer {
  margin-top: var(--sp-space-4);
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-space-3);
}

.capability-card {
  display: grid;
  gap: var(--sp-space-3);
  padding: var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  text-align: left;
  cursor: pointer;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-control);
  transition:
    border-color var(--sp-transition-fast),
    transform var(--sp-transition-fast);
}

.capability-card:hover {
  border-color: var(--sp-border-strong);
  transform: translateY(-1px);
}

.capability-card strong {
  color: var(--sp-color-text);
}

.capability-card small {
  line-height: 1.5;
  color: var(--sp-color-text-muted);
}

.plan-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-space-3);
}

.plan-summary > div {
  display: grid;
  gap: var(--sp-space-2);
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-control);
}

.plan-summary span,
.parameter-list dt {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.plan-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-space-5);
  margin-top: var(--sp-space-6);
}

.parameter-list {
  display: grid;
  gap: var(--sp-space-2);
}

.parameter-list > div {
  display: grid;
  grid-template-columns: minmax(100px, 0.35fr) 1fr;
  gap: var(--sp-space-3);
}

.parameter-list dd {
  margin: 0;
  overflow-wrap: anywhere;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
}

.plan-section {
  margin-top: var(--sp-space-6);
}

.plan-steps {
  display: grid;
  gap: var(--sp-space-3);
  padding: 0;
  list-style: none;
}

.plan-steps li {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
}

.plan-steps li > span {
  display: grid;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  color: var(--sp-color-primary);
  font-weight: 800;
  place-items: center;
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-pill);
}

.plan-steps div {
  display: grid;
  gap: var(--sp-space-1);
}

.plan-steps small {
  color: var(--sp-color-text-secondary);
}

.risk-panel {
  margin-top: var(--sp-space-6);
}

.risk-panel small {
  color: var(--sp-color-text-secondary);
}

.plan-footer {
  margin-top: var(--sp-space-5);
}

.error-state,
.unavailable-state {
  padding: var(--sp-space-3) var(--sp-space-4);
  color: var(--sp-color-danger);
  background: var(--sp-color-accent-pink-soft);
  border-radius: var(--sp-radius-control);
}

.success-copy {
  color: var(--sp-color-success);
}

.empty-state,
.capability-loading {
  color: var(--sp-color-text-muted);
}

@media (max-width: 1023px) {
  .capability-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .plan-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .assistant-hero,
  .section-heading,
  .composer-footer,
  .risk-panel,
  .plan-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .capability-grid,
  .plan-summary,
  .plan-columns {
    grid-template-columns: 1fr;
  }
}
</style>
