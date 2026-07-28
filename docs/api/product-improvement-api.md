# 产品改良 API

前缀：`/api/v1/product-improvement`，全部要求 Bearer JWT。

- `POST /reports`：根据已完成且归属当前用户的评论分析生成或复用报告。
- `GET /reports/{report_id}`：读取报告和建议。
- `PATCH /suggestions/{suggestion_id}`：人工编辑、采纳或忽略建议。
- `GET /reports/{report_id}/export`：返回稳定 JSON 导出载荷。
- `POST /reports/{report_id}/draft-confirmations`：创建草稿待确认任务，不直接写草稿。

草稿最终通过公共 `/confirmations/{id}/confirm` 或 `/cancel` 处理。确认成功只创建 Mock 商品内容草稿。
