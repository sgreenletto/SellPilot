<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Activity, CheckCircle2, Cpu, FileCode2, RefreshCw, ShieldAlert } from "@lucide/vue";

import { getMemberThreeEvaluation, getModelRuntime, getPromptTemplates } from "@/api/ai-management";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import type {
  MemberThreeEvaluationSummary,
  ModelRuntimeSummary,
  PromptTemplateSummary,
} from "@/types/ai-management";

const loading = ref(false);
const error = ref("");
const prompts = ref<PromptTemplateSummary[]>([]);
const runtime = ref<ModelRuntimeSummary | null>(null);
const evaluation = ref<MemberThreeEvaluationSummary | null>(null);
const passPercent = computed(() =>
  evaluation.value ? Math.round(evaluation.value.pass_rate * 100) : 0,
);

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    [prompts.value, runtime.value, evaluation.value] = await Promise.all([
      getPromptTemplates(),
      getModelRuntime(),
      getMemberThreeEvaluation(),
    ]);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取 AI 管理数据";
  } finally {
    loading.value = false;
  }
};
onMounted(load);
</script>

<template>
  <section class="ai-page">
    <header class="ai-hero">
      <div>
        <p class="eyebrow">AI GOVERNANCE · MEMBER 3</p>
        <h1>Prompt、模型与评估</h1>
        <p>统一查看结构化 Prompt、百炼运行状态、调用指标和可复现评估结果。</p>
      </div>
      <SpButton :loading="loading" @click="load"><RefreshCw :size="17" />刷新数据</SpButton>
    </header>
    <div v-if="error" class="error-panel"><ShieldAlert :size="20" />{{ error }}</div>
    <div class="metric-grid">
      <SpCard>
        <div class="metric-icon"><Cpu :size="22" /></div>
        <strong>{{ runtime?.provider ?? "—" }}</strong>
        <span>运行提供方 · {{ runtime?.model_name ?? "—" }}</span>
        <SpBadge :variant="runtime?.configured ? 'success' : 'warning'">
          {{ runtime?.configured ? "配置有效" : "需要配置" }}
        </SpBadge>
      </SpCard>
      <SpCard>
        <div class="metric-icon"><Activity :size="22" /></div>
        <strong>{{ runtime?.invocation_count ?? 0 }}</strong>
        <span>模型调用 · {{ runtime?.total_tokens ?? 0 }} Tokens</span>
        <small>平均 {{ runtime?.average_duration_ms ?? 0 }} ms</small>
      </SpCard>
      <SpCard>
        <div class="metric-icon"><FileCode2 :size="22" /></div>
        <strong>{{ prompts.length }}</strong
        ><span>Prompt 模板</span>
        <small>{{ prompts.reduce((sum, item) => sum + item.version_count, 0) }} 个版本</small>
      </SpCard>
      <SpCard>
        <div class="metric-icon success"><CheckCircle2 :size="22" /></div>
        <strong>{{ passPercent }}%</strong><span>离线回归通过率</span>
        <small>{{ evaluation?.passed_cases ?? 0 }}/{{ evaluation?.total_cases ?? 0 }} 样例</small>
      </SpCard>
    </div>
    <div class="content-grid">
      <SpCard class="panel">
        <div class="panel-title">
          <div>
            <p class="eyebrow">PROMPT REGISTRY</p>
            <h2>结构化 Prompt 版本</h2>
          </div>
          <SpBadge>只读审计</SpBadge>
        </div>
        <SpEmptyState
          v-if="!loading && !prompts.length"
          title="尚无 Prompt 版本"
          description="运行内容生成后会自动记录模板与版本。"
        />
        <article v-for="prompt in prompts" :key="prompt.id" class="prompt-row">
          <div>
            <strong>{{ prompt.name }}</strong>
            <p>{{ prompt.purpose }}</p>
            <code>{{ prompt.key }}</code>
          </div>
          <div class="prompt-meta">
            <SpBadge variant="success">{{ prompt.status }}</SpBadge>
            <span>v{{ prompt.latest_version?.version ?? "—" }}</span>
            <small>{{ prompt.version_count }} 个版本</small>
          </div>
        </article>
      </SpCard>
      <SpCard class="panel">
        <div class="panel-title">
          <div>
            <p class="eyebrow">EVALUATION</p>
            <h2>评估样例</h2>
          </div>
          <SpBadge>{{ evaluation?.dataset_version ?? "member3-v1" }}</SpBadge>
        </div>
        <article v-for="item in evaluation?.cases ?? []" :key="item.case_id" class="case-row">
          <div :class="['case-state', { pass: item.passed }]">
            {{ item.passed ? "PASS" : "待运行" }}
          </div>
          <div>
            <strong>{{ item.case_id }}</strong>
            <p>{{ item.category }}</p>
            <small v-if="item.failures.length">{{ item.failures.join("；") }}</small>
          </div>
        </article>
        <div v-if="evaluation?.limitations.length" class="limitations">
          <strong>评估边界</strong>
          <p v-for="item in evaluation.limitations" :key="item">{{ item }}</p>
        </div>
      </SpCard>
    </div>
  </section>
</template>

<style scoped>
.ai-page {
  display: grid;
  gap: 24px;
  padding: 8px 0 48px;
}
.ai-hero {
  display: flex;
  justify-content: space-between;
  align-items: end;
  padding: 32px;
  border-radius: 28px;
  color: white;
  background: linear-gradient(125deg, #4c8fdd, #7f88e9);
}
.ai-hero h1 {
  margin: 6px 0 8px;
  font-size: clamp(30px, 4vw, 46px);
}
.ai-hero p {
  margin: 0;
  opacity: 0.86;
}
.eyebrow {
  color: var(--sp-color-primary);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
}
.ai-hero .eyebrow {
  color: #e3efff;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}
.metric-grid :deep(.sp-card) {
  display: grid;
  gap: 8px;
  min-height: 154px;
}
.metric-grid strong {
  font-size: 28px;
}
.metric-grid span,
.metric-grid small {
  color: var(--sp-color-text-secondary);
}
.metric-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: #eaf2ff;
  color: #3478d4;
}
.metric-icon.success {
  color: #22986b;
  background: #e6f7f0;
}
.content-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 18px;
}
.panel {
  min-height: 360px;
}
.panel-title,
.prompt-row,
.case-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.panel-title {
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--sp-color-border-subtle);
}
.panel-title h2 {
  margin: 4px 0 0;
}
.prompt-row,
.case-row {
  align-items: flex-start;
  padding: 18px 0;
  border-bottom: 1px solid var(--sp-color-border-subtle);
}
.prompt-row p,
.case-row p,
.limitations p {
  margin: 5px 0;
  color: var(--sp-color-text-secondary);
}
.prompt-row code {
  color: var(--sp-color-primary);
}
.prompt-meta {
  display: grid;
  justify-items: end;
  gap: 8px;
  white-space: nowrap;
}
.case-row {
  justify-content: flex-start;
}
.case-state {
  min-width: 64px;
  padding: 7px;
  border-radius: 10px;
  text-align: center;
  background: #fff1e4;
  color: #b56a11;
  font-weight: 800;
  font-size: 12px;
}
.case-state.pass {
  background: #e6f7f0;
  color: #17855a;
}
.limitations {
  margin-top: 20px;
  padding: 16px;
  border-radius: 16px;
  background: var(--sp-color-surface-muted);
}
.error-panel {
  display: flex;
  gap: 10px;
  padding: 16px;
  border-radius: 16px;
  color: #d94a64;
  background: #fff0f3;
}
@media (max-width: 1100px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .content-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .ai-hero {
    align-items: flex-start;
    flex-direction: column;
    gap: 18px;
  }
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
