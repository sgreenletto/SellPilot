import type { KnowledgeEntry, RetrievalResult, UploadedDocument } from "@/types/knowledge-base";

// ==================== 知识条目 ====================

export const knowledgeEntries: KnowledgeEntry[] = [
  {
    id: "kb-001",
    title: "无线降噪蓝牙耳机 Pro 产品说明",
    content:
      "本产品采用 40mm 钕磁铁驱动单元，支持 ANC 主动降噪，蓝牙 5.3 连接。标准模式下续航约 8 小时，ANC 降噪模式下约 6 小时。支持 USB-C 快充，充电 10 分钟可使用 2 小时。",
    category: "product",
    status: "active",
    source: "产品手册 v2.3",
    updatedAt: "2026-07-25",
    tags: ["耳机", "降噪", "续航", "充电"],
  },
  {
    id: "kb-002",
    title: "65W GaN 氮化镓快充充电器规格",
    content:
      "输出功率最高 65W（20V/3.25A），支持 PD 3.0、QC 4+、PPS 快充协议。兼容 iPhone、Samsung、小米等主流品牌。须搭配支持 65W 的 USB-C to USB-C 数据线使用。",
    category: "product",
    status: "active",
    source: "产品规格表",
    updatedAt: "2026-07-22",
    tags: ["充电器", "快充", "GaN", "65W"],
  },
  {
    id: "kb-003",
    title: "无线耳机电池续航短怎么办？",
    content:
      "若续航显著低于标称值，建议：1) 充满电后使用至自动关机以校准电池电量显示；2) 关闭 ANC 降噪模式（降噪会加快耗电）；3) 关闭不必要的蓝牙多点连接。如仍无法解决，可申请售后检测。",
    category: "faq",
    status: "active",
    source: "客服 FAQ 文档",
    updatedAt: "2026-07-20",
    tags: ["耳机", "电池", "续航", "故障排除"],
  },
  {
    id: "kb-004",
    title: "如何修改订单收货地址？",
    content:
      "订单未发货前可在订单详情页直接修改地址。若订单已发货，请联系客服并提供新地址，我们将通知物流承运商尝试改派。注意：跨境包裹出境后无法修改地址。",
    category: "faq",
    status: "active",
    source: "客服 FAQ 文档",
    updatedAt: "2026-07-18",
    tags: ["订单", "地址", "物流"],
  },
  {
    id: "kb-005",
    title: "7 天无理由退换货政策",
    content:
      "买家签收后 7 天内可申请无理由退换货。要求：商品未使用、包装完整、不影响二次销售。退货运费由平台承担（每月前 3 笔）。特殊商品（耳机、充电器等涉及个人卫生）需未拆封。",
    category: "policy",
    status: "active",
    source: "售后政策 v4.1",
    updatedAt: "2026-07-15",
    tags: ["退货", "退款", "政策", "售后"],
  },
  {
    id: "kb-006",
    title: "商品外观瑕疵退换货流程",
    content:
      "签收后发现商品存在外观瑕疵，需在 24 小时内提供开箱照片/视频作为证据。人工客服审核通过后发起退换流程。换货：3-5 个工作日发出新品。退货：收到退回商品后 48 小时内退款。",
    category: "policy",
    status: "active",
    source: "售后政策 v4.1",
    updatedAt: "2026-07-15",
    tags: ["瑕疵", "退换货", "证据", "政策"],
  },
  {
    id: "kb-007",
    title: "跨境物流时效说明（中国→东南亚）",
    content:
      "中国→东南亚跨境包裹全流程时效：揽收后 1-2 天出关，跨境运输 2-4 天（此段为静默期，无物流更新），目的国清关 1-2 天，末端派送 1-3 天。全程预计 5-11 个工作日。静默期无物流更新属正常流程。",
    category: "logistics",
    status: "active",
    source: "物流说明文档",
    updatedAt: "2026-07-12",
    tags: ["跨境", "物流", "时效", "清关"],
  },
  {
    id: "kb-008",
    title: "包裹丢失或损坏理赔规则",
    content:
      "包裹在运输过程中丢失或损坏，买家可在物流状态异常后 48 小时内提交理赔申请。平台核实后：丢失按订单金额全额退款 + 补偿券；损坏按损坏程度赔偿 30%-100%。处理周期 3-5 个工作日。",
    category: "logistics",
    status: "active",
    source: "物流说明文档",
    updatedAt: "2026-07-10",
    tags: ["理赔", "丢失", "损坏", "物流"],
  },
  {
    id: "kb-009",
    title: "多功能折叠手机支架使用指南",
    content:
      "铝合金材质，支持 4-10 寸手机/平板。360° 旋转底座，高度可调 12-18cm。最大承重 1.5kg。使用前请确认底座防滑垫清洁无灰尘以确保稳定性。",
    category: "product",
    status: "inactive",
    source: "产品手册 v1.0",
    updatedAt: "2026-06-28",
    tags: ["支架", "手机", "使用指南"],
  },
  {
    id: "kb-010",
    title: "发票与收据开具说明",
    content:
      "订单完成后系统自动生成电子收据（PDF 格式）并发送至买家注册邮箱。如需纸质发票，可在订单详情页点击「申请纸质发票」，5-7 个工作日寄达。企业买家可在下单时填写开票信息获取增值税发票。",
    category: "faq",
    status: "active",
    source: "客服 FAQ 文档",
    updatedAt: "2026-07-08",
    tags: ["发票", "收据", "税务"],
  },
];

// ==================== 上传文档状态 ====================

export const uploadedDocuments: UploadedDocument[] = [
  {
    id: "doc-001",
    name: "产品FAQ手册_v3.2.pdf",
    type: "pdf",
    size: "2.4 MB",
    parseStatus: "indexed",
    progress: 100,
    uploadedAt: "2026-07-26 14:30",
    chunks: 48,
  },
  {
    id: "doc-002",
    name: "售后政策_2026Q3.md",
    type: "markdown",
    size: "156 KB",
    parseStatus: "indexed",
    progress: 100,
    uploadedAt: "2026-07-25 09:15",
    chunks: 22,
  },
  {
    id: "doc-003",
    name: "跨境物流操作指南.pdf",
    type: "pdf",
    size: "4.8 MB",
    parseStatus: "parsing",
    progress: 64,
    uploadedAt: "2026-07-27 16:02",
  },
  {
    id: "doc-004",
    name: "店铺政策汇总_v2.txt",
    type: "txt",
    size: "89 KB",
    parseStatus: "failed",
    progress: 32,
    uploadedAt: "2026-07-27 11:45",
    errorMessage: "文档编码格式不支持，请转换为 UTF-8 后重试",
  },
];

// ==================== 检索测试结果 ====================

export const mockRetrievalResults: RetrievalResult[] = [
  {
    id: "ret-001",
    fragment:
      "本产品采用 40mm 钕磁铁驱动单元，支持 ANC 主动降噪，蓝牙 5.3 连接。标准模式下续航约 8 小时，ANC 降噪模式下约 6 小时。",
    score: 0.92,
    sourceDoc: "产品FAQ手册_v3.2.pdf",
    sourceCategory: "product",
    chunkIndex: 3,
  },
  {
    id: "ret-002",
    fragment:
      "若续航显著低于标称值，建议：1) 充满电后使用至自动关机以校准电池电量显示；2) 关闭 ANC 降噪模式（降噪会加快耗电）；3) 关闭不必要的蓝牙多点连接。",
    score: 0.87,
    sourceDoc: "产品FAQ手册_v3.2.pdf",
    sourceCategory: "faq",
    chunkIndex: 12,
  },
  {
    id: "ret-003",
    fragment:
      "支持 USB-C 快充，充电 10 分钟可使用 2 小时。输出功率最高 65W（20V/3.25A），支持 PD 3.0、QC 4+、PPS 快充协议。",
    score: 0.74,
    sourceDoc: "产品FAQ手册_v3.2.pdf",
    sourceCategory: "product",
    chunkIndex: 8,
  },
  {
    id: "ret-004",
    fragment:
      "7 天无理由退换货：买家签收后 7 天内可申请，商品未使用、包装完整。退货运费由平台承担（每月前 3 笔）。耳机、充电器等涉及个人卫生需未拆封。",
    score: 0.61,
    sourceDoc: "售后政策_2026Q3.md",
    sourceCategory: "policy",
    chunkIndex: 5,
  },
  {
    id: "ret-005",
    fragment:
      "跨境物流全程预计 5-11 个工作日：揽收 1-2 天出关，跨境运输 2-4 天（静默期），目的国清关 1-2 天，末端派送 1-3 天。",
    score: 0.53,
    sourceDoc: "跨境物流操作指南.pdf",
    sourceCategory: "logistics",
    chunkIndex: 18,
  },
];
