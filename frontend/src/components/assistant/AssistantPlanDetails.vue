<script setup lang="ts">
import { computed } from "vue";

import type { AssistantPlan, AssistantTaskResult } from "@/api/assistant";
import type { TaskToolCall } from "@/api/tasks";
import SpBadge from "@/components/base/SpBadge.vue";
import type { TaskStepDetail } from "@/types/contracts";
import {
  availabilityLabels,
  capabilityLabel,
  displayParameterValue,
  intentLabel,
  parameterLabel,
  planRiskLabel,
  stepLabel,
  stepSummary,
  statusLabel,
  taskStatusLabels,
  workflowLabel,
} from "@/utils/assistantPresentation";

interface Props {
  plan: AssistantPlan;
  task?: AssistantTaskResult | null;
  taskSteps?: TaskStepDetail[];
  toolCalls?: TaskToolCall[];
}

const props = withDefaults(defineProps<Props>(), {
  task: null,
  taskSteps: () => [],
  toolCalls: () => [],
});

const parameters = computed(() => Object.entries(props.plan.extracted_parameters));
</script>

<template>
  <details class="assistant-plan-details" data-testid="assistant-plan-details">
    <summary>查看执行计划</summary>
    <div class="assistant-plan-details__body">
      <dl class="assistant-plan-details__summary">
        <div>
          <dt>识别意图</dt>
          <dd>
            {{ intentLabel(plan.detected_intent) }}
            <code>{{ plan.detected_intent }}</code>
          </dd>
        </div>
        <div>
          <dt>选中能力</dt>
          <dd>
            {{ capabilityLabel(plan.selected_capability) }}
            <code v-if="plan.selected_capability">{{ plan.selected_capability }}</code>
          </dd>
        </div>
        <div>
          <dt>工作流</dt>
          <dd>
            {{ workflowLabel(plan.selected_workflow?.name) }}
            <code v-if="plan.selected_workflow">
              {{ plan.selected_workflow.name }}@{{ plan.selected_workflow.version }}
            </code>
          </dd>
        </div>
        <div>
          <dt>执行状态</dt>
          <dd>
            <SpBadge
              :tone="
                task?.task_status === 'failed'
                  ? 'danger'
                  : task?.task_status === 'succeeded'
                    ? 'success'
                    : 'neutral'
              "
            >
              {{
                task ? taskStatusLabels[task.task_status] : availabilityLabels[plan.availability]
              }}
            </SpBadge>
          </dd>
        </div>
        <div>
          <dt>风险与确认</dt>
          <dd>
            {{ planRiskLabel(plan) }} · {{ plan.requires_confirmation ? "需要确认" : "无需确认" }}
          </dd>
        </div>
        <div v-if="task">
          <dt>任务编号</dt>
          <dd>
            <code>{{ task.task_id }}</code>
          </dd>
        </div>
      </dl>

      <section>
        <h4>已提取参数</h4>
        <dl v-if="parameters.length" class="assistant-plan-details__parameters">
          <div v-for="[key, value] in parameters" :key="key">
            <dt>{{ parameterLabel(key) }}</dt>
            <dd>
              {{ displayParameterValue(key, value) }}
              <code>{{ key }}</code>
            </dd>
          </div>
        </dl>
        <p v-else>没有提取到参数。</p>
      </section>

      <section v-if="plan.missing_parameters.length">
        <h4>缺失参数</h4>
        <p>
          {{ plan.missing_parameters.map(parameterLabel).join("、") }}
        </p>
      </section>

      <section>
        <h4>执行步骤</h4>
        <ol v-if="plan.steps.length" class="assistant-plan-details__steps">
          <li v-for="step in plan.steps" :key="`${step.order}-${step.name}`">
            <span>{{ step.order }}</span>
            <div>
              <strong>{{ stepLabel(step.name) }}</strong>
              <p>{{ stepSummary(step.name, step.summary) }}</p>
              <code>{{ step.name }}</code>
            </div>
          </li>
        </ol>
        <p v-else>没有可执行步骤，不会调用工具。</p>
      </section>

      <section v-if="taskSteps.length">
        <h4>实际执行记录</h4>
        <ul class="assistant-plan-details__trace">
          <li v-for="step in taskSteps" :key="step.id">
            <span>{{ step.sequence }}. {{ stepLabel(step.node_name) }}</span>
            <code>{{ step.node_name }} · {{ statusLabel(step.status) }}</code>
          </li>
        </ul>
      </section>

      <section v-if="toolCalls.length">
        <h4>工具调用</h4>
        <ul class="assistant-plan-details__trace">
          <li v-for="toolCall in toolCalls" :key="toolCall.id">
            <span>{{ stepLabel(toolCall.tool_name) }}</span>
            <code>{{ toolCall.tool_name }} · {{ toolCall.id }}</code>
          </li>
        </ul>
      </section>
    </div>
  </details>
</template>

<style scoped>
.assistant-plan-details {
  width: 100%;
  margin-top: var(--sp-space-3);
  border-top: 1px solid var(--sp-border-soft);
}

.assistant-plan-details summary {
  width: fit-content;
  padding-top: var(--sp-space-3);
  color: var(--sp-color-primary);
  font-size: var(--sp-font-xs);
  font-weight: 750;
  cursor: pointer;
}

.assistant-plan-details__body {
  display: grid;
  gap: var(--sp-space-4);
  padding-top: var(--sp-space-4);
}

.assistant-plan-details__body section {
  min-width: 0;
}

.assistant-plan-details h4 {
  margin: 0 0 var(--sp-space-2);
  font-size: var(--sp-font-sm);
}

.assistant-plan-details p {
  margin: 0;
  color: var(--sp-color-text-secondary);
}

.assistant-plan-details__summary,
.assistant-plan-details__parameters {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-space-2) var(--sp-space-4);
  margin: 0;
}

.assistant-plan-details__summary > div,
.assistant-plan-details__parameters > div {
  display: grid;
  gap: var(--sp-space-1);
  min-width: 0;
  padding: var(--sp-space-2) 0;
}

.assistant-plan-details dt {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.assistant-plan-details dd {
  display: grid;
  gap: var(--sp-space-1);
  min-width: 0;
  margin: 0;
}

.assistant-plan-details code {
  max-width: 100%;
  overflow-wrap: anywhere;
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}

.assistant-plan-details__steps,
.assistant-plan-details__trace {
  display: grid;
  gap: var(--sp-space-2);
  padding: 0;
  margin: 0;
  list-style: none;
}

.assistant-plan-details__steps li {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
}

.assistant-plan-details__steps li > span {
  display: grid;
  flex: 0 0 26px;
  width: 26px;
  height: 26px;
  color: var(--sp-color-primary);
  font-size: var(--sp-font-xs);
  font-weight: 800;
  place-items: center;
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-pill);
}

.assistant-plan-details__steps div {
  display: grid;
  gap: var(--sp-space-1);
  min-width: 0;
}

.assistant-plan-details__trace li {
  display: grid;
  gap: var(--sp-space-1);
  padding: var(--sp-space-2) var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-control);
}

@media (max-width: 767px) {
  .assistant-plan-details__summary,
  .assistant-plan-details__parameters {
    grid-template-columns: 1fr;
  }
}
</style>
