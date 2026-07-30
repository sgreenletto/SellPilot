<script setup lang="ts">
import { BookOpen, Search, Trash2, Zap } from "@lucide/vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, ref, watch } from "vue";
import {
  fetchDocuments,
  deleteDocument,
  retrieveKnowledge,
  type KnowledgeDocumentItem,
  type RetrievalItem,
} from "@/api/knowledge-base";
import SpBadge from "@/components/base/SpBadge.vue";
import SpButton from "@/components/base/SpButton.vue";
import SpInput from "@/components/base/SpInput.vue";
import PageContainer from "@/components/layout/PageContainer.vue";
import { formatBusinessStatus } from "@/utils/displayLabels";

// ==================== 文档列表 ====================

const categoryTabs = [
  { key: "", label: "全部" },
  { key: "product", label: "商品知识" },
  { key: "faq", label: "客服常见问题" },
  { key: "review", label: "用户评论" },
];

const activeCategory = ref("");
const searchQuery = ref("");
const documents = ref<KnowledgeDocumentItem[]>([]);
const docTotal = ref(0);
const docLoading = ref(false);
const categoryCounts = ref<Record<string, number>>({});

const categoryLabels: Record<string, string> = {
  product: "商品知识",
  faq: "客服常见问题",
  review: "用户评论",
};
const knowledgeStatusLabels: Record<string, string> = {
  pending: "待处理",
  processing: "处理中",
  indexed: "已建立索引",
  failed: "处理失败",
};

function categoryLabel(value: string): string {
  return categoryLabels[value] ?? "其他分类";
}

function knowledgeStatusLabel(value: string): string {
  return knowledgeStatusLabels[value] ?? formatBusinessStatus(value);
}

const statusTone = (s: string) =>
  s === "indexed" ? "success" : s === "failed" ? "danger" : "warning";

async function loadDocuments() {
  docLoading.value = true;
  try {
    const res = await fetchDocuments({
      page_size: 100,
      category: activeCategory.value || undefined,
    });
    documents.value = res.items;
    docTotal.value = res.total;
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "未知错误";
    ElMessage.error(`加载文档失败：${msg}`);
  } finally {
    docLoading.value = false;
  }
}

async function loadCategoryCounts() {
  try {
    const totals = await Promise.all(
      categoryTabs.map(async (tab) => {
        const response = await fetchDocuments({
          page_size: 1,
          category: tab.key || undefined,
        });
        return [tab.key, response.total] as const;
      }),
    );
    categoryCounts.value = Object.fromEntries(totals);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "未知错误";
    ElMessage.error(`加载分类统计失败：${msg}`);
  }
}

const filteredDocs = computed(() => {
  if (!searchQuery.value.trim()) return documents.value;
  const q = searchQuery.value.trim().toLowerCase();
  return documents.value.filter(
    (d) => d.title.toLowerCase().includes(q) || (d.source ?? "").toLowerCase().includes(q),
  );
});

async function handleDelete(doc: KnowledgeDocumentItem) {
  try {
    await ElMessageBox.confirm(`确定删除「${doc.title}」？向量数据也将被清除。`, "确认删除", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteDocument(doc.id);
    documents.value = documents.value.filter((d) => d.id !== doc.id);
    docTotal.value = Math.max(0, docTotal.value - 1);
    await loadCategoryCounts();
    ElMessage.success("已删除");
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  void Promise.all([loadDocuments(), loadCategoryCounts()]);
});
watch(activeCategory, () => loadDocuments());

// ==================== 检索测试 ====================

const queryText = ref("");
const searching = ref(false);
const retrievalResults = ref<RetrievalItem[]>([]);

async function handleSearch() {
  const q = queryText.value.trim();
  if (!q) {
    ElMessage.warning("请输入检索问题");
    return;
  }
  searching.value = true;
  retrievalResults.value = [];
  try {
    const results = await retrieveKnowledge({ query: q, top_k: 5 });
    retrievalResults.value = results;
    if (results.length === 0) {
      ElMessage.info("未找到匹配片段");
    } else {
      ElMessage.success(`返回 ${results.length} 条匹配片段`);
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "未知错误";
    ElMessage.error(`检索失败：${msg}`);
  } finally {
    searching.value = false;
  }
}

function scoreClass(s: number) {
  if (s >= 0.5) return "success";
  if (s >= 0.3) return "warning";
  return "danger";
}
</script>

<template>
  <PageContainer>
    <div class="kb-page">
      <!-- ==================== 1. 知识文档 ==================== -->
      <section class="kb-card">
        <div class="kb-card__head">
          <h2><BookOpen :size="20" /> 知识文档</h2>
          <span class="kb-card__total">共 {{ docTotal }} 条</span>
        </div>

        <!-- 分类 Tab + 搜索 -->
        <div class="kb-toolbar">
          <div class="kb-tabs">
            <button
              v-for="tab in categoryTabs"
              :key="tab.key"
              type="button"
              :class="['kb-tab', { 'kb-tab--active': activeCategory === tab.key }]"
              @click="activeCategory = tab.key"
            >
              {{ tab.label }}
              <span class="kb-tab__count">{{ categoryCounts[tab.key] ?? 0 }}</span>
            </button>
          </div>
          <SpInput v-model="searchQuery" placeholder="搜索标题或来源…" class="kb-search" clearable>
            <template #prefix><Search :size="14" /></template>
          </SpInput>
        </div>

        <!-- 表格 -->
        <div v-loading="docLoading" class="kb-table-wrap">
          <table v-if="filteredDocs.length > 0" class="kb-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>分类</th>
                <th>来源</th>
                <th>状态</th>
                <th>切块</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in filteredDocs" :key="doc.id">
                <td>
                  <div class="kb-cell-title">
                    <strong>{{ doc.title }}</strong>
                    <small
                      >{{ doc.file_type }} · {{ (doc.file_size_bytes / 1024).toFixed(1) }} KB</small
                    >
                  </div>
                </td>
                <td>
                  <SpBadge tone="info">{{ categoryLabel(doc.category) }}</SpBadge>
                </td>
                <td class="kb-cell-source">{{ doc.source || "-" }}</td>
                <td>
                  <SpBadge :tone="statusTone(doc.status)" dot>{{
                    knowledgeStatusLabel(doc.status)
                  }}</SpBadge>
                </td>
                <td>{{ doc.chunk_count }}</td>
                <td>
                  <SpButton size="sm" variant="ghost" @click="handleDelete(doc)">
                    <template #icon><Trash2 :size="14" /></template>
                  </SpButton>
                </td>
              </tr>
            </tbody>
          </table>
          <el-empty v-else-if="!docLoading" description="暂无知识文档" />
        </div>
      </section>

      <!-- ==================== 2. 检索测试 ==================== -->
      <section class="kb-card">
        <div class="kb-card__head">
          <h2><Zap :size="20" /> 检索测试</h2>
        </div>

        <div class="kb-search-bar">
          <SpInput
            v-model="queryText"
            placeholder="输入问题，如：电池不耐用怎么办？"
            class="kb-search-bar__input"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #prefix><Search :size="14" /></template>
          </SpInput>
          <SpButton :loading="searching" @click="handleSearch">
            <template #icon><Zap :size="14" /></template>
            检索
          </SpButton>
        </div>

        <!-- 检索结果 -->
        <div v-if="retrievalResults.length > 0" class="kb-results">
          <div v-for="(item, idx) in retrievalResults" :key="idx" class="kb-result">
            <div class="kb-result__head">
              <strong>#{{ idx + 1 }}</strong>
              <span :class="['kb-score', `kb-score--${scoreClass(item.score)}`]">
                相似度 {{ Math.round(item.score * 100) }}%
              </span>
              <span class="kb-result__source">{{ item.source_doc || "来源未知" }}</span>
            </div>
            <blockquote class="kb-result__text">{{ item.fragment }}</blockquote>
          </div>
        </div>
        <el-empty v-else-if="!searching" description="输入问题检索知识库" />
      </section>
    </div>
  </PageContainer>
</template>

<style scoped>
.kb-page {
  display: grid;
  gap: 20px;
}

/* Card */
.kb-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}
.kb-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.kb-card__head h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  margin: 0;
}
.kb-card__total {
  font-size: 13px;
  color: #999;
}

/* Tabs */
.kb-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.kb-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.kb-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: 99px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #666;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.kb-tab:hover {
  border-color: #0b234a;
  color: #0b234a;
}
.kb-tab--active {
  background: #0b234a10;
  border-color: #0b234a;
  color: #0b234a;
}
.kb-tab__count {
  font-size: 11px;
  color: #999;
}
.kb-tab--active .kb-tab__count {
  color: #0b234a;
}
.kb-search {
  width: 220px;
}

/* Table */
.kb-table-wrap {
  min-height: 200px;
}
.kb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.kb-table th {
  padding: 8px 12px;
  text-align: left;
  color: #999;
  font-weight: 600;
}
.kb-table td {
  padding: 10px 12px;
  border-top: 1px solid #f3f4f6;
}
.kb-cell-title {
  display: grid;
  gap: 2px;
}
.kb-cell-title strong {
  color: #111;
}
.kb-cell-title small {
  font-size: 11px;
  color: #999;
}
.kb-cell-source {
  color: #999;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Search */
.kb-search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.kb-search-bar__input {
  flex: 1;
}
.kb-cn-toggle {
  padding: 6px 12px;
  border-radius: 99px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #999;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.kb-cn-toggle--on {
  background: #0b234a10;
  border-color: #0b234a;
  color: #0b234a;
}

/* Results */
.kb-results {
  display: grid;
  gap: 8px;
}
.kb-result {
  border: 1px solid #f3f4f6;
  border-radius: 14px;
  padding: 14px;
}
.kb-result__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.kb-score {
  padding: 2px 8px;
  border-radius: 99px;
  font-weight: 700;
  font-size: 11px;
}
.kb-score--success {
  background: #dcfce7;
  color: #166534;
}
.kb-score--warning {
  background: #fef9c3;
  color: #854d0e;
}
.kb-score--danger {
  background: #fee2e2;
  color: #991b1b;
}
.kb-result__source {
  color: #999;
  margin-left: auto;
}
.kb-result__text {
  margin: 0;
  padding: 10px 12px;
  background: #f9fafb;
  border-left: 3px solid #3b82f6;
  border-radius: 0 8px 8px 0;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
</style>
