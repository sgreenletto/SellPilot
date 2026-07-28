export type KnowledgeCategory = "product" | "faq" | "policy" | "logistics";
export type KnowledgeStatus = "active" | "inactive";
export type DocParseStatus = "pending" | "parsing" | "indexed" | "failed";
export type DocFileType = "pdf" | "markdown" | "txt";

export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  category: KnowledgeCategory;
  status: KnowledgeStatus;
  source: string;
  updatedAt: string;
  tags: string[];
}

export interface UploadedDocument {
  id: string;
  name: string;
  type: DocFileType;
  size: string;
  parseStatus: DocParseStatus;
  progress: number; // 0-100
  uploadedAt: string;
  chunks?: number;
  errorMessage?: string;
}

export interface RetrievalResult {
  id: string;
  fragment: string;
  score: number; // 0-1
  sourceDoc: string;
  sourceCategory: KnowledgeCategory;
  chunkIndex: number;
}
