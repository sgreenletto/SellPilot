import { request } from "@/api/http"

export interface KnowledgeDocumentItem {
  id: string
  title: string
  file_type: string
  file_size_bytes: number
  category: string
  status: string
  chunk_count: number
  source: string | null
  error_message: string | null
  updated_at: string
}

interface PageResult<T> { items: T[]; total: number; page: number; page_size: number; pages: number }

export interface RetrievalItem { fragment: string; score: number; source_doc: string; document_id: string; chunk_index: number }

export interface RAGAnswer { answer: string; sources: { score: number; source_doc: string; category: string; fragment: string }[] }

export function fetchDocuments(p?: { page?: number; page_size?: number; category?: string }): Promise<PageResult<KnowledgeDocumentItem>> {
  const sp = new URLSearchParams()
  sp.set("page", String(p?.page ?? 1)); sp.set("page_size", String(p?.page_size ?? 100))
  if (p?.category) sp.set("category", p.category)
  return request(`/v1/knowledge/documents?${sp.toString()}`)
}

export function deleteDocument(id: string): Promise<{ deleted: boolean }> {
  return request(`/v1/knowledge/documents/${encodeURIComponent(id)}`, { method: "DELETE" })
}

export function retrieveKnowledge(p: { query: string; top_k?: number; category?: string }): Promise<RetrievalItem[]> {
  return request("/v1/knowledge/retrieve", { method: "POST", body: JSON.stringify(p) })
}

export function ragQA(p: { question: string; top_k?: number; category?: string }): Promise<RAGAnswer> {
  return request("/v1/knowledge/qa", { method: "POST", body: JSON.stringify(p) })
}
