<script setup lang="ts">
import {
  ArrowRight,
  Bot,
  ChevronLeft,
  ChevronRight,
  Clock3,
  LoaderCircle,
  PanelRightOpen,
  RefreshCw,
  RotateCcw,
  Send,
} from "@lucide/vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  createAssistantTask,
  listAssistantCapabilities,
  listRecentAssistantTasks,
  planAssistantMessage,
  type AssistantCapability,
  type AssistantExecutionMode,
  type AssistantPlan,
  type AssistantTaskResult,
} from "@/api/assistant";
import { FrontendApiError } from "@/api/http";
import { getTask, listTaskSteps, listTaskToolCalls, type TaskToolCall } from "@/api/tasks";
import AssistantPlanDetails from "@/components/assistant/AssistantPlanDetails.vue";
import AssistantResultContent from "@/components/assistant/AssistantResultContent.vue";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpEmptyState from "@/components/base/SpEmptyState.vue";
import SpSkeleton from "@/components/base/SpSkeleton.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useAppStore } from "@/stores/app";
import type { TaskDetail, TaskStatus, TaskStepDetail } from "@/types/contracts";
import {
  localizedTaskFailure,
  missingParameterPrompt,
  presentTaskResult,
  taskStatusLabels,
  workflowLabel,
  type AssistantResultPresentation,
} from "@/utils/assistantPresentation";
import { formatPlatformMode } from "@/utils/displayLabels";

type AssistantSubmitMode = AssistantExecutionMode | "plan_only";
type ChatMessageState = "ready" | "loading" | "error";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  state: ChatMessageState;
  plan?: AssistantPlan;
  taskResult?: AssistantTaskResult;
  task?: TaskDetail;
  taskSteps?: TaskStepDetail[];
  toolCalls?: TaskToolCall[];
  presentation?: AssistantResultPresentation;
  retryMessage?: string;
  retryMode?: AssistantSubmitMode;
  requestId?: string;
}

const TERMINAL_STATUSES = new Set<TaskStatus>(["succeeded", "failed", "cancelled"]);
const QUICK_PANEL_STORAGE_KEY = "sellpilot_assistant_quick_tasks_collapsed";
const POLL_INTERVAL_MS = 800;
const MAX_POLL_ATTEMPTS = 15;

const router = useRouter();
const { isMobile } = useBreakpoint();
const appStore = useAppStore();
const { platformStatus, platformStatusError, platformStatusLoading } = storeToRefs(appStore);
const message = ref("");
const selectedMode = ref<AssistantSubmitMode>("create_and_run");
const capabilities = ref<AssistantCapability[]>([]);
const loadingCapabilities = ref(false);
const capabilityError = ref("");
const recentTasks = ref<TaskDetail[]>([]);
const loadingRecentTasks = ref(false);
const recentTasksError = ref("");
const processing = ref(false);
const chatLog = ref<HTMLElement | null>(null);
const disposed = ref(false);
const pollTimers = new Set<number>();
const quickPanelCollapsed = ref(
  readPanelPreference() ?? (typeof window !== "undefined" && window.innerWidth < 1024),
);
const messages = ref<ChatMessage[]>([
  {
    id: "assistant-welcome",
    role: "assistant",
    content: "你好，我可以协助查询订单、分析库存、进行选品和商品运营分析。",
    state: "ready",
  },
]);

const modeOptions: Array<{ value: AssistantSubmitMode; label: string }> = [
  { value: "create_and_run", label: "发送并执行" },
  { value: "create_only", label: "仅创建任务" },
  { value: "plan_only", label: "仅生成计划" },
];

const latestAssistantTaskId = computed(
  () =>
    [...messages.value].reverse().find((item) => item.role === "assistant" && item.taskResult)
      ?.taskResult?.task_id ?? null,
);
const connectionView = computed(() => {
  if (platformStatusLoading.value) {
    return { label: "状态检测中", tone: "neutral" as const };
  }
  if (platformStatusError.value || !platformStatus.value?.reachable) {
    return { label: "后端未连接", tone: "danger" as const };
  }
  return { label: "后端已连接", tone: "success" as const };
});
const platformModeLabel = computed(() => {
  if (!platformStatus.value) return "模式未知";
  return formatPlatformMode(platformStatus.value.adapter);
});

function readPanelPreference(): boolean | null {
  try {
    const value = localStorage.getItem(QUICK_PANEL_STORAGE_KEY);
    return value === null ? null : value === "true";
  } catch {
    return null;
  }
}

function writePanelPreference(value: boolean) {
  try {
    localStorage.setItem(QUICK_PANEL_STORAGE_KEY, String(value));
  } catch {
    // 浏览器禁用本地存储时仅保留当前会话状态。
  }
}

function newId(): string {
  return crypto.randomUUID();
}

async function scrollToLatest() {
  await nextTick();
  chatLog.value?.scrollTo({ top: chatLog.value.scrollHeight, behavior: "smooth" });
}

function updateChatMessage(id: string, patch: Partial<ChatMessage>) {
  const target = messages.value.find((item) => item.id === id);
  if (target) Object.assign(target, patch);
  void scrollToLatest();
}

async function loadCapabilities() {
  loadingCapabilities.value = true;
  capabilityError.value = "";
  try {
    capabilities.value = await listAssistantCapabilities();
  } catch (error: unknown) {
    capabilities.value = [];
    capabilityError.value = safeError(error, "常用任务加载失败");
  } finally {
    loadingCapabilities.value = false;
  }
}

async function loadRecentTasks() {
  loadingRecentTasks.value = true;
  recentTasksError.value = "";
  try {
    recentTasks.value = await listRecentAssistantTasks();
  } catch (error: unknown) {
    recentTasks.value = [];
    recentTasksError.value = safeError(error, "最近任务加载失败");
  } finally {
    loadingRecentTasks.value = false;
  }
}

function useCapability(capability: AssistantCapability) {
  message.value = capability.example_message;
  if (isMobile.value) {
    quickPanelCollapsed.value = true;
    writePanelPreference(true);
  }
  void nextTick(() =>
    document.querySelector<HTMLTextAreaElement>('[data-testid="assistant-message"]')?.focus(),
  );
}

function toggleQuickPanel() {
  quickPanelCollapsed.value = !quickPanelCollapsed.value;
  writePanelPreference(quickPanelCollapsed.value);
}

async function openTaskCenter(taskId: string) {
  await router.push({ path: "/tasks", query: { task_id: taskId } });
}

function safeError(error: unknown, fallback: string): string {
  if (error instanceof FrontendApiError) {
    if (error.status === 401) return "登录状态已失效，请重新登录。";
    if (error.status === 404) return "任务或能力不存在，可能已被更新。";
    if (error.status === 409) return "请求冲突，请刷新任务状态后重试。";
    if (error.status === 422) return "输入内容不符合助手要求，请补充必要信息。";
    if (error.status >= 500) return "服务暂时不可用，请稍后重试。";
    if (error.status === 0) return "后端未连接，请检查服务状态后重试。";
    return fallback;
  }
  return fallback;
}

function statusTone(status: TaskStatus): "neutral" | "success" | "warning" | "danger" | "info" {
  if (status === "succeeded") return "success";
  if (status === "failed" || status === "cancelled") return "danger";
  if (status === "running") return "info";
  if (status === "waiting_confirmation" || status === "pending") return "warning";
  return "neutral";
}

function planReply(plan: AssistantPlan): string | null {
  if (plan.detected_intent === "unknown") {
    return "暂时无法识别该请求，请换一种更具体的表达。";
  }
  if (plan.availability === "contract_only") {
    return "该能力目前已完成接口契约，但尚未接入统一执行工作流。";
  }
  if (plan.availability === "unavailable") {
    return "该能力目前尚未开放执行。";
  }
  if (plan.missing_parameters.length) {
    return missingParameterPrompt(plan.missing_parameters);
  }
  return null;
}

async function waitForTask(taskId: string): Promise<TaskDetail> {
  let detail = await getTask(taskId);
  let attempt = 0;
  while (
    !disposed.value &&
    !TERMINAL_STATUSES.has(detail.status) &&
    detail.status !== "waiting_confirmation" &&
    attempt < MAX_POLL_ATTEMPTS
  ) {
    await new Promise<void>((resolve) => {
      const timer = window.setTimeout(() => {
        pollTimers.delete(timer);
        resolve();
      }, POLL_INTERVAL_MS);
      pollTimers.add(timer);
    });
    if (disposed.value) return detail;
    detail = await getTask(taskId);
    attempt += 1;
  }
  return detail;
}

async function loadTaskTrace(
  taskId: string,
): Promise<{ taskSteps: TaskStepDetail[]; toolCalls: TaskToolCall[] }> {
  const [stepsResult, toolsResult] = await Promise.allSettled([
    listTaskSteps(taskId),
    listTaskToolCalls(taskId),
  ]);
  return {
    taskSteps: stepsResult.status === "fulfilled" ? stepsResult.value : [],
    toolCalls: toolsResult.status === "fulfilled" ? toolsResult.value.items : [],
  };
}

async function submitMessage(
  overrideMessage?: string,
  overrideMode?: AssistantSubmitMode,
  existingRequestId?: string,
) {
  const normalized = (overrideMessage ?? message.value).trim();
  if (!normalized || processing.value) return;

  const mode = overrideMode ?? selectedMode.value;
  const requestId = existingRequestId ?? newId();
  const assistantMessageId = newId();
  messages.value.push(
    { id: newId(), role: "user", content: normalized, state: "ready" },
    {
      id: assistantMessageId,
      role: "assistant",
      content: "正在处理……",
      state: "loading",
      retryMessage: normalized,
      retryMode: mode,
      requestId,
    },
  );
  if (!overrideMessage) message.value = "";
  processing.value = true;
  void scrollToLatest();

  try {
    const plan = await planAssistantMessage(normalized);
    updateChatMessage(assistantMessageId, { plan });
    const immediateReply = planReply(plan);
    if (immediateReply) {
      updateChatMessage(assistantMessageId, { content: immediateReply, state: "ready" });
      return;
    }

    if (mode === "plan_only") {
      updateChatMessage(assistantMessageId, {
        content: "执行计划已生成，未创建任务或调用工具。",
        state: "ready",
      });
      return;
    }

    const executionMode: AssistantExecutionMode =
      mode === "create_only" ? "create_only" : "create_and_run";
    const taskResult = await createAssistantTask(normalized, executionMode, requestId);
    updateChatMessage(assistantMessageId, { taskResult });
    await loadRecentTasks();

    if (executionMode === "create_only") {
      updateChatMessage(assistantMessageId, {
        content: "任务已创建，尚未开始执行。",
        state: "ready",
      });
      return;
    }

    const task = await waitForTask(taskResult.task_id);
    const trace = await loadTaskTrace(taskResult.task_id);
    if (task.status === "succeeded") {
      updateChatMessage(assistantMessageId, {
        content: "任务已完成。",
        state: "ready",
        task,
        presentation: presentTaskResult(task.workflow_name, task.result),
        ...trace,
      });
      return;
    }
    if (task.status === "waiting_confirmation") {
      updateChatMessage(assistantMessageId, {
        content: "任务已暂停，等待你在任务中心确认后继续。",
        state: "ready",
        task,
        ...trace,
      });
      return;
    }
    if (task.status === "failed") {
      updateChatMessage(assistantMessageId, {
        content: `任务执行失败：${localizedTaskFailure(
          task.error_code,
          task.safe_error_summary ?? task.error_message,
          task.request_id,
        )}`,
        state: "error",
        task,
        ...trace,
      });
      return;
    }
    if (task.status === "cancelled") {
      updateChatMessage(assistantMessageId, {
        content: "任务已取消，没有生成业务结果。",
        state: "ready",
        task,
        ...trace,
      });
      return;
    }
    updateChatMessage(assistantMessageId, {
      content: `任务仍在${taskStatusLabels[task.status]}，可前往任务中心查看最新状态。`,
      state: "ready",
      task,
      ...trace,
    });
  } catch (error: unknown) {
    updateChatMessage(assistantMessageId, {
      content: safeError(error, "助手处理失败，请稍后重试。"),
      state: "error",
    });
  } finally {
    processing.value = false;
    void scrollToLatest();
  }
}

function retryChatMessage(chatMessage: ChatMessage) {
  if (!chatMessage.retryMessage || !chatMessage.retryMode) return;
  void submitMessage(chatMessage.retryMessage, chatMessage.retryMode, chatMessage.requestId);
}

function handleComposerKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  void submitMessage();
}

onMounted(async () => {
  await Promise.all([loadCapabilities(), loadRecentTasks()]);
});

onBeforeUnmount(() => {
  disposed.value = true;
  pollTimers.forEach((timer) => window.clearTimeout(timer));
  pollTimers.clear();
});
</script>

<template>
  <PageContainer>
    <section
      :class="[
        'assistant-workspace',
        { 'assistant-workspace--tasks-collapsed': quickPanelCollapsed },
      ]"
    >
      <div class="assistant-chat">
        <header class="assistant-chat__toolbar">
          <div>
            <Bot :size="18" aria-hidden="true" />
            <strong>对话工作台</strong>
          </div>
          <div>
            <SpBadge :tone="connectionView.tone" dot>{{ connectionView.label }}</SpBadge>
            <SpBadge tone="info">{{ platformModeLabel }}</SpBadge>
          </div>
        </header>

        <div
          ref="chatLog"
          class="assistant-chat__log"
          data-testid="assistant-chat"
          aria-live="polite"
        >
          <article
            v-for="chatMessage in messages"
            :key="chatMessage.id"
            :class="[
              'chat-message',
              `chat-message--${chatMessage.role}`,
              { 'chat-message--error': chatMessage.state === 'error' },
            ]"
          >
            <div
              v-if="chatMessage.role === 'assistant'"
              class="chat-message__avatar"
              aria-hidden="true"
            >
              <Bot :size="17" />
            </div>
            <div class="chat-message__bubble">
              <p
                :role="chatMessage.state === 'error' ? 'alert' : undefined"
                class="chat-message__copy"
              >
                <LoaderCircle
                  v-if="chatMessage.state === 'loading'"
                  class="chat-message__spinner"
                  :size="16"
                  aria-hidden="true"
                />
                {{ chatMessage.content }}
              </p>

              <AssistantResultContent
                v-if="chatMessage.presentation"
                :presentation="chatMessage.presentation"
              />

              <div v-if="chatMessage.taskResult" class="chat-message__task-actions">
                <SpBadge
                  :tone="statusTone(chatMessage.task?.status ?? chatMessage.taskResult.task_status)"
                >
                  {{
                    taskStatusLabels[chatMessage.task?.status ?? chatMessage.taskResult.task_status]
                  }}
                </SpBadge>
                <SpButton
                  size="sm"
                  variant="ghost"
                  data-testid="assistant-open-task"
                  @click="openTaskCenter(chatMessage.taskResult.task_id)"
                >
                  前往任务中心
                  <template #icon><ArrowRight :size="14" /></template>
                </SpButton>
              </div>

              <AssistantPlanDetails
                v-if="chatMessage.plan"
                :plan="chatMessage.plan"
                :task="chatMessage.taskResult"
                :task-steps="chatMessage.taskSteps"
                :tool-calls="chatMessage.toolCalls"
              />

              <SpButton
                v-if="chatMessage.state === 'error' && chatMessage.retryMessage"
                class="chat-message__retry"
                data-testid="assistant-retry"
                size="sm"
                variant="ghost"
                :disabled="processing"
                @click="retryChatMessage(chatMessage)"
              >
                <template #icon><RotateCcw :size="14" /></template>
                重试
              </SpButton>
            </div>
          </article>
        </div>

        <form class="assistant-composer" @submit.prevent="submitMessage()">
          <label class="sp-visually-hidden" for="assistant-message">输入运营问题</label>
          <textarea
            id="assistant-message"
            v-model="message"
            data-testid="assistant-message"
            maxlength="2000"
            rows="1"
            placeholder="输入你的运营问题…"
            :disabled="processing"
            @keydown="handleComposerKeydown"
          ></textarea>
          <div class="assistant-composer__actions">
            <label>
              <span class="sp-visually-hidden">发送方式</span>
              <select v-model="selectedMode" data-testid="assistant-mode" :disabled="processing">
                <option v-for="option in modeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
            <SpButton
              type="button"
              data-testid="assistant-send"
              :loading="processing"
              :disabled="!message.trim() || processing"
              @click="submitMessage()"
            >
              <template #icon><Send :size="16" /></template>
              发送
            </SpButton>
          </div>
        </form>
      </div>

      <button
        v-if="quickPanelCollapsed"
        type="button"
        class="assistant-quick-toggle"
        data-testid="assistant-quick-toggle"
        aria-label="展开常用任务"
        :aria-expanded="false"
        @click="toggleQuickPanel"
      >
        <PanelRightOpen :size="17" />
        <span>常用任务</span>
      </button>

      <button
        v-if="isMobile && !quickPanelCollapsed"
        type="button"
        class="assistant-quick-backdrop"
        aria-label="关闭常用任务"
        @click="toggleQuickPanel"
      ></button>

      <aside
        class="assistant-quick-panel"
        data-testid="assistant-quick-tasks"
        :aria-hidden="quickPanelCollapsed"
      >
        <header>
          <h2>常用任务</h2>
          <button
            type="button"
            data-testid="assistant-quick-toggle"
            aria-label="收起常用任务"
            :aria-expanded="true"
            @click="toggleQuickPanel"
          >
            <ChevronRight :size="17" />
          </button>
        </header>

        <div class="assistant-quick-panel__body">
          <div v-if="loadingCapabilities" class="assistant-quick-panel__loading">
            <SpSkeleton v-for="index in 4" :key="index" variant="line" />
          </div>
          <p v-else-if="capabilityError" class="assistant-quick-panel__error">
            {{ capabilityError }}
          </p>
          <div v-else class="quick-task-list">
            <button
              v-for="capability in capabilities"
              :key="capability.capability_key"
              type="button"
              :data-capability="capability.capability_key"
              :class="[
                'quick-task-item',
                { 'quick-task-item--limited': capability.availability !== 'available' },
              ]"
              :title="capability.display_name"
              @click="useCapability(capability)"
            >
              <span>{{ capability.display_name }}</span>
              <ChevronLeft :size="14" aria-hidden="true" />
            </button>
          </div>
        </div>

        <details class="assistant-recent-tasks">
          <summary>
            <span><Clock3 :size="15" />最近任务</span>
            <RefreshCw
              :class="{ 'assistant-recent-tasks__refreshing': loadingRecentTasks }"
              :size="14"
              aria-hidden="true"
            />
          </summary>
          <p v-if="recentTasksError" class="assistant-quick-panel__error">{{ recentTasksError }}</p>
          <div v-else-if="loadingRecentTasks" class="assistant-quick-panel__loading">
            <SpSkeleton v-for="index in 2" :key="index" variant="line" />
          </div>
          <ul v-else-if="recentTasks.length">
            <li v-for="task in recentTasks" :key="task.id">
              <button type="button" @click="openTaskCenter(task.id)">
                <span>{{ workflowLabel(task.workflow_name) }}</span>
                <small>{{ taskStatusLabels[task.status] }}</small>
              </button>
            </li>
          </ul>
          <SpEmptyState v-else title="暂无最近任务" description="完成任务后会显示在这里。" />
        </details>
      </aside>
    </section>
    <span v-if="latestAssistantTaskId" class="sp-visually-hidden">
      最近创建的任务：{{ latestAssistantTaskId }}
    </span>
  </PageContainer>
</template>

<style scoped>
.assistant-workspace {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 248px;
  gap: var(--sp-space-4);
  min-width: 0;
  height: clamp(590px, calc(100dvh - 176px), 850px);
  min-height: 0;
  transition: grid-template-columns var(--sp-transition-normal);
}

.assistant-workspace--tasks-collapsed {
  grid-template-columns: minmax(0, 1fr) 0;
}

.assistant-chat {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-card);
  box-shadow: var(--sp-shadow-card);
  backdrop-filter: blur(18px);
}

.assistant-chat__toolbar {
  display: flex;
  flex: 0 0 auto;
  gap: var(--sp-space-4);
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-space-4) var(--sp-space-5);
  border-bottom: 1px solid var(--sp-border-soft);
}

.assistant-chat__toolbar > div {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
}

.assistant-chat__toolbar > div:first-child {
  color: var(--sp-color-primary);
}

.assistant-chat__log {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--sp-space-4);
  min-height: 0;
  padding: var(--sp-space-6);
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.chat-message {
  display: flex;
  gap: var(--sp-space-2);
  align-items: flex-start;
  max-width: 82%;
}

.chat-message--assistant {
  align-self: flex-start;
}

.chat-message--user {
  align-self: flex-end;
  justify-content: flex-end;
  max-width: 76%;
}

.chat-message__avatar {
  display: grid;
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  color: var(--sp-color-primary);
  place-items: center;
  background: var(--sp-color-accent-blue-soft);
  border-radius: var(--sp-radius-pill);
}

.chat-message__bubble {
  min-width: 0;
  max-width: 100%;
  padding: var(--sp-space-3) var(--sp-space-4);
  background: var(--sp-color-surface-strong);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-card-small);
  border-top-left-radius: var(--sp-space-1);
}

.chat-message--user .chat-message__bubble {
  color: var(--sp-color-text-inverse);
  background: var(--sp-color-primary);
  border-color: transparent;
  border-top-left-radius: var(--sp-radius-card-small);
  border-top-right-radius: var(--sp-space-1);
}

.chat-message--error .chat-message__bubble {
  border-color: color-mix(in srgb, var(--sp-color-danger) 24%, transparent);
}

.chat-message__copy {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  margin: 0;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.chat-message__spinner {
  flex: 0 0 auto;
  color: var(--sp-color-info);
  animation: assistant-spin 0.85s linear infinite;
}

.chat-message__task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-space-2);
  align-items: center;
  margin-top: var(--sp-space-3);
}

.chat-message__retry {
  margin-top: var(--sp-space-2);
}

.assistant-composer {
  display: grid;
  flex: 0 0 auto;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--sp-space-3);
  align-items: end;
  padding: var(--sp-space-4);
  background: color-mix(in srgb, var(--sp-color-surface-strong) 88%, transparent);
  border-top: 1px solid var(--sp-border-soft);
  backdrop-filter: blur(16px);
}

.assistant-composer textarea {
  width: 100%;
  min-height: 46px;
  max-height: 132px;
  padding: var(--sp-space-3) var(--sp-space-4);
  overflow-y: auto;
  color: var(--sp-color-text);
  line-height: 1.5;
  resize: vertical;
  background: var(--sp-color-surface-muted);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
  outline: none;
}

.assistant-composer textarea:focus {
  background: var(--sp-color-surface-strong);
  border-color: var(--sp-color-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-color-accent-blue) 16%, transparent);
}

.assistant-composer textarea:disabled {
  cursor: wait;
  opacity: 0.72;
}

.assistant-composer__actions {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
}

.assistant-composer select {
  min-height: 42px;
  padding: 0 var(--sp-space-8) 0 var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  cursor: pointer;
  background: var(--sp-color-surface-strong);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-control);
}

.assistant-quick-toggle {
  position: absolute;
  z-index: 7;
  top: var(--sp-space-3);
  right: var(--sp-space-3);
  display: inline-flex;
  gap: var(--sp-space-2);
  align-items: center;
  min-height: 34px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  cursor: pointer;
  background: var(--sp-color-surface-strong);
  border: 1px solid var(--sp-border-soft);
  border-radius: var(--sp-radius-pill);
  box-shadow: var(--sp-shadow-card);
  transition: right var(--sp-transition-normal);
}

.assistant-quick-panel {
  position: relative;
  z-index: 6;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-highlight);
  border-radius: var(--sp-radius-card);
  box-shadow: var(--sp-shadow-card);
  opacity: 1;
  transition:
    opacity var(--sp-transition-fast),
    transform var(--sp-transition-normal);
  backdrop-filter: blur(18px);
}

.assistant-workspace--tasks-collapsed .assistant-quick-panel {
  pointer-events: none;
  border-width: 0;
  opacity: 0;
}

.assistant-quick-panel > header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  min-height: 58px;
  padding: 0 var(--sp-space-4);
  border-bottom: 1px solid var(--sp-border-soft);
}

.assistant-quick-panel h2 {
  margin: 0;
  font-size: var(--sp-font-md);
}

.assistant-quick-panel > header button {
  display: grid;
  width: 30px;
  height: 30px;
  color: var(--sp-color-text-muted);
  cursor: pointer;
  place-items: center;
  background: transparent;
  border-radius: var(--sp-radius-pill);
}

.assistant-quick-panel > header button:hover {
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-hover);
}

.assistant-quick-panel__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.quick-task-list {
  display: grid;
  gap: var(--sp-space-1);
  padding: var(--sp-space-3);
}

.quick-task-item {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  min-height: 38px;
  padding: 0 var(--sp-space-3);
  color: var(--sp-color-text-secondary);
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--sp-radius-control);
}

.quick-task-item:hover {
  color: var(--sp-color-primary);
  background: var(--sp-color-surface-hover);
  border-color: var(--sp-border-soft);
}

.quick-task-item--limited {
  opacity: 0.58;
}

.quick-task-item span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-task-item svg {
  flex: 0 0 auto;
  opacity: 0;
  transition: opacity var(--sp-transition-fast);
}

.quick-task-item:hover svg {
  opacity: 1;
}

.assistant-quick-panel__loading,
.assistant-quick-panel__error {
  display: grid;
  gap: var(--sp-space-2);
  padding: var(--sp-space-4);
}

.assistant-quick-panel__error {
  color: var(--sp-color-danger);
  font-size: var(--sp-font-xs);
}

.assistant-recent-tasks {
  flex: 0 0 auto;
  max-height: 42%;
  overflow-y: auto;
  border-top: 1px solid var(--sp-border-soft);
}

.assistant-recent-tasks summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 46px;
  padding: 0 var(--sp-space-4);
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 750;
  cursor: pointer;
  list-style: none;
}

.assistant-recent-tasks summary span {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
}

.assistant-recent-tasks ul {
  display: grid;
  gap: var(--sp-space-1);
  padding: 0 var(--sp-space-3) var(--sp-space-3);
}

.assistant-recent-tasks li button {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  padding: var(--sp-space-2);
  color: var(--sp-color-text-secondary);
  text-align: left;
  cursor: pointer;
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-control);
}

.assistant-recent-tasks li span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.assistant-recent-tasks li small {
  flex: 0 0 auto;
  color: var(--sp-color-text-muted);
}

.assistant-recent-tasks__refreshing {
  animation: assistant-spin 0.85s linear infinite;
}

.assistant-quick-backdrop {
  display: none;
}

@keyframes assistant-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1279px) {
  .assistant-workspace {
    grid-template-columns: minmax(0, 1fr) 224px;
  }
}

@media (max-width: 1023px) {
  .assistant-workspace {
    grid-template-columns: minmax(0, 1fr);
    height: clamp(560px, calc(100dvh - 206px), 780px);
  }

  .assistant-workspace--tasks-collapsed {
    grid-template-columns: minmax(0, 1fr);
  }

  .assistant-quick-panel {
    position: fixed;
    z-index: 52;
    top: var(--sp-space-4);
    right: var(--sp-space-4);
    bottom: var(--sp-space-4);
    width: min(280px, calc(100vw - var(--sp-space-8)));
  }

  .assistant-workspace--tasks-collapsed .assistant-quick-panel {
    transform: translateX(calc(100% + var(--sp-space-6)));
  }

  .assistant-quick-toggle {
    position: fixed;
    z-index: 53;
    top: var(--sp-space-6);
    right: var(--sp-space-6);
  }

  .assistant-quick-backdrop {
    position: fixed;
    z-index: 51;
    display: block;
    inset: 0;
    cursor: pointer;
    background: var(--sp-color-overlay);
    backdrop-filter: blur(3px);
  }
}

@media (max-width: 767px) {
  .assistant-workspace {
    height: calc(100dvh - 184px);
    min-height: 500px;
  }

  .assistant-chat__toolbar {
    align-items: flex-start;
    padding: var(--sp-space-3) var(--sp-space-4);
  }

  .assistant-chat__toolbar > div:last-child {
    display: grid;
    justify-items: end;
  }

  .assistant-chat__log {
    padding: var(--sp-space-4);
  }

  .chat-message,
  .chat-message--user {
    max-width: 92%;
  }

  .assistant-composer {
    grid-template-columns: 1fr;
  }

  .assistant-composer__actions {
    justify-content: space-between;
  }

  .assistant-composer select {
    max-width: 160px;
  }

  .assistant-quick-toggle {
    top: var(--sp-space-4);
    right: var(--sp-space-4);
  }
}
</style>
