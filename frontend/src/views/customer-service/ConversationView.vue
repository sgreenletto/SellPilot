<script setup lang="ts">
import { Bot, FileText, Package, Search, Send, Truck } from "@lucide/vue";
import { ElMessage } from "element-plus";
import { nextTick, ref } from "vue";

import { fetchLogistics, fetchOrder, fetchProduct } from "@/api/customer-service";
import { ragQA } from "@/api/knowledge-base";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpInput from "@/components/base/SpInput.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import type { Logistics, Order, Product } from "@/types/commerce";

// ==================== 会话消息 ====================

interface ChatMsg {
  id: number;
  role: "buyer" | "ai";
  text: string;
  sources?: { score: number; source_doc: string; category: string; fragment: string }[];
  time: string;
}

const messages = ref<ChatMsg[]>([]);
const inputText = ref("");
const sending = ref(false);
const categoryFilter = ref("");
let msgId = 0;

function timeNow() {
  return new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

async function sendMsg() {
  const q = inputText.value.trim();
  if (!q || sending.value) return;
  const userMsg: ChatMsg = { id: ++msgId, role: "buyer", text: q, time: timeNow() };
  messages.value.push(userMsg);
  inputText.value = "";
  sending.value = true;
  await nextTick();
  scrollBottom();

  try {
    const res = await ragQA({ question: q, top_k: 3, category: categoryFilter.value || undefined });
    const aiMsg: ChatMsg = {
      id: ++msgId,
      role: "ai",
      text: res.answer,
      sources: res.sources,
      time: timeNow(),
    };
    messages.value.push(aiMsg);
  } catch (e: unknown) {
    const err = e instanceof Error ? e.message : "未知错误";
    messages.value.push({ id: ++msgId, role: "ai", text: `请求失败：${err}`, time: timeNow() });
    ElMessage.error(`AI 回复失败：${err}`);
  } finally {
    sending.value = false;
    await nextTick();
    scrollBottom();
  }
}

function scrollBottom() {
  const el = document.getElementById("chat-msgs");
  if (el) el.scrollTop = el.scrollHeight;
}

const catOptions = [
  { label: "全部知识", value: "" },
  { label: "商品知识", value: "product" },
  { label: "客服FAQ", value: "faq" },
  { label: "用户评论", value: "review" },
];

// ==================== 上下文面板 ====================

const productId = ref("");
const orderId = ref("");
const ctxProduct = ref<Product | null>(null);
const ctxOrder = ref<Order | null>(null);
const ctxLogistics = ref<Logistics | null>(null);
const ctxLoading = ref(false);

async function loadContext() {
  const pid = productId.value.trim();
  const oid = orderId.value.trim();
  if (!pid && !oid) return;
  ctxLoading.value = true;
  ctxProduct.value = null;
  ctxOrder.value = null;
  ctxLogistics.value = null;
  try {
    if (pid) ctxProduct.value = await fetchProduct(pid).catch(() => null);
    if (oid) {
      ctxOrder.value = await fetchOrder(oid).catch(() => null);
      ctxLogistics.value = await fetchLogistics(oid).catch(() => null);
    }
  } finally {
    ctxLoading.value = false;
  }
}

const orderStatusTone = (s: string) =>
  s === "delivered" || s === "completed" ? "success" : s === "shipped" ? "info" : "warning";
</script>

<template>
  <PageContainer :padded="false">
    <div class="cs-workspace">
      <!-- ===== 左：聊天区 ===== -->
      <main class="cs-chat">
        <header class="cs-chat-hd">
          <Bot :size="20" /><strong>模拟买家咨询</strong>
          <span class="cs-hint">输入买家问题，AI 自动检索知识库回复</span>
        </header>

        <div id="chat-msgs" class="cs-msgs">
          <div v-if="messages.length === 0" class="cs-empty">
            <Bot :size="42" />
            <p>输入买家问题开始模拟</p>
            <span>AI 将从商品知识、用户评论、客服FAQ 中检索回答</span>
          </div>
          <div
            v-for="m in messages"
            :key="m.id"
            :class="['cs-bubble', m.role === 'buyer' ? 'cs-bubble--buyer' : 'cs-bubble--ai']"
          >
            <div class="cs-bubble__label">{{ m.role === "buyer" ? "🧑 买家" : "🤖 AI 客服" }}</div>
            <div class="cs-bubble__text">{{ m.text }}</div>
            <div v-if="m.sources && m.sources.length" class="cs-sources">
              <div v-for="(s, i) in m.sources" :key="i" class="cs-src">
                <FileText :size="12" /><span>{{ s.source_doc || "来源未知" }}</span>
                <SpBadge :tone="s.score >= 0.5 ? 'success' : 'warning'"
                  >{{ Math.round(s.score * 100) }}%</SpBadge
                >
                <span class="cs-src__frag"
                  >{{ s.fragment.slice(0, 150) }}{{ s.fragment.length > 150 ? "..." : "" }}</span
                >
              </div>
            </div>
            <span class="cs-bubble__time">{{ m.time }}</span>
          </div>
          <div v-if="sending" class="cs-bubble cs-bubble--ai">
            <Bot :size="14" class="cs-typing" /> AI 思考中…
          </div>
        </div>

        <div class="cs-composer">
          <SpSelect
            v-model="categoryFilter"
            :options="catOptions"
            placeholder="知识范围"
            style="width: 130px"
          />
          <SpInput
            v-model="inputText"
            placeholder="输入买家问题，如：电池不耐用怎么办？"
            class="cs-input"
            clearable
            @keyup.enter="sendMsg"
          >
            <template #prefix><Search :size="15" /></template>
          </SpInput>
          <SpButton :loading="sending" @click="sendMsg"
            ><template #icon><Send :size="15" /></template>发送</SpButton
          >
        </div>
      </main>

      <!-- ===== 右：上下文面板 ===== -->
      <aside class="cs-ctx">
        <div class="cs-ctx-card">
          <h4><Package :size="15" /> 关联商品</h4>
          <SpInput v-model="productId" placeholder="商品 ID，如 PROD0001" clearable />
          <h4 style="margin-top: 12px"><Truck :size="15" /> 关联订单</h4>
          <SpInput v-model="orderId" placeholder="订单 ID，如 ORD000252" clearable />
          <SpButton size="sm" :loading="ctxLoading" @click="loadContext" style="margin-top: 8px"
            >查询上下文</SpButton
          >
        </div>

        <div v-if="ctxProduct" class="cs-ctx-card">
          <h4><Package :size="15" /> {{ ctxProduct.title }}</h4>
          <p>{{ ctxProduct.category_name }} · {{ ctxProduct.site }}</p>
          <p>
            <strong>¥{{ Number(ctxProduct.price).toFixed(2) }}</strong> {{ ctxProduct.currency }} ·
            销量 {{ ctxProduct.sales_count }} · 评分 {{ ctxProduct.rating }}
          </p>
        </div>

        <div v-if="ctxOrder" class="cs-ctx-card">
          <h4><Truck :size="15" /> {{ ctxOrder.order_id }}</h4>
          <SpBadge :tone="orderStatusTone(ctxOrder.order_status)">{{
            ctxOrder.order_status
          }}</SpBadge>
          <p>
            ¥{{ Number(ctxOrder.total_amount).toFixed(2) }} {{ ctxOrder.currency }} ·
            {{ ctxOrder.created_at?.slice(0, 10) }}
          </p>
        </div>

        <div v-if="ctxLogistics" class="cs-ctx-card">
          <h4>物流</h4>
          <p>{{ ctxLogistics.carrier }} · {{ ctxLogistics.tracking_number }}</p>
          <div v-for="(t, i) in ctxLogistics.tracks" :key="i" class="cs-track">
            {{ t.event_time?.slice(5, 16) }} {{ t.description }} @{{ t.location }}
          </div>
        </div>
      </aside>
    </div>
  </PageContainer>
</template>

<style scoped>
.cs-workspace {
  display: flex;
  height: calc(100vh - 130px);
  min-height: 500px;
  overflow: hidden;
}
.cs-chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: #fff;
}
.cs-chat-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  font-size: 15px;
}
.cs-hint {
  margin-left: auto;
  font-size: 12px;
  color: #999;
}
.cs-msgs {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: grid;
  gap: 12px;
  align-content: start;
}
.cs-empty {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 4px;
  padding: 60px 0;
  color: #ccc;
}
.cs-empty p {
  margin: 0;
  font-weight: 600;
  color: #999;
}
.cs-empty span {
  font-size: 12px;
}
.cs-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
}
.cs-bubble--buyer {
  justify-self: end;
  background: #0b234a;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.cs-bubble--ai {
  justify-self: start;
  background: #f3f4f6;
  border-bottom-left-radius: 4px;
}
.cs-bubble__label {
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 4px;
  opacity: 0.7;
}
.cs-bubble__text {
  white-space: pre-wrap;
}
.cs-bubble__time {
  display: block;
  font-size: 10px;
  opacity: 0.5;
  margin-top: 4px;
  text-align: right;
}
.cs-sources {
  margin-top: 8px;
  display: grid;
  gap: 4px;
}
.cs-src {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 4px 8px;
  align-items: center;
  font-size: 11px;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}
.cs-src__frag {
  grid-column: 1/-1;
  color: #666;
  font-size: 11px;
}
.cs-composer {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #eee;
  align-items: center;
}
.cs-input {
  flex: 1;
}
.cs-typing {
  animation: cs-pulse 1s infinite;
}
@keyframes cs-pulse {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 1;
  }
}

.cs-ctx {
  width: 300px;
  overflow-y: auto;
  background: #fafbfc;
  border-left: 1px solid #eee;
  padding: 12px;
  display: grid;
  gap: 10px;
  align-content: start;
}
.cs-ctx-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 12px;
  display: grid;
  gap: 4px;
}
.cs-ctx-card h4 {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin: 0;
}
.cs-ctx-card p {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.cs-track {
  font-size: 11px;
  color: #999;
  padding: 2px 0;
  border-bottom: 1px solid #f5f5f5;
}

@media (max-width: 900px) {
  .cs-ctx {
    display: none;
  }
  .cs-bubble {
    max-width: 95%;
  }
}
</style>
