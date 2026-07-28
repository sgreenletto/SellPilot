# 产品改良 API

前缀：`/api/v1/product-improvement`，全部要求 Bearer JWT。

- `POST /reports`：根据已完成且归属当前用户的评论分析生成或复用报告。配置百炼模型时，
  建议文案由模型基于已验证的改进信号生成；模型不得新增证据中不存在的类别。
- `GET /reports/{report_id}`：读取报告和建议。
- `PATCH /suggestions/{suggestion_id}`：人工编辑、采纳或忽略建议。
- `GET /reports/{report_id}/export`：返回面向人工阅读的 Markdown 报告载荷；API 本身仍使用
  统一 JSON 包装传输文件名、格式和 Markdown 正文。
- `POST /reports/{report_id}/draft-confirmations`：创建草稿待确认任务，不直接写草稿。

草稿最终通过公共 `/confirmations/{id}/confirm` 或 `/cancel` 处理。确认成功只创建 Mock 商品内容草稿。
