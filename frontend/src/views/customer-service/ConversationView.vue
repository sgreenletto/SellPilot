<script setup lang="ts">
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  ChevronDown,
  Globe,
  MessageCircle,
  MessageSquare,
  Package,
  Search,
  Send,
  Truck,
  UserCheck,
  X,
} from "@lucide/vue"
import { ElMessage } from "element-plus"
import { computed, ref, watch } from "vue"

import SpAvatar from "@/components/base/SpAvatar.vue"
import SpBadge from "@/components/base/SpBadge.vue"
import SpButton from "@/components/base/SpButton.vue"
import SpIconButton from "@/components/base/SpIconButton.vue"
import SpInput from "@/components/base/SpInput.vue"
import SpSelect from "@/components/base/SpSelect.vue"
import PageContainer from "@/components/layout/PageContainer.vue"
import {
  chatMessages,
  conversationContexts,
  conversations,
} from "@/mocks/customer-service"
import type {
  BuyerLanguage,
  Conversation,
  ConversationTab,
} from "@/types/customer-service"

// ==================== 页签筛选 ====================

const tabs: { key: ConversationTab; label: string; count?: number }[] = [
  { key: "all", label: "全部" },
  { key: "pending_reply", label: "待回复" },
  { key: "pending_human", label: "待人工" },
  { key: "resolved", label: "已解决" },
]

const activeTab = ref<ConversationTab>("all")

const filteredConversations = computed(() => {
  if (activeTab.value === "all") return conversations
  return conversations.filter((c) => c.status === activeTab.value)
})

// 每个页签下的会话数
function tabCount(key: ConversationTab): number {
  if (key === "all") return conversations.length
  return conversations.filter((c) => c.status === key).length
}

// ==================== 选中会话 ====================

const selectedId = ref<string>(conversations[0]?.id ?? "")
const selectedConversation = computed(() =>
  conversations.find((c) => c.id === selectedId.value) ?? null,
)
const activeMessages = computed(() => chatMessages[selectedId.value] ?? [])
const activeContext = computed(() => conversationContexts[selectedId.value] ?? null)

// 移动端：是否展示对话区（而非列表）
const showChat = ref(false)

function selectConversation(id: string) {
  selectedId.value = id
  showChat.value = true
}

function backToList() {
  showChat.value = false
}

// 切换页签时重置首条选中
watch(activeTab, (tab) => {
  const first = conversations.find((c) => (tab === "all" ? true : c.status === tab))
  if (first) {
    selectedId.value = first.id
  }
})

// ==================== 人工回复编辑器 ====================

const replyText = ref("")
const transferNote = ref("")
const showTransferInput = ref(false)

function sendReply() {
  const trimmed = replyText.value.trim()
  if (!trimmed) {
    ElMessage.warning("请输入回复内容")
    return
  }
  ElMessage.success("模拟回复已发送，系统将生成待确认任务")
  replyText.value = ""
}

function transferToHuman() {
  const note = transferNote.value.trim()
  ElMessage.success(
    note
      ? `已转人工处理，备注：${note}`
      : "已转人工处理，客服将在 5 分钟内接手",
  )
  transferNote.value = ""
  showTransferInput.value = false
}

// ==================== 快捷筛选 ====================

const searchQuery = ref("")
const langFilter = ref("all")
const langOptions = [
  { label: "全部语种", value: "all" },
  { label: "印尼语", value: "id" },
  { label: "泰语", value: "th" },
  { label: "越南语", value: "vi" },
]

const displayConversations = computed(() => {
  let list = filteredConversations.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(
      (c) =>
        c.buyerName.toLowerCase().includes(q) ||
        c.lastMessage.toLowerCase().includes(q) ||
        c.intentLabel.includes(q),
    )
  }
  if (langFilter.value !== "all") {
    list = list.filter((c) => c.language === langFilter.value)
  }
  return list
})

// ==================== 工具函数 ====================

const langFlag: Record<BuyerLanguage, string> = {
  id: "🇮🇩",
  th: "🇹🇭",
  vi: "🇻🇳",
  en: "🇬🇧",
  zh: "🇨🇳",
}

const riskBadge: Record<string, { tone: "danger" | "warning" | "neutral" | "success"; label: string }> = {
  critical: { tone: "danger", label: "高危" },
  high: { tone: "danger", label: "高风险" },
  medium: { tone: "warning", label: "中等" },
  low: { tone: "success", label: "低风险" },
}

const statusLabel: Record<ConversationTab, string> = {
  all: "",
  pending_reply: "待回复",
  pending_human: "待人工",
  resolved: "已解决",
}

const skuStatusLabel: Record<string, string> = {
  sufficient: "充足",
  low: "偏低",
  out: "售罄",
}

const skuStatusTone: Record<string, "success" | "warning" | "danger"> = {
  sufficient: "success",
  low: "warning",
  out: "danger",
}
</script>

<template>
  <PageContainer :padded="false">
    <div class="cs-workspace">
      <!-- ==================== 左栏：会话列表 ==================== -->
      <aside :class="['cs-left', { 'cs-left--hidden': showChat }]">
        <div class="cs-left__header">
          <h2 class="cs-left__title">会话工作台</h2>
          <div class="cs-left__tools">
            <SpSelect
              v-model="langFilter"
              :options="langOptions"
              placeholder="语种"
            />
          </div>
        </div>

        <!-- 搜索 -->
        <div class="cs-left__search">
          <SpInput
            v-model="searchQuery"
            placeholder="搜索买家或消息…"
            type="search"
            clearable
          >
            <template #prefix><Search :size="16" /></template>
          </SpInput>
        </div>

        <!-- 页签 -->
        <nav class="cs-tabs" aria-label="会话筛选">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            :class="['cs-tabs__item', { 'cs-tabs__item--active': activeTab === tab.key }]"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
            <span class="cs-tabs__count">{{ tabCount(tab.key) }}</span>
          </button>
        </nav>

        <!-- 会话列表 -->
        <div class="cs-conv-list">
          <button
            v-for="conv in displayConversations"
            :key="conv.id"
            type="button"
            :class="[
              'cs-conv-item',
              { 'cs-conv-item--active': selectedId === conv.id, 'cs-conv-item--unread': conv.unread },
            ]"
            @click="selectConversation(conv.id)"
          >
            <div class="cs-conv-item__avatar">
              <SpAvatar :initials="conv.buyerInitials" :gradient="conv.riskLevel === 'critical' || conv.riskLevel === 'high' ? 'pink' : 'blue'" size="md" />
              <span v-if="conv.unread" class="cs-conv-item__dot" aria-label="未读"></span>
            </div>
            <div class="cs-conv-item__body">
              <div class="cs-conv-item__top">
                <strong>{{ conv.buyerName }}</strong>
                <span class="cs-conv-item__time">{{ conv.lastMessageTime }}</span>
              </div>
              <div class="cs-conv-item__meta">
                <span class="cs-conv-item__lang">
                  {{ langFlag[conv.language] }} {{ conv.languageLabel }}
                </span>
                <SpBadge :tone="riskBadge[conv.riskLevel].tone" dot>
                  {{ conv.intentLabel }}
                </SpBadge>
              </div>
              <p class="cs-conv-item__preview">{{ conv.lastMessage }}</p>
            </div>
            <ChevronDown v-if="selectedId === conv.id" :size="14" class="cs-conv-item__arrow" />
          </button>

          <div v-if="displayConversations.length === 0" class="cs-conv-empty">
            <MessageSquare :size="28" />
            <p>暂无匹配会话</p>
          </div>
        </div>
      </aside>

      <!-- ==================== 中栏：聊天主窗口 ==================== -->
      <main :class="['cs-center', { 'cs-center--visible': showChat }]">
        <!-- 无选中会话时的空状态 -->
        <div v-if="!selectedConversation" class="cs-center__empty">
          <MessageCircle :size="42" />
          <h3>选择会话开始处理</h3>
          <p>从左侧列表中选择一个买家会话</p>
        </div>

        <template v-else>
          <!-- 聊天顶栏 -->
          <header class="cs-chat-header">
            <button type="button" class="cs-chat-header__back" @click="backToList">
              <ArrowLeft :size="19" />
            </button>
            <div class="cs-chat-header__info">
              <div class="cs-chat-header__buyer">
                <strong>{{ selectedConversation.buyerName }}</strong>
                <span class="cs-chat-header__lang">
                  {{ langFlag[selectedConversation.language] }}
                  {{ selectedConversation.languageLabel }}
                </span>
                <SpBadge :tone="riskBadge[selectedConversation.riskLevel].tone" dot>
                  {{ statusLabel[selectedConversation.status] || selectedConversation.intentLabel }}
                </SpBadge>
              </div>
              <p class="cs-chat-header__summary">
                订单 {{ selectedConversation.orderId }} · 意图：{{ selectedConversation.intentLabel }}
                <span v-if="selectedConversation.riskLevel === 'critical' || selectedConversation.riskLevel === 'high'" class="cs-chat-header__risk">
                  · ⚠️ 高风险会话，建议优先处理
                </span>
              </p>
            </div>
            <SpButton
              v-if="selectedConversation.status !== 'resolved'"
              size="sm"
              variant="secondary"
              @click="showTransferInput = !showTransferInput"
            >
              <template #icon><UserCheck :size="16" /></template>
              转人工
            </SpButton>
          </header>

          <!-- 转人工备注输入 -->
          <div v-if="showTransferInput" class="cs-transfer-note">
            <SpInput v-model="transferNote" placeholder="添加处理备注（选填）…" clearable />
            <SpButton size="sm" @click="transferToHuman">确认转人工</SpButton>
            <SpIconButton ariaLabel="取消转人工" size="sm" @click="showTransferInput = false">
              <X :size="16" />
            </SpIconButton>
          </div>

          <!-- 消息流 -->
          <div class="cs-messages">
            <div
              v-for="msg in activeMessages"
              :key="msg.id"
              :class="['cs-msg', `cs-msg--${msg.sender}`]"
            >
              <!-- 买家消息 -->
              <template v-if="msg.sender === 'buyer'">
                <div class="cs-msg__bubble cs-msg__bubble--buyer">
                  <div v-if="msg.originalContent" class="cs-msg__original">
                    <span class="cs-msg__lang-tag">
                      {{ langFlag[msg.language ?? 'id'] }} 原文
                    </span>
                    <p>{{ msg.originalContent }}</p>
                  </div>
                  <div v-if="msg.translatedContent" class="cs-msg__translated">
                    <span class="cs-msg__lang-tag cs-msg__lang-tag--zh">中文翻译</span>
                    <p>{{ msg.translatedContent }}</p>
                  </div>
                  <div v-if="!msg.originalContent && !msg.translatedContent" class="cs-msg__original">
                    <p>{{ msg.content }}</p>
                  </div>
                  <span class="cs-msg__time">{{ msg.timestamp }}</span>
                </div>
              </template>

              <!-- AI 消息（含建议回复） -->
              <template v-else-if="msg.sender === 'ai'">
                <div class="cs-msg__bubble cs-msg__bubble--ai">
                  <div class="cs-msg__ai-label">
                    <Bot :size="14" />
                    <span>AI 自动回复</span>
                  </div>
                  <p>{{ msg.content }}</p>
                  <span class="cs-msg__time">{{ msg.timestamp }}</span>
                </div>

                <!-- AI 建议回复框 -->
                <div v-if="msg.aiSuggestion" class="cs-suggestion">
                  <div class="cs-suggestion__header">
                    <Bot :size="15" />
                    <strong>AI 建议回复</strong>
                    <span class="cs-suggestion__confidence">
                      置信度 {{ msg.aiSuggestion.confidence }}%
                    </span>
                  </div>
                  <p class="cs-suggestion__text">{{ msg.aiSuggestion.reply }}</p>
                  <div class="cs-suggestion__source">
                    <span class="cs-suggestion__source-label">知识依据</span>
                    <strong>{{ msg.aiSuggestion.knowledgeSource }}</strong>
                    <p>"{{ msg.aiSuggestion.knowledgeExcerpt }}"</p>
                  </div>
                  <SpButton size="sm" variant="secondary" @click="replyText = msg.aiSuggestion?.reply ?? ''">
                    <template #icon><CheckCircle2 :size="15" /></template>
                    采用此建议
                  </SpButton>
                </div>
              </template>

              <!-- 人工代理消息 -->
              <template v-else-if="msg.sender === 'agent'">
                <div class="cs-msg__bubble cs-msg__bubble--agent">
                  <div class="cs-msg__agent-label">
                    <UserCheck :size="14" />
                    <span>人工回复</span>
                  </div>
                  <p>{{ msg.content }}</p>
                  <span class="cs-msg__time">{{ msg.timestamp }}</span>
                </div>
              </template>
            </div>
          </div>

          <!-- 底部编辑框 -->
          <div class="cs-composer">
            <SpInput
              v-model="replyText"
              class="cs-composer__input"
              placeholder="输入人工回复…"
              clearable
            />
            <SpButton @click="sendReply" :disabled="!replyText.trim()">
              <template #icon><Send :size="16" /></template>
              模拟发送回复
            </SpButton>
          </div>
        </template>
      </main>

      <!-- ==================== 右栏：上下文面板 ==================== -->
      <aside v-if="activeContext" :class="['cs-right', { 'cs-right--hidden': showChat }]">
        <!-- 关联商品 -->
        <section class="cs-ctx-card">
          <h4 class="cs-ctx-card__title">
            <Package :size="15" /> 关联商品
          </h4>
          <div class="cs-ctx-product">
            <SpAvatar :initials="activeContext.product.imageInitials" gradient="blue" size="lg" />
            <div>
              <strong>{{ activeContext.product.name }}</strong>
              <span>{{ activeContext.product.category }}</span>
              <span class="cs-ctx-product__price">
                ¥{{ activeContext.product.price.toFixed(2) }} {{ activeContext.product.currency }}
              </span>
            </div>
          </div>
          <p class="cs-ctx-shop">{{ activeContext.product.shopName }}</p>
        </section>

        <!-- SKU 库存 -->
        <section class="cs-ctx-card">
          <h4 class="cs-ctx-card__title">
            <Package :size="15" /> SKU 库存状态
          </h4>
          <div class="cs-sku-list">
            <div
              v-for="sku in activeContext.skus"
              :key="sku.sku"
              class="cs-sku-item"
            >
              <div class="cs-sku-item__info">
                <code>{{ sku.sku }}</code>
                <span>{{ sku.variant }}</span>
              </div>
              <div class="cs-sku-item__stock">
                <span>库存 {{ sku.stock }}</span>
                <span v-if="sku.reserved > 0">预留 {{ sku.reserved }}</span>
                <SpBadge :tone="skuStatusTone[sku.status]">
                  {{ skuStatusLabel[sku.status] }}
                </SpBadge>
              </div>
            </div>
          </div>
        </section>

        <!-- 关联订单 -->
        <section class="cs-ctx-card">
          <h4 class="cs-ctx-card__title">
            <Truck :size="15" /> 关联订单
          </h4>
          <div class="cs-ctx-order">
            <div class="cs-ctx-order__head">
              <strong>{{ activeContext.order.id }}</strong>
              <SpBadge :tone="activeContext.order.status === 'delivered' ? 'success' : activeContext.order.status === 'shipped' ? 'info' : 'warning'">
                {{ activeContext.order.statusLabel }}
              </SpBadge>
            </div>
            <p class="cs-ctx-order__amount">
              ¥{{ activeContext.order.amount.toFixed(2) }}
              <span>· {{ activeContext.order.placedAt }}</span>
            </p>
            <ul class="cs-ctx-order__items">
              <li v-for="item in activeContext.order.items" :key="item">{{ item }}</li>
            </ul>
            <p class="cs-ctx-order__buyer">买家：{{ activeContext.order.buyerName }}</p>
          </div>
        </section>

        <!-- 物流轨迹 -->
        <section v-if="activeContext.logistics" class="cs-ctx-card">
          <h4 class="cs-ctx-card__title">
            <Globe :size="15" /> 物流轨迹
          </h4>
          <div class="cs-logistics">
            <p class="cs-logistics__carrier">
              {{ activeContext.logistics.carrier }}
              <code>{{ activeContext.logistics.trackingNumber }}</code>
            </p>
            <div class="cs-logistics__timeline">
              <div
                v-for="(event, idx) in activeContext.logistics.events"
                :key="idx"
                :class="[
                  'cs-logistics__event',
                  { 'cs-logistics__event--active': idx === activeContext.logistics.events.length - 1 },
                ]"
              >
                <span class="cs-logistics__dot" aria-hidden="true"></span>
                <div>
                  <p>{{ event.description }}</p>
                  <span class="cs-logistics__meta">{{ event.time }} · {{ event.location }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </PageContainer>
</template>

<style scoped>
/* ==================== Workspace Layout ==================== */

.cs-workspace {
  display: flex;
  height: calc(100vh - 160px);
  height: calc(100dvh - 160px);
  min-height: 560px;
  overflow: hidden;
}

/* ==================== Left Column: 会话列表 ==================== */

.cs-left {
  display: flex;
  flex-direction: column;
  flex: 0 0 312px;
  width: 312px;
  min-width: 0;
  background: #fafbfc;
  border-right: 1px solid var(--sp-border-soft);
  overflow: hidden;
}

.cs-left__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-3);
  padding: var(--sp-space-5) var(--sp-space-4) var(--sp-space-3);
  flex: 0 0 auto;
}

.cs-left__title {
  font-size: var(--sp-font-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
  color: var(--sp-color-text);
}

.cs-left__search {
  padding: 0 var(--sp-space-4) var(--sp-space-3);
  flex: 0 0 auto;
}

.cs-left__search :deep(.sp-input-field__control) {
  background: #ffffff;
}

/* 页签 */

.cs-tabs {
  display: flex;
  gap: var(--sp-space-1);
  padding: 0 var(--sp-space-4) var(--sp-space-3);
  flex: 0 0 auto;
  overflow-x: auto;
}

.cs-tabs__item {
  display: flex;
  gap: var(--sp-space-1);
  align-items: center;
  flex: 0 0 auto;
  padding: var(--sp-space-2) var(--sp-space-3);
  font-size: var(--sp-font-xs);
  font-weight: 600;
  color: var(--sp-color-text-muted);
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--sp-radius-pill);
  transition: color var(--sp-transition-fast), background var(--sp-transition-fast);
  white-space: nowrap;
}

.cs-tabs__item:hover {
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface-hover);
}

.cs-tabs__item--active {
  color: var(--sp-color-primary);
  background: #ffffff;
  border-color: var(--sp-border-strong);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.cs-tabs__count {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  min-width: 18px;
  text-align: center;
}

.cs-tabs__item--active .cs-tabs__count {
  color: var(--sp-color-primary);
}

/* 会话列表项 */

.cs-conv-list {
  flex: 1 1 auto;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: 0 var(--sp-space-3) var(--sp-space-3);
}

.cs-conv-item {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  width: 100%;
  padding: var(--sp-space-3);
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 14px;
  transition: background var(--sp-transition-fast);
  position: relative;
}

.cs-conv-item:hover {
  background: var(--sp-color-surface-hover);
}

.cs-conv-item--active {
  background: #ffffff;
  border-color: var(--sp-border-strong);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.cs-conv-item--unread .cs-conv-item__preview {
  font-weight: 650;
  color: var(--sp-color-text);
}

.cs-conv-item + .cs-conv-item {
  margin-top: var(--sp-space-1);
}

.cs-conv-item__avatar {
  position: relative;
  flex: 0 0 auto;
}

.cs-conv-item__dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 10px;
  height: 10px;
  background: var(--sp-color-accent-pink);
  border: 2px solid #fafbfc;
  border-radius: var(--sp-radius-pill);
}

.cs-conv-item--active .cs-conv-item__dot {
  border-color: #ffffff;
}

.cs-conv-item__body {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: var(--sp-space-1);
}

.cs-conv-item__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--sp-space-2);
}

.cs-conv-item__top strong {
  font-size: var(--sp-font-sm);
  font-weight: 700;
  color: var(--sp-color-text);
}

.cs-conv-item__time {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  flex: 0 0 auto;
  white-space: nowrap;
}

.cs-conv-item__meta {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  flex-wrap: wrap;
}

.cs-conv-item__lang {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  background: var(--sp-color-surface-muted);
  padding: 1px 6px;
  border-radius: var(--sp-radius-pill);
}

.cs-conv-item__preview {
  margin: 0;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cs-conv-item__arrow {
  flex: 0 0 auto;
  color: var(--sp-color-primary);
  margin-top: 10px;
}

.cs-conv-empty {
  display: grid;
  place-items: center;
  padding: var(--sp-space-10) var(--sp-space-4);
  color: var(--sp-color-text-muted);
  gap: var(--sp-space-2);
}

.cs-conv-empty p {
  margin: 0;
  font-size: var(--sp-font-sm);
}

/* ==================== Center: 聊天窗口 ==================== */

.cs-center {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: #ffffff;
}

.cs-center__empty {
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--sp-space-3);
  flex: 1;
  color: var(--sp-color-text-muted);
}

.cs-center__empty h3 {
  margin: 0;
  color: var(--sp-color-text);
}

.cs-center__empty p {
  margin: 0;
  font-size: var(--sp-font-sm);
}

/* 聊天顶栏 */

.cs-chat-header {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
  padding: var(--sp-space-4) var(--sp-space-5);
  border-bottom: 1px solid var(--sp-border-soft);
  flex: 0 0 auto;
}

.cs-chat-header__back {
  display: none;
  flex: 0 0 auto;
  padding: var(--sp-space-1);
  color: var(--sp-color-text-secondary);
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: var(--sp-radius-control);
  margin-top: 2px;
}

.cs-chat-header__info {
  flex: 1;
  min-width: 0;
}

.cs-chat-header__buyer {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  flex-wrap: wrap;
}

.cs-chat-header__buyer strong {
  font-size: var(--sp-font-md);
  font-weight: 700;
}

.cs-chat-header__lang {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  background: var(--sp-color-surface-muted);
  padding: 1px 7px;
  border-radius: var(--sp-radius-pill);
}

.cs-chat-header__summary {
  margin: var(--sp-space-1) 0 0;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
}

.cs-chat-header__risk {
  color: var(--sp-color-accent-pink);
  font-weight: 600;
}

/* 转人工备注 */

.cs-transfer-note {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  padding: var(--sp-space-3) var(--sp-space-5);
  background: color-mix(in srgb, var(--sp-color-accent-pink) 6%, #ffffff);
  border-bottom: 1px solid var(--sp-border-soft);
  flex: 0 0 auto;
}

.cs-transfer-note > :first-child {
  flex: 1;
}

/* 消息流 */

.cs-messages {
  flex: 1 1 auto;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: var(--sp-space-5);
  display: grid;
  gap: var(--sp-space-5);
  align-content: start;
}

.cs-msg {
  display: grid;
  gap: var(--sp-space-3);
  max-width: 82%;
}

.cs-msg--buyer {
  justify-self: start;
}

.cs-msg--ai,
.cs-msg--agent {
  justify-self: end;
}

.cs-msg__bubble {
  padding: var(--sp-space-4);
  border-radius: 18px;
  font-size: var(--sp-font-sm);
  line-height: 1.6;
  position: relative;
}

.cs-msg__bubble--buyer {
  background: #f3f4f6;
  color: var(--sp-color-text);
  border-bottom-left-radius: 6px;
}

.cs-msg__bubble--ai {
  background: color-mix(in srgb, var(--sp-color-accent-blue) 6%, #ffffff);
  color: var(--sp-color-text);
  border: 1px solid var(--sp-color-accent-blue-soft);
  border-bottom-right-radius: 6px;
}

.cs-msg__bubble--agent {
  background: color-mix(in srgb, var(--sp-color-primary) 8%, #ffffff);
  color: var(--sp-color-text);
  border: 1px solid color-mix(in srgb, var(--sp-color-primary) 14%, transparent);
  border-bottom-right-radius: 6px;
}

.cs-msg__bubble p {
  margin: 0;
}

.cs-msg__original,
.cs-msg__translated {
  display: grid;
  gap: var(--sp-space-1);
}

.cs-msg__translated {
  margin-top: var(--sp-space-3);
  padding-top: var(--sp-space-3);
  border-top: 1px dashed var(--sp-border-soft);
}

.cs-msg__lang-tag {
  font-size: 10px;
  font-weight: 700;
  color: var(--sp-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.cs-msg__lang-tag--zh {
  color: var(--sp-color-accent-blue);
}

.cs-msg__time {
  display: block;
  margin-top: var(--sp-space-2);
  font-size: 11px;
  color: var(--sp-color-text-muted);
  text-align: right;
}

.cs-msg__ai-label,
.cs-msg__agent-label {
  display: flex;
  gap: var(--sp-space-1);
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--sp-color-accent-blue);
  margin-bottom: var(--sp-space-2);
}

.cs-msg__agent-label {
  color: var(--sp-color-primary);
}

/* AI 建议回复框 */

.cs-suggestion {
  background: #ffffff;
  border: 1px solid var(--sp-color-accent-blue-soft);
  border-radius: 18px;
  padding: var(--sp-space-4);
  display: grid;
  gap: var(--sp-space-3);
}

.cs-suggestion__header {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  color: var(--sp-color-accent-blue);
}

.cs-suggestion__header strong {
  font-size: var(--sp-font-sm);
  color: var(--sp-color-text);
}

.cs-suggestion__confidence {
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  color: var(--sp-color-accent-blue);
  background: var(--sp-color-accent-blue-soft);
  padding: 2px 8px;
  border-radius: var(--sp-radius-pill);
}

.cs-suggestion__text {
  margin: 0;
  font-size: var(--sp-font-sm);
  line-height: 1.6;
  color: var(--sp-color-text);
}

.cs-suggestion__source {
  background: var(--sp-color-surface-muted);
  border-radius: 12px;
  padding: var(--sp-space-3);
}

.cs-suggestion__source-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--sp-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.cs-suggestion__source strong {
  display: block;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text);
  margin-top: 2px;
}

.cs-suggestion__source p {
  margin: var(--sp-space-1) 0 0;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
  font-style: italic;
  line-height: 1.5;
}

/* 底部编辑框 */

.cs-composer {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  padding: var(--sp-space-4) var(--sp-space-5);
  border-top: 1px solid var(--sp-border-soft);
  flex: 0 0 auto;
}

.cs-composer__input {
  flex: 1;
  min-width: 0;
}

.cs-composer__input :deep(.sp-input-field__control) {
  border-radius: var(--sp-radius-control);
}

/* ==================== Right Column: 上下文面板 ==================== */

.cs-right {
  flex: 0 0 340px;
  width: 340px;
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  background: #fafbfc;
  border-left: 1px solid var(--sp-border-soft);
  padding: var(--sp-space-4);
  display: grid;
  gap: var(--sp-space-4);
  align-content: start;
}

.cs-ctx-card {
  background: #ffffff;
  border: 1px solid var(--sp-border-soft);
  border-radius: 16px;
  padding: var(--sp-space-4);
  display: grid;
  gap: var(--sp-space-3);
}

.cs-ctx-card__title {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  font-size: var(--sp-font-xs);
  font-weight: 700;
  color: var(--sp-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

/* 商品 */

.cs-ctx-product {
  display: flex;
  gap: var(--sp-space-3);
  align-items: flex-start;
}

.cs-ctx-product > div {
  display: grid;
  gap: 2px;
}

.cs-ctx-product strong {
  font-size: var(--sp-font-sm);
  font-weight: 700;
}

.cs-ctx-product span {
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
}

.cs-ctx-product__price {
  font-weight: 700 !important;
  color: var(--sp-color-accent-pink) !important;
  font-size: var(--sp-font-sm) !important;
  margin-top: var(--sp-space-1);
}

.cs-ctx-shop {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  margin: 0;
  padding: var(--sp-space-2) var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-pill);
  justify-self: start;
}

/* SKU */

.cs-sku-list {
  display: grid;
  gap: var(--sp-space-2);
}

.cs-sku-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-space-2);
  padding: var(--sp-space-2) var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border-radius: 10px;
}

.cs-sku-item__info {
  display: grid;
  gap: 1px;
}

.cs-sku-item__info code {
  font-size: 11px;
  font-weight: 700;
  color: var(--sp-color-primary);
}

.cs-sku-item__info span {
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

.cs-sku-item__stock {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  font-size: 11px;
  color: var(--sp-color-text-muted);
  text-align: right;
}

/* 订单 */

.cs-ctx-order {
  display: grid;
  gap: var(--sp-space-2);
}

.cs-ctx-order__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cs-ctx-order__head strong {
  font-size: var(--sp-font-sm);
  font-weight: 700;
}

.cs-ctx-order__amount {
  margin: 0;
  font-size: var(--sp-font-md);
  font-weight: 700;
  color: var(--sp-color-text);
}

.cs-ctx-order__amount span {
  font-size: var(--sp-font-xs);
  font-weight: 400;
  color: var(--sp-color-text-muted);
}

.cs-ctx-order__items {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: var(--sp-space-1);
}

.cs-ctx-order__items li {
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-secondary);
  padding-left: var(--sp-space-3);
  border-left: 2px solid var(--sp-color-accent-blue);
}

.cs-ctx-order__buyer {
  margin: 0;
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

/* 物流 */

.cs-logistics__carrier {
  margin: 0;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-secondary);
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  flex-wrap: wrap;
}

.cs-logistics__carrier code {
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

.cs-logistics__timeline {
  display: grid;
  gap: 0;
  position: relative;
}

.cs-logistics__event {
  display: flex;
  gap: var(--sp-space-3);
  padding: var(--sp-space-2) 0;
  position: relative;
}

.cs-logistics__event::before {
  content: "";
  position: absolute;
  left: 5px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--sp-border-soft);
}

.cs-logistics__event:last-child::before {
  bottom: 50%;
}

.cs-logistics__dot {
  width: 11px;
  height: 11px;
  flex: 0 0 auto;
  border-radius: var(--sp-radius-pill);
  background: var(--sp-color-surface-muted);
  border: 2px solid var(--sp-border-strong);
  position: relative;
  z-index: 1;
  margin-top: 3px;
}

.cs-logistics__event--active .cs-logistics__dot {
  background: var(--sp-color-accent-blue);
  border-color: var(--sp-color-accent-blue);
}

.cs-logistics__event p {
  margin: 0;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text);
}

.cs-logistics__event--active p {
  font-weight: 650;
}

.cs-logistics__meta {
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

/* ==================== Responsive ==================== */

@media (max-width: 1279px) {
  .cs-right {
    flex: 0 0 300px;
    width: 300px;
  }

  .cs-left {
    flex: 0 0 280px;
    width: 280px;
  }
}

@media (max-width: 1023px) {
  .cs-left--hidden {
    display: none;
  }

  .cs-center {
    display: none;
  }

  .cs-center--visible {
    display: flex;
  }

  .cs-right--hidden {
    display: none;
  }

  .cs-chat-header__back {
    display: block;
  }

  .cs-left {
    flex: 1 1 auto;
    width: 100%;
  }

  .cs-right {
    flex: 1 1 auto;
    width: 100%;
  }

  .cs-msg {
    max-width: 92%;
  }
}

@media (max-width: 767px) {
  .cs-workspace {
    height: calc(100vh - 120px);
    height: calc(100dvh - 120px);
    min-height: 0;
  }

  .cs-msg {
    max-width: 100%;
  }

  .cs-chat-header {
    padding: var(--sp-space-3);
  }

  .cs-messages {
    padding: var(--sp-space-3);
  }

  .cs-composer {
    padding: var(--sp-space-3);
    flex-wrap: wrap;
  }

  .cs-composer__input {
    width: 100%;
    flex: auto;
  }
}
</style>
