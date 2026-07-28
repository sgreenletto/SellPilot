// ---- 会话筛选 ----

export type ConversationTab = "all" | "pending_reply" | "pending_human" | "resolved"

// ---- 会话 ----

export type RiskLevel = "low" | "medium" | "high" | "critical"
export type BuyerLanguage = "id" | "th" | "vi" | "en" | "zh"

export interface Conversation {
  id: string
  buyerName: string
  buyerInitials: string
  language: BuyerLanguage
  languageLabel: string
  unread: boolean
  messageCount: number
  lastMessage: string
  lastMessageTime: string
  status: ConversationTab
  intent: string
  intentLabel: string
  riskLevel: RiskLevel
  platform: "shopee"
  productId: string
  orderId: string
}

// ---- 聊天消息 ----

export interface AiSuggestion {
  confidence: number
  reply: string
  knowledgeSource: string
  knowledgeExcerpt: string
}

export interface ChatMessage {
  id: string
  conversationId: string
  sender: "buyer" | "ai" | "agent"
  content: string
  originalContent?: string
  translatedContent?: string
  language?: BuyerLanguage
  timestamp: string
  aiSuggestion?: AiSuggestion
}

// ---- 右侧上下文面板 ----

export interface ProductContext {
  id: string
  name: string
  imageInitials: string
  price: number
  currency: string
  category: string
  status: "active" | "inactive"
  shopName: string
}

export interface SkuStockItem {
  sku: string
  variant: string
  stock: number
  reserved: number
  status: "sufficient" | "low" | "out"
}

export interface OrderContext {
  id: string
  status: string
  statusLabel: string
  amount: number
  currency: string
  placedAt: string
  items: string[]
  buyerName: string
}

export interface LogisticsEvent {
  time: string
  description: string
  location: string
}

export interface LogisticsTrace {
  id: string
  carrier: string
  trackingNumber: string
  status: string
  statusLabel: string
  events: LogisticsEvent[]
}

export interface ConversationContext {
  product: ProductContext
  skus: SkuStockItem[]
  order: OrderContext
  logistics: LogisticsTrace | null
}
