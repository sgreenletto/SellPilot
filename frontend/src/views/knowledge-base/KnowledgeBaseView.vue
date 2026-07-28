<script setup lang="ts">
import {
  BookOpen,
  Bot,
  CheckCircle2,
  Clock,
  Edit3,
  ExternalLink,
  FileText,
  FileWarning,
  LoaderCircle,
  PauseCircle,
  Plus,
  RotateCw,
  Search,
  Trash2,
  Upload,
  XCircle,
  Zap,
} from "@lucide/vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { computed, ref } from "vue"

import SpBadge from "@/components/base/SpBadge.vue"
import SpButton from "@/components/base/SpButton.vue"
import SpIconButton from "@/components/base/SpIconButton.vue"
import SpInput from "@/components/base/SpInput.vue"
import PageContainer from "@/components/layout/PageContainer.vue"
import {
  knowledgeEntries,
  mockRetrievalResults,
  uploadedDocuments,
} from "@/mocks/knowledge-base"
import type {
  DocParseStatus,
  KnowledgeCategory,
  KnowledgeEntry,
  RetrievalResult,
} from "@/types/knowledge-base"

// ==================== 1. 知识条目管理 ====================

const categoryTabs: { key: KnowledgeCategory | "all"; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "product", label: "商品知识" },
  { key: "faq", label: "FAQ" },
  { key: "policy", label: "店铺政策" },
  { key: "logistics", label: "物流规则" },
]

const activeCategory = ref<KnowledgeCategory | "all">("all")
const entrySearch = ref("")

const filteredEntries = computed(() => {
  let list = knowledgeEntries
  if (activeCategory.value !== "all") {
    list = list.filter((e) => e.category === activeCategory.value)
  }
  if (entrySearch.value.trim()) {
    const q = entrySearch.value.trim().toLowerCase()
    list = list.filter(
      (e) =>
        e.title.toLowerCase().includes(q) ||
        e.tags.some((t) => t.toLowerCase().includes(q)) ||
        e.content.toLowerCase().includes(q),
    )
  }
  return list
})

const categoryLabel: Record<string, string> = {
  product: "商品知识",
  faq: "FAQ",
  policy: "店铺政策",
  logistics: "物流规则",
}

function toggleEntryStatus(entry: KnowledgeEntry) {
  const newStatus = entry.status === "active" ? "inactive" : "active"
  const action = newStatus === "active" ? "启用" : "停用"
  ElMessage.success(`已${action}知识条目「${entry.title}」`)
  entry.status = newStatus
}

function editEntry(entry: KnowledgeEntry) {
  ElMessage.info(`编辑「${entry.title}」—— 模拟打开编辑弹窗`)
}

function deleteEntry(entry: KnowledgeEntry) {
  ElMessageBox.confirm(`确定要删除「${entry.title}」吗？此操作不可恢复。`, "确认删除", {
    confirmButtonText: "删除",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(() => {
      const idx = knowledgeEntries.findIndex((e) => e.id === entry.id)
      if (idx !== -1) knowledgeEntries.splice(idx, 1)
      ElMessage.success(`已删除「${entry.title}」`)
    })
    .catch(() => {})
}

function addEntry() {
  ElMessage.info("模拟打开新增知识条目弹窗")
}

// ==================== 2. 文档上传与解析 ====================

const uploading = ref(false)
const uploadProgress = ref(0)

function triggerUpload() {
  if (uploading.value) return
  uploading.value = true
  uploadProgress.value = 0
  const interval = setInterval(() => {
    uploadProgress.value += Math.random() * 18
    if (uploadProgress.value >= 100) {
      uploadProgress.value = 100
      clearInterval(interval)
      uploading.value = false
      ElMessage.success("文档上传完成，已加入解析队列")
    }
  }, 300)
}

const parseStatusBadge: Record<
  DocParseStatus,
  { tone: "info" | "success" | "warning" | "danger"; label: string }
> = {
  pending: { tone: "info", label: "排队中" },
  parsing: { tone: "warning", label: "解析中" },
  indexed: { tone: "success", label: "已建索引" },
  failed: { tone: "danger", label: "解析失败" },
}

const parseStatusIcon: Record<DocParseStatus, typeof CheckCircle2> = {
  pending: Clock,
  parsing: LoaderCircle,
  indexed: CheckCircle2,
  failed: XCircle,
}

const fileTypeIcon: Record<string, typeof FileText> = {
  pdf: FileText,
  markdown: FileText,
  txt: FileWarning,
}

// ==================== 3. 检索测试 ====================

const queryText = ref("")
const searching = ref(false)
const retrievalResults = ref<RetrievalResult[]>([])
const hasSearched = ref(false)

function runRetrieval() {
  const q = queryText.value.trim()
  if (!q) {
    ElMessage.warning("请输入测试问题")
    return
  }
  searching.value = true
  retrievalResults.value = []
  setTimeout(() => {
    retrievalResults.value = mockRetrievalResults.map((r) => ({
      ...r,
      score: Math.round((r.score * (0.8 + Math.random() * 0.2)) * 100) / 100,
    }))
    searching.value = false
    hasSearched.value = true
    ElMessage.success(`检索完成，返回 ${retrievalResults.value.length} 条匹配片段`)
  }, 800 + Math.random() * 600)
}

const scoreTone = (s: number) => {
  if (s >= 0.85) return "success"
  if (s >= 0.6) return "warning"
  return "danger"
}
</script>

<template>
  <PageContainer>
    <div class="kb-page">
      <!-- 后端尚未提供知识库 API，当前使用本地 Mock 数据 -->
      <div class="kb-mock-notice">
        <SpBadge tone="warning" dot>本地 Mock 数据</SpBadge>
        <span>知识库 API 尚未在后端实现，当前展示为本地模拟数据。接入后端后将替换为真实检索结果。</span>
      </div>

      <!-- ==================== 1. 知识条目管理 ==================== -->
      <section class="kb-section">
        <div class="kb-section__head">
          <h2><BookOpen :size="22" /> 知识条目管理</h2>
          <SpButton size="sm" @click="addEntry">
            <template #icon><Plus :size="16" /></template>
            新增知识条目
          </SpButton>
        </div>

        <!-- 分类页签 + 搜索 -->
        <div class="kb-toolbar">
          <nav class="kb-tabs" aria-label="分类筛选">
            <button
              v-for="tab in categoryTabs"
              :key="tab.key"
              type="button"
              :class="['kb-tabs__item', { 'kb-tabs__item--active': activeCategory === tab.key }]"
              @click="activeCategory = tab.key"
            >
              {{ tab.label }}
              <span class="kb-tabs__count">
                {{ tab.key === 'all' ? knowledgeEntries.length : knowledgeEntries.filter(e => e.category === tab.key).length }}
              </span>
            </button>
          </nav>
          <SpInput
            v-model="entrySearch"
            class="kb-search"
            placeholder="搜索标题或标签…"
            type="search"
            clearable
          >
            <template #prefix><Search :size="15" /></template>
          </SpInput>
        </div>

        <!-- 条目列表 -->
        <div class="kb-table-wrap">
          <table class="kb-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>分类</th>
                <th>标签</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in filteredEntries" :key="entry.id">
                <td>
                  <div class="kb-table__title">
                    <strong>{{ entry.title }}</strong>
                    <small>{{ entry.source }}</small>
                  </div>
                </td>
                <td>
                  <SpBadge tone="info">{{ categoryLabel[entry.category] }}</SpBadge>
                </td>
                <td>
                  <div class="kb-table__tags">
                    <span v-for="tag in entry.tags.slice(0, 3)" :key="tag" class="kb-tag">{{ tag }}</span>
                    <span v-if="entry.tags.length > 3" class="kb-tag kb-tag--more">+{{ entry.tags.length - 3 }}</span>
                  </div>
                </td>
                <td>
                  <SpBadge :tone="entry.status === 'active' ? 'success' : 'neutral'" dot>
                    {{ entry.status === 'active' ? '激活' : '停用' }}
                  </SpBadge>
                </td>
                <td class="kb-table__date">{{ entry.updatedAt }}</td>
                <td>
                  <div class="kb-table__actions">
                    <SpIconButton ariaLabel="编辑" size="sm" @click="editEntry(entry)">
                      <Edit3 :size="15" />
                    </SpIconButton>
                    <SpIconButton
                      :ariaLabel="entry.status === 'active' ? '停用' : '启用'"
                      size="sm"
                      @click="toggleEntryStatus(entry)"
                    >
                      <PauseCircle v-if="entry.status === 'active'" :size="15" />
                      <RotateCw v-else :size="15" />
                    </SpIconButton>
                    <SpIconButton ariaLabel="删除" size="sm" @click="deleteEntry(entry)">
                      <Trash2 :size="15" />
                    </SpIconButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="filteredEntries.length === 0" class="kb-empty">
            <FileText :size="32" />
            <p>暂无匹配的知识条目</p>
          </div>
        </div>
      </section>

      <!-- ==================== 2. 文档上传与解析 ==================== -->
      <section class="kb-section">
        <div class="kb-section__head">
          <h2><Upload :size="22" /> 文档上传与解析</h2>
        </div>

        <div class="kb-upload-grid">
          <!-- 上传区域 -->
          <div class="kb-upload-zone" @click="triggerUpload">
            <Upload :size="32" class="kb-upload-zone__icon" />
            <strong>点击上传文档</strong>
            <span>支持 PDF、Markdown、TXT 格式，单文件不超过 10 MB</span>
            <div v-if="uploading" class="kb-upload-zone__progress">
              <LoaderCircle :size="15" class="kb-upload-zone__spinner" />
              <span>上传中 {{ Math.round(uploadProgress) }}%</span>
              <progress :value="uploadProgress" max="100"></progress>
            </div>
          </div>

          <!-- 文档解析状态列表 -->
          <div class="kb-doc-list">
            <p class="kb-doc-list__label">解析状态</p>
            <div class="kb-doc-items">
              <div
                v-for="doc in uploadedDocuments"
                :key="doc.id"
                :class="['kb-doc-item', `kb-doc-item--${doc.parseStatus}`]"
              >
                <span class="kb-doc-item__icon">
                  <component :is="fileTypeIcon[doc.type]" :size="18" />
                </span>
                <div class="kb-doc-item__info">
                  <strong>{{ doc.name }}</strong>
                  <span>{{ doc.type.toUpperCase() }} · {{ doc.size }}</span>
                  <span class="kb-doc-item__time">{{ doc.uploadedAt }}</span>
                </div>
                <div class="kb-doc-item__status">
                  <!-- 解析中显示进度条 -->
                  <template v-if="doc.parseStatus === 'parsing'">
                    <progress :value="doc.progress" max="100"></progress>
                    <span>{{ doc.progress }}%</span>
                  </template>
                  <!-- 其他状态 -->
                  <template v-else>
                    <SpBadge :tone="parseStatusBadge[doc.parseStatus].tone" dot>
                      {{ parseStatusBadge[doc.parseStatus].label }}
                    </SpBadge>
                    <span v-if="doc.parseStatus === 'indexed' && doc.chunks" class="kb-doc-item__chunks">
                      {{ doc.chunks }} 个向量块
                    </span>
                  </template>
                </div>
                <!-- 失败重试 -->
                <SpIconButton
                  v-if="doc.parseStatus === 'failed'"
                  ariaLabel="重新解析"
                  size="sm"
                  :title="doc.errorMessage"
                >
                  <RotateCw :size="14" />
                </SpIconButton>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ==================== 3. 检索测试与召回验证 ==================== -->
      <section class="kb-section">
        <div class="kb-section__head">
          <h2><Zap :size="22" /> 检索测试与召回验证</h2>
        </div>

        <!-- 搜索栏 -->
        <div class="kb-retrieval-bar">
          <SpInput
            v-model="queryText"
            class="kb-retrieval-bar__input"
            placeholder="输入测试问题，例如：耳机电池不耐用怎么办？"
            clearable
            @keyup.enter="runRetrieval"
          >
            <template #prefix><Search :size="16" /></template>
          </SpInput>
          <SpButton :loading="searching" @click="runRetrieval">
            <template #icon><Zap :size="16" /></template>
            检索
          </SpButton>
        </div>

        <!-- 检索结果 -->
        <div v-if="hasSearched" class="kb-retrieval-results">
          <p class="kb-retrieval-results__summary">
            <template v-if="retrievalResults.length > 0">
              共召回 <strong>{{ retrievalResults.length }}</strong> 条匹配片段
            </template>
            <template v-else>
              未找到相关片段，请尝试更换查询关键词
            </template>
          </p>

          <div
            v-for="(result, idx) in retrievalResults"
            :key="result.id"
            class="kb-result-item"
          >
            <div class="kb-result-item__head">
              <span class="kb-result-item__rank">#{{ idx + 1 }}</span>
              <span
                :class="['kb-result-item__score', `kb-result-item__score--${scoreTone(result.score)}`]"
              >
                匹配度 {{ Math.round(result.score * 100) }}%
              </span>
              <SpBadge tone="info">{{ categoryLabel[result.sourceCategory] }}</SpBadge>
            </div>
            <blockquote class="kb-result-item__fragment">
              "{{ result.fragment }}"
            </blockquote>
            <div class="kb-result-item__source">
              <FileText :size="13" />
              <span>{{ result.sourceDoc }}</span>
              <span class="kb-result-item__chunk">· Chunk #{{ result.chunkIndex }}</span>
              <SpButton size="sm" variant="ghost" class="kb-result-item__view">
                <template #icon><ExternalLink :size="13" /></template>
                查看原文
              </SpButton>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="kb-retrieval-empty">
          <Bot :size="36" />
          <p>输入测试问题，验证知识库检索效果</p>
          <span>基于向量相似度匹配，返回 Top-K 召回片段与来源引用</span>
        </div>
      </section>
    </div>
  </PageContainer>
</template>

<style scoped>
/* ==================== Page Layout ==================== */

.kb-page {
  display: grid;
  gap: var(--sp-space-6);
  min-width: 0;
}

.kb-mock-notice {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  padding: var(--sp-space-3) var(--sp-space-5);
  background: color-mix(in srgb, var(--sp-color-warning) 8%, #ffffff);
  border: 1px solid color-mix(in srgb, var(--sp-color-warning) 20%, transparent);
  border-radius: 14px;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-secondary);
}

/* ==================== Section Shared ==================== */

.kb-section {
  background: #ffffff;
  border: 1px solid rgba(62, 79, 105, 0.06);
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(64, 82, 112, 0.06);
  padding: var(--sp-space-6);
  min-width: 0;
}

.kb-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-space-4);
  margin-bottom: var(--sp-space-5);
}

.kb-section__head h2 {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  font-size: var(--sp-font-md);
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
}

/* ==================== Toolbar ==================== */

.kb-toolbar {
  display: flex;
  gap: var(--sp-space-4);
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sp-space-5);
  flex-wrap: wrap;
}

.kb-tabs {
  display: flex;
  gap: var(--sp-space-1);
  flex-wrap: wrap;
}

.kb-tabs__item {
  display: flex;
  gap: var(--sp-space-1);
  align-items: center;
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

.kb-tabs__item:hover {
  color: var(--sp-color-text-secondary);
  background: var(--sp-color-surface-muted);
}

.kb-tabs__item--active {
  color: var(--sp-color-primary);
  background: color-mix(in srgb, var(--sp-color-primary) 7%, transparent);
  border-color: color-mix(in srgb, var(--sp-color-primary) 12%, transparent);
}

.kb-tabs__count {
  font-size: 10px;
  color: var(--sp-color-text-muted);
  min-width: 16px;
  text-align: center;
}

.kb-tabs__item--active .kb-tabs__count {
  color: var(--sp-color-primary);
}

.kb-search {
  width: 220px;
}

.kb-search :deep(.sp-input-field__control) {
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-surface-muted);
  border-color: transparent;
}

/* ==================== Table ==================== */

.kb-table-wrap {
  overflow-x: auto;
  min-width: 0;
}

.kb-table {
  width: 100%;
  min-width: 820px;
  border-collapse: collapse;
}

.kb-table th {
  padding: 0 var(--sp-space-4) var(--sp-space-3);
  color: var(--sp-color-text-muted);
  font-size: var(--sp-font-xs);
  font-weight: 600;
  text-align: left;
}

.kb-table td {
  padding: var(--sp-space-3) var(--sp-space-4);
  border-top: 1px solid var(--sp-border-soft);
  color: var(--sp-color-text-secondary);
}

.kb-table tbody tr:hover td {
  background: var(--sp-color-surface-hover);
}

.kb-table__title {
  display: grid;
  gap: var(--sp-space-1);
}

.kb-table__title strong {
  color: var(--sp-color-text);
  font-weight: 700;
  font-size: var(--sp-font-sm);
}

.kb-table__title small {
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

.kb-table__tags {
  display: flex;
  gap: var(--sp-space-1);
  flex-wrap: wrap;
}

.kb-tag {
  display: inline-block;
  padding: 1px 7px;
  font-size: 11px;
  font-weight: 600;
  color: var(--sp-color-text-muted);
  background: var(--sp-color-surface-muted);
  border-radius: var(--sp-radius-pill);
}

.kb-tag--more {
  color: var(--sp-color-accent-blue);
  background: var(--sp-color-accent-blue-soft);
}

.kb-table__date {
  white-space: nowrap;
  font-size: var(--sp-font-xs);
}

.kb-table__actions {
  display: flex;
  gap: var(--sp-space-1);
}

.kb-empty {
  display: grid;
  place-items: center;
  gap: var(--sp-space-3);
  padding: var(--sp-space-12);
  color: var(--sp-color-text-muted);
}

/* ==================== Upload Section ==================== */

.kb-upload-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-space-5);
  min-width: 0;
}

.kb-upload-zone {
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--sp-space-2);
  padding: var(--sp-space-8);
  border: 2px dashed var(--sp-border-soft);
  border-radius: 18px;
  cursor: pointer;
  transition: border-color var(--sp-transition-fast), background var(--sp-transition-fast);
  text-align: center;
}

.kb-upload-zone:hover {
  border-color: var(--sp-color-accent-blue);
  background: color-mix(in srgb, var(--sp-color-accent-blue) 3%, transparent);
}

.kb-upload-zone__icon {
  color: var(--sp-color-accent-blue);
}

.kb-upload-zone strong {
  font-size: var(--sp-font-sm);
  color: var(--sp-color-text);
}

.kb-upload-zone span {
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
}

.kb-upload-zone__progress {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  margin-top: var(--sp-space-2);
  font-size: var(--sp-font-xs);
  color: var(--sp-color-accent-blue);
}

.kb-upload-zone__spinner {
  animation: sp-spin 0.85s linear infinite;
}

@keyframes sp-spin {
  to { transform: rotate(360deg); }
}

.kb-upload-zone__progress progress {
  width: 120px;
  height: 6px;
  border-radius: var(--sp-radius-pill);
  accent-color: var(--sp-color-accent-blue);
}

/* Document list */

.kb-doc-list__label {
  font-size: var(--sp-font-xs);
  font-weight: 700;
  color: var(--sp-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 var(--sp-space-3);
}

.kb-doc-items {
  display: grid;
  gap: var(--sp-space-2);
}

.kb-doc-item {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  padding: var(--sp-space-3);
  border-radius: 14px;
  background: var(--sp-color-surface-muted);
  border: 1px solid transparent;
}

.kb-doc-item--parsing {
  border-color: var(--sp-color-accent-blue-soft);
  background: color-mix(in srgb, var(--sp-color-accent-blue) 4%, #ffffff);
}

.kb-doc-item--failed {
  border-color: var(--sp-color-accent-pink-soft);
  background: color-mix(in srgb, var(--sp-color-accent-pink) 4%, #ffffff);
}

.kb-doc-item__icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border-radius: 11px;
  color: var(--sp-color-primary);
  background: color-mix(in srgb, var(--sp-color-primary) 8%, #ffffff);
}

.kb-doc-item--failed .kb-doc-item__icon {
  color: var(--sp-color-accent-pink);
  background: var(--sp-color-accent-pink-soft);
}

.kb-doc-item__info {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 1px;
}

.kb-doc-item__info strong {
  font-size: var(--sp-font-xs);
  font-weight: 650;
  color: var(--sp-color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-doc-item__info span {
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

.kb-doc-item__time {
  display: none !important;
}

.kb-doc-item__status {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  flex: 0 0 auto;
}

.kb-doc-item__status progress {
  width: 80px;
  height: 5px;
  border-radius: var(--sp-radius-pill);
  accent-color: var(--sp-color-accent-blue);
}

.kb-doc-item__status span {
  font-size: 11px;
  color: var(--sp-color-text-muted);
  white-space: nowrap;
}

.kb-doc-item__chunks {
  font-size: 10px !important;
  color: var(--sp-color-text-muted) !important;
}

/* ==================== Retrieval Section ==================== */

.kb-retrieval-bar {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  margin-bottom: var(--sp-space-5);
}

.kb-retrieval-bar__input {
  flex: 1;
  min-width: 0;
}

.kb-retrieval-bar__input :deep(.sp-input-field__control) {
  border-radius: var(--sp-radius-control);
}

.kb-retrieval-results__summary {
  margin: 0 0 var(--sp-space-4);
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
}

.kb-retrieval-results__summary strong {
  color: var(--sp-color-text);
  font-weight: 700;
}

.kb-result-item {
  padding: var(--sp-space-4);
  border: 1px solid var(--sp-border-soft);
  border-radius: 16px;
  transition: box-shadow var(--sp-transition-fast);
}

.kb-result-item:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.kb-result-item + .kb-result-item {
  margin-top: var(--sp-space-3);
}

.kb-result-item__head {
  display: flex;
  gap: var(--sp-space-3);
  align-items: center;
  margin-bottom: var(--sp-space-2);
}

.kb-result-item__rank {
  font-size: var(--sp-font-xs);
  font-weight: 700;
  color: var(--sp-color-text-muted);
}

.kb-result-item__score {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--sp-radius-pill);
}

.kb-result-item__score--success {
  color: var(--sp-color-success);
  background: color-mix(in srgb, var(--sp-color-success) 12%, #ffffff);
}

.kb-result-item__score--warning {
  color: var(--sp-color-warning);
  background: color-mix(in srgb, var(--sp-color-warning) 12%, #ffffff);
}

.kb-result-item__score--danger {
  color: var(--sp-color-danger);
  background: color-mix(in srgb, var(--sp-color-danger) 10%, #ffffff);
}

.kb-result-item__fragment {
  margin: 0;
  padding: var(--sp-space-3);
  background: var(--sp-color-surface-muted);
  border-radius: 12px;
  font-size: var(--sp-font-sm);
  line-height: 1.7;
  color: var(--sp-color-text);
  border-left: 3px solid var(--sp-color-accent-blue);
}

.kb-result-item__source {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  margin-top: var(--sp-space-2);
  font-size: 11px;
  color: var(--sp-color-text-muted);
}

.kb-result-item__chunk {
  color: var(--sp-color-text-muted);
}

.kb-result-item__view {
  margin-left: auto;
}

/* Empty retrieval */

.kb-retrieval-empty {
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--sp-space-2);
  padding: var(--sp-space-10);
  color: var(--sp-color-text-muted);
}

.kb-retrieval-empty p {
  margin: 0;
  font-weight: 600;
  color: var(--sp-color-text-secondary);
}

.kb-retrieval-empty span {
  font-size: var(--sp-font-xs);
}

/* ==================== Responsive ==================== */

@media (max-width: 1279px) {
  .kb-upload-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1023px) {
  .kb-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .kb-search {
    width: 100%;
  }

  .kb-table {
    min-width: 700px;
  }
}

@media (max-width: 767px) {
  .kb-section {
    padding: var(--sp-space-4);
  }

  .kb-upload-zone {
    padding: var(--sp-space-6);
  }

  .kb-retrieval-bar {
    flex-direction: column;
  }
}
</style>
