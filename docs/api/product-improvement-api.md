# 产品改良 API

前缀：`/api/v1/product-improvement`，全部要求 Bearer JWT。

- `POST /reports`：根据已完成且归属当前用户的评论分析生成报告。请求携带
  `force_regenerate=true` 时始终创建递增的新版本；评论分析页的“生成产品改良报告”入口使用此模式。
  未要求强制生成时可复用同一算法版本的已有报告。配置百炼模型时，
  建议文案由模型基于已验证的改进信号生成；模型不得新增证据中不存在的类别。
- `GET /reports/{report_id}`：读取报告和建议。
- `PATCH /suggestions/{suggestion_id}`：人工编辑、采纳或忽略建议。
- `GET /reports/{report_id}/export`：返回面向工厂人工复核的 Markdown 报告载荷，包含问题
  频率、严重程度、优先级、置信度和证据评论编号；API 本身仍使用统一 JSON 包装传输
  文件名、格式和 Markdown 正文。
- `POST /reports/{report_id}/draft-confirmations`：创建草稿待确认任务，不直接写草稿。
- `GET /drafts?source_product_id={product_id}`：查询当前用户指定商品的改良草稿版本历史，仅返回
  `improvement_draft` 和 `improvement_revision` 版本。
- `POST /drafts/{version_id}/revision-confirmations`：基于最新草稿版本申请保存人工编辑结果。
  请求包含 `expected_version` 和结构化改良项；确认前不写入新版本。
- `POST /drafts/clear-confirmations`：为指定 `source_product_id` 创建草稿历史清空待确认任务。
  确认后写入不可见清空标记，不物理删除审计版本。

草稿最终通过公共 `/confirmations/{id}/confirm` 或 `/cancel` 处理。确认成功只创建 Mock 商品内容草稿。
改良方案不是面向站点发布的多语言文案，因此使用语言中立标记 `target_language=und`，避免与同一
商品、站点的内容工坊版本共用内容容器。
报告中的 `confidence` 是改良结论置信度，由评论判定可靠度 60%、去重证据充足度 25% 和
问题覆盖率 15% 组成；`evidence_count` 与 `frequency_rate` 均按来源评论 ID 去重。

前端根据报告的 `review_analysis_result_id` 调用评论分析证据端点读取具体评论内容；建议
响应中的 `evidence_review_ids` 只用于关联，不作为面向用户的主要展示内容。

确认成功后，产品改良页直接展示由已采纳建议组成的草稿预览，不要求跳转内容工坊。
该草稿是供运营和工厂继续审核的改良方案，不等同于已完成的多语言商品文案。

产品改良页会从 PostgreSQL 重新查询草稿历史，因此刷新或重新进入后仍可查看。历史版本只读；
最新版本可编辑。保存编辑结果使用乐观版本检查，若已有更新版本则返回冲突并要求重新加载，
确认成功后新增不可变版本，不覆盖或删除旧版本。

响应中的 `sequence` 是商品维度、按创建顺序递增的展示序号，不等同于内容容器内部的
`version`。清空后页面不再返回清空标记之前的版本，后续新草稿从 `v1` 重新计数；底层审计
版本仍然保留。
