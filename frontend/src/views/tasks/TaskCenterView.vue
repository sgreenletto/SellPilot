<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  cancelConfirmation,
  cancelTask,
  confirmConfirmation,
  getTask,
  listTaskConfirmations,
  listTaskOperationLogs,
  listTaskSteps,
  listTasks,
  listTaskToolCalls,
  rerunTask,
  resumeTask,
  retryTask,
  runTask,
  type TaskConfirmation,
  type TaskOperationLog,
  type TaskToolCall,
} from "@/api/tasks";
import { FrontendApiError } from "@/api/http";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpCard from "@/components/base/SpCard.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpSelect, { type SelectOption } from "@/components/base/SpSelect.vue";
import SpSkeleton from "@/components/base/SpSkeleton.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import {
  TASK_STATUSES,
  type TaskAction,
  type TaskDetail,
  type TaskStatus,
  type TaskStepDetail,
} from "@/types/contracts";

const route = useRoute();
const router = useRouter();
const pageSize = 20;
const page = ref(1);
const total = ref(0);
const tasks = ref<TaskDetail[]>([]);
const loading = ref(false);
const detailLoading = ref(false);
const errorMessage = ref("");
const detailError = ref("");
const selectedTaskId = ref("");
const selectedTask = ref<TaskDetail | null>(null);
const steps = ref<TaskStepDetail[]>([]);
const confirmations = ref<TaskConfirmation[]>([]);
const toolCalls = ref<TaskToolCall[]>([]);
const operationLogs = ref<TaskOperationLog[]>([]);
const activeOperation = ref("");

const statusFilter = ref("__all__");
const workflowFilter = ref("__all__");
const taskTypeFilter = ref("__all__");
const createdFrom = ref("");
const createdTo = ref("");

const statusOptions: SelectOption[] = [
  { label: "全部状态", value: "__all__" },
  ...TASK_STATUSES.map((status) => ({ label: status, value: status })),
];
const workflowOptions = computed<SelectOption[]>(() => [
  { label: "全部 Workflow", value: "__all__" },
  ...Array.from(new Set(tasks.value.map((task) => task.workflow_name)))
    .sort()
    .map((value) => ({ label: value, value })),
]);
const taskTypeOptions = computed<SelectOption[]>(() => [
  { label: "全部类型", value: "__all__" },
  ...Array.from(new Set(tasks.value.map((task) => task.task_type)))
    .sort()
    .map((value) => ({ label: value, value })),
]);
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

function formatTime(value: string | null): string {
  return value ? new Date(value).toLocaleString("zh-CN") : "—";
}

function summary(value: Record<string, unknown> | null): string {
  return value ? JSON.stringify(value, null, 2) : "—";
}

function statusTone(status: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (status === "succeeded") return "success";
  if (status === "failed" || status === "cancelled") return "danger";
  if (status === "running") return "info";
  if (status === "waiting_confirmation" || status === "pending") return "warning";
  return "neutral";
}

function displayError(error: unknown): string {
  if (!(error instanceof FrontendApiError)) return "任务中心加载失败，请稍后重试";
  if (error.status === 409) return "任务状态已变化，请刷新";
  if (error.status === 404) return "资源不存在或无权访问";
  if (error.status === 422) return error.message || "请求参数校验失败";
  return error.message;
}

function filterValue(value: string): string | undefined {
  return value === "__all__" ? undefined : value;
}

async function loadTasks(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";
  try {
    const result = await listTasks({
      page: page.value,
      page_size: pageSize,
      status: filterValue(statusFilter.value) as TaskStatus | undefined,
      workflow_name: filterValue(workflowFilter.value),
      task_type: filterValue(taskTypeFilter.value),
      created_from: createdFrom.value
        ? new Date(`${createdFrom.value}T00:00:00`).toISOString()
        : undefined,
      created_to: createdTo.value
        ? new Date(`${createdTo.value}T23:59:59`).toISOString()
        : undefined,
    });
    tasks.value = result.items;
    total.value = result.total;
  } catch (error) {
    tasks.value = [];
    total.value = 0;
    errorMessage.value = displayError(error);
  } finally {
    loading.value = false;
  }
}

async function loadDetail(taskId: string): Promise<void> {
  selectedTaskId.value = taskId;
  detailLoading.value = true;
  detailError.value = "";
  await router.replace({ query: { ...route.query, task_id: taskId } });
  try {
    const [detail, stepItems, callPage, confirmationPage, logPage] = await Promise.all([
      getTask(taskId),
      listTaskSteps(taskId),
      listTaskToolCalls(taskId),
      listTaskConfirmations(taskId),
      listTaskOperationLogs(taskId),
    ]);
    selectedTask.value = detail;
    steps.value = stepItems;
    toolCalls.value = callPage.items;
    confirmations.value = confirmationPage.items;
    operationLogs.value = logPage.items;
  } catch (error) {
    selectedTask.value = null;
    steps.value = [];
    toolCalls.value = [];
    confirmations.value = [];
    operationLogs.value = [];
    detailError.value = displayError(error);
  } finally {
    detailLoading.value = false;
  }
}

async function refreshAll(): Promise<void> {
  await loadTasks();
  if (selectedTaskId.value) await loadDetail(selectedTaskId.value);
}

async function performTaskAction(action: TaskAction): Promise<void> {
  const taskId = selectedTaskId.value;
  if (!taskId || activeOperation.value) return;
  activeOperation.value = action;
  detailError.value = "";
  try {
    if (action === "run") await runTask(taskId);
    if (action === "resume") await resumeTask(taskId);
    if (action === "retry") await retryTask(taskId);
    if (action === "cancel") await cancelTask(taskId);
    if (action === "rerun") {
      const created = await rerunTask(taskId);
      selectedTaskId.value = created.id;
    }
    await refreshAll();
  } catch (error) {
    detailError.value = displayError(error);
  } finally {
    activeOperation.value = "";
  }
}

async function performConfirmationAction(
  confirmation: TaskConfirmation,
  action: "confirm" | "cancel",
): Promise<void> {
  if (activeOperation.value) return;
  if (
    action === "confirm" &&
    !window.confirm("该操作可能修改业务数据。请确认已核对风险提示和变更摘要。")
  ) {
    return;
  }
  activeOperation.value = `${action}:${confirmation.id}`;
  detailError.value = "";
  try {
    if (action === "confirm") await confirmConfirmation(confirmation.id);
    else await cancelConfirmation(confirmation.id);
    await refreshAll();
  } catch (error) {
    detailError.value = displayError(error);
  } finally {
    activeOperation.value = "";
  }
}

async function applyFilters(): Promise<void> {
  page.value = 1;
  await loadTasks();
}

async function resetFilters(): Promise<void> {
  statusFilter.value = "__all__";
  workflowFilter.value = "__all__";
  taskTypeFilter.value = "__all__";
  createdFrom.value = "";
  createdTo.value = "";
  await applyFilters();
}

async function changePage(nextPage: number): Promise<void> {
  page.value = nextPage;
  await loadTasks();
}

onMounted(async () => {
  await loadTasks();
  const taskId = typeof route.query.task_id === "string" ? route.query.task_id : "";
  if (taskId) await loadDetail(taskId);
});
</script>

<template>
  <PageContainer>
    <div class="task-center">
      <header class="task-center__header">
        <div>
          <p class="task-center__eyebrow">TaskWorkflowRuntime</p>
          <h1>任务中心</h1>
          <p>查看任务进度、确认风险操作，并按服务端允许的操作继续执行。</p>
        </div>
        <div class="task-center__header-actions">
          <span>筛选结果 {{ total }} 条</span>
          <SpButton variant="secondary" :loading="loading" @click="refreshAll">刷新</SpButton>
        </div>
      </header>

      <SpCard padding="sm">
        <div class="filters">
          <SpSelect v-model="statusFilter" label="状态" :options="statusOptions" />
          <SpSelect v-model="workflowFilter" label="Workflow" :options="workflowOptions" />
          <SpSelect v-model="taskTypeFilter" label="Task Type" :options="taskTypeOptions" />
          <label class="date-field">创建自<input v-model="createdFrom" type="date" /></label>
          <label class="date-field">创建至<input v-model="createdTo" type="date" /></label>
          <div class="filters__actions">
            <SpButton size="sm" @click="applyFilters">应用筛选</SpButton>
            <SpButton size="sm" variant="ghost" @click="resetFilters">重置筛选</SpButton>
          </div>
        </div>
      </SpCard>

      <p v-if="errorMessage" class="message message--error" role="alert">{{ errorMessage }}</p>
      <div v-if="loading" class="skeleton-grid">
        <SpSkeleton v-for="index in 3" :key="index" variant="card" />
      </div>
      <SpEmptyState
        v-else-if="!tasks.length"
        title="暂无任务"
        description="当前筛选条件下没有可展示的真实任务。"
      />
      <SpCard v-else padding="sm">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>状态</th>
                <th>Workflow</th>
                <th>类型</th>
                <th>当前节点</th>
                <th>创建时间</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="task in tasks"
                :key="task.id"
                :class="{ 'is-selected': task.id === selectedTaskId }"
              >
                <td>
                  <SpBadge :tone="statusTone(task.status)" dot>{{ task.status }}</SpBadge>
                  <small v-if="task.waiting_confirmation">等待确认</small>
                </td>
                <td>
                  {{ task.workflow_name }} <small>v{{ task.workflow_version }}</small>
                </td>
                <td>{{ task.task_type }}</td>
                <td>{{ task.current_node || "—" }}</td>
                <td>{{ formatTime(task.created_at) }}</td>
                <td>{{ formatTime(task.updated_at) }}</td>
                <td>
                  <SpButton size="sm" variant="ghost" @click="loadDetail(task.id)">详情</SpButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <template #footer>
          <div class="pagination">
            <SpButton
              size="sm"
              variant="secondary"
              :disabled="page <= 1"
              @click="changePage(page - 1)"
            >
              上一页
            </SpButton>
            <span>第 {{ page }} / {{ totalPages }} 页</span>
            <SpButton
              size="sm"
              variant="secondary"
              :disabled="page >= totalPages"
              @click="changePage(page + 1)"
            >
              下一页
            </SpButton>
          </div>
        </template>
      </SpCard>

      <p v-if="detailError" class="message message--error" role="alert">{{ detailError }}</p>
      <SpSkeleton v-if="detailLoading" variant="card" />
      <SpCard v-else-if="selectedTask" padding="lg">
        <template #header>
          <div class="detail-title">
            <div>
              <h2>任务详情</h2>
              <code>{{ selectedTask.id }}</code>
            </div>
            <SpBadge :tone="statusTone(selectedTask.status)" dot>{{ selectedTask.status }}</SpBadge>
          </div>
        </template>

        <section class="detail-section">
          <h3>基本信息</h3>
          <dl class="detail-grid">
            <div>
              <dt>Workflow</dt>
              <dd>{{ selectedTask.workflow_name }} v{{ selectedTask.workflow_version }}</dd>
            </div>
            <div>
              <dt>Task Type</dt>
              <dd>{{ selectedTask.task_type }}</dd>
            </div>
            <div>
              <dt>当前节点</dt>
              <dd>{{ selectedTask.current_node || "—" }}</dd>
            </div>
            <div>
              <dt>父任务</dt>
              <dd>{{ selectedTask.parent_task_id || "—" }}</dd>
            </div>
            <div>
              <dt>等待原因</dt>
              <dd>{{ selectedTask.waiting_reason || "—" }}</dd>
            </div>
            <div>
              <dt>Request ID</dt>
              <dd>
                <code>{{ selectedTask.request_id }}</code>
              </dd>
            </div>
          </dl>
          <div class="action-row">
            <SpButton
              v-for="action in selectedTask.available_actions"
              :key="action"
              :variant="action === 'cancel' ? 'danger' : 'primary'"
              :loading="activeOperation === action"
              :disabled="Boolean(activeOperation)"
              @click="performTaskAction(action)"
            >
              {{ action }}
            </SpButton>
          </div>
        </section>

        <section class="detail-section">
          <h3>Step 时间线</h3>
          <div v-if="steps.length" class="timeline">
            <article v-for="step in steps" :key="step.id" class="timeline__item">
              <header>
                <strong>#{{ step.sequence }} {{ step.node_name }}</strong
                ><SpBadge :tone="statusTone(step.status)">{{ step.status }}</SpBadge>
              </header>
              <p>
                {{ step.node_type }} · 尝试 {{ step.attempt_count }} 次 ·
                {{ formatTime(step.started_at) }} → {{ formatTime(step.completed_at) }}
              </p>
              <pre>输入：{{ summary(step.input_summary) }}</pre>
              <pre>输出：{{ summary(step.output_summary) }}</pre>
              <small
                >ToolCall {{ step.tool_call_id || "—" }} · Confirmation
                {{ step.confirmation_id || "—" }}</small
              >
            </article>
          </div>
          <p v-else class="muted">暂无 Step。</p>
        </section>

        <section class="detail-section">
          <h3>Confirmation</h3>
          <div class="card-list">
            <article v-for="confirmation in confirmations" :key="confirmation.id" class="sub-card">
              <header>
                <strong>{{ confirmation.operation_type }}</strong
                ><SpBadge :tone="statusTone(confirmation.status)">{{
                  confirmation.status
                }}</SpBadge>
              </header>
              <p>风险等级：{{ confirmation.risk_level }}</p>
              <p v-if="confirmation.risk_warning">{{ confirmation.risk_warning }}</p>
              <pre>变更前：{{ summary(confirmation.before_snapshot) }}</pre>
              <pre>变更后：{{ summary(confirmation.after_snapshot) }}</pre>
              <pre>执行结果：{{ summary(confirmation.execution_result) }}</pre>
              <p>
                {{ formatTime(confirmation.created_at) }} · 确认于
                {{ formatTime(confirmation.confirmed_at) }}
              </p>
              <div v-if="confirmation.status === 'pending'" class="action-row">
                <SpButton
                  size="sm"
                  :loading="activeOperation === `confirm:${confirmation.id}`"
                  :disabled="Boolean(activeOperation)"
                  @click="performConfirmationAction(confirmation, 'confirm')"
                >
                  确认执行
                </SpButton>
                <SpButton
                  size="sm"
                  variant="danger"
                  :loading="activeOperation === `cancel:${confirmation.id}`"
                  :disabled="Boolean(activeOperation)"
                  @click="performConfirmationAction(confirmation, 'cancel')"
                >
                  取消
                </SpButton>
              </div>
            </article>
            <p v-if="!confirmations.length" class="muted">暂无 Confirmation。</p>
          </div>
        </section>

        <section class="detail-section">
          <h3>ToolCall</h3>
          <div class="card-list">
            <article v-for="call in toolCalls" :key="call.id" class="sub-card">
              <header>
                <strong>{{ call.tool_name }} v{{ call.tool_version }}</strong
                ><SpBadge :tone="statusTone(call.status)">{{ call.status }}</SpBadge>
              </header>
              <p>尝试 {{ call.attempt_count }} 次 · 耗时 {{ call.duration_ms ?? "—" }} ms</p>
              <pre>输入：{{ summary(call.input_summary) }}</pre>
              <pre>输出：{{ summary(call.output_summary) }}</pre>
              <p v-if="call.error_message" class="message--error">{{ call.error_message }}</p>
              <small>Request ID：{{ call.request_id }}</small>
            </article>
            <p v-if="!toolCalls.length" class="muted">暂无 ToolCall。</p>
          </div>
        </section>

        <section class="detail-section">
          <h3>OperationLog</h3>
          <div class="timeline">
            <article v-for="log in operationLogs" :key="log.id" class="timeline__item">
              <header>
                <strong>{{ formatTime(log.created_at) }} · {{ log.event_type }}</strong
                ><SpBadge :tone="statusTone(log.status)">{{ log.status }}</SpBadge>
              </header>
              <p>{{ log.description }}</p>
              <small
                >Step {{ log.task_step_id || "—" }} · ToolCall {{ log.tool_call_id || "—" }} ·
                Confirmation {{ log.confirmation_id || "—" }}</small
              >
              <small>Request ID：{{ log.request_id }}</small>
            </article>
            <p v-if="!operationLogs.length" class="muted">暂无 OperationLog。</p>
          </div>
        </section>

        <section v-if="selectedTask.safe_error_summary" class="detail-section">
          <h3>安全错误摘要</h3>
          <p class="message message--error">{{ selectedTask.safe_error_summary }}</p>
        </section>
      </SpCard>
    </div>
  </PageContainer>
</template>

<style scoped>
.task-center {
  display: grid;
  gap: var(--sp-space-6);
}
.task-center__header,
.task-center__header-actions,
.detail-title,
.action-row,
.pagination,
article header {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  justify-content: space-between;
}
.task-center__header {
  padding-top: var(--sp-space-7);
}
.task-center__header h1 {
  margin: var(--sp-space-1) 0;
}
.task-center__header p,
.muted,
small {
  color: var(--sp-color-text-muted);
}
.task-center__eyebrow {
  color: var(--sp-color-accent-blue) !important;
  font-size: var(--sp-font-xs);
  font-weight: 750;
  text-transform: uppercase;
}
.filters {
  display: grid;
  grid-template-columns: repeat(5, minmax(130px, 1fr)) auto;
  gap: var(--sp-space-3);
  align-items: end;
}
.filters__actions,
.action-row {
  display: flex;
  gap: var(--sp-space-2);
  flex-wrap: wrap;
}
.date-field {
  display: grid;
  gap: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}
.date-field input {
  min-height: 40px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}
.skeleton-grid,
.card-list,
.timeline {
  display: grid;
  gap: var(--sp-space-3);
}
.message {
  padding: var(--sp-space-3) var(--sp-space-4);
  border-radius: var(--sp-radius-control);
}
.message--error {
  color: var(--sp-color-danger);
  background: var(--sp-color-accent-pink-soft);
}
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: var(--sp-space-3);
  text-align: left;
  border-bottom: 1px solid var(--sp-border-soft);
}
th {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
tbody tr.is-selected {
  background: var(--sp-color-accent-blue-soft);
}
td small {
  display: block;
  margin-top: var(--sp-space-1);
}
.pagination {
  justify-content: flex-end;
}
.detail-title {
  width: 100%;
}
.detail-title code {
  color: var(--sp-color-text-muted);
}
.detail-section {
  display: grid;
  gap: var(--sp-space-3);
  padding: var(--sp-space-5) 0;
  border-bottom: 1px solid var(--sp-border-soft);
}
.detail-section:last-child {
  border-bottom: 0;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-space-4);
  margin: 0;
}
.detail-grid div {
  min-width: 0;
}
dt {
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
}
dd {
  margin: var(--sp-space-1) 0 0;
  overflow-wrap: anywhere;
}
.timeline__item,
.sub-card {
  display: grid;
  gap: var(--sp-space-2);
  padding: var(--sp-space-4);
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-card-small);
}
pre {
  max-height: 220px;
  padding: var(--sp-space-3);
  overflow: auto;
  color: var(--sp-color-text-secondary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: var(--sp-color-surface-strong);
  border-radius: var(--sp-radius-control);
}
.timeline__item small {
  display: block;
}
@media (max-width: 1023px) {
  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .detail-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 640px) {
  .task-center__header,
  .detail-title {
    align-items: flex-start;
    flex-direction: column;
  }
  .filters,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
