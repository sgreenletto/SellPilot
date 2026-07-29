# 商品内容生成 API

- `POST /api/v1/content-generation/generate`：读取适配器商品事实并生成结构化本地化内容。
- `POST /api/v1/content-generation/draft-confirmations`：为生成结果创建待确认草稿任务，不立即写库。
- `GET /api/v1/content-generation/contents/{content_id}/versions`：查询不可变版本历史。
- `POST /api/v1/content-generation/contents/{content_id}/restore-confirmations`：创建版本恢复待确认任务。
- `POST /api/v1/confirmations/{confirmation_id}/confirm`：确认后执行草稿或恢复写入。
- `POST /api/v1/confirmations/{confirmation_id}/cancel`：取消待确认写操作。

所有接口使用统一认证、响应包装和 Pydantic Schema。商品事实通过平台适配器读取；当前演示数据明确为 Mock。

`site` 只接受公共契约中的 `sg`、`my`、`ph`、`th`、`vn`、`id`、`tw`、`br`；`target_language` 只接受 `zh-CN`、`en`、`ms`、`id`、`th`、`vi`、`tl`、`pt-BR`、`zh-TW`。质量循环最多三次。

草稿确认请求可携带人工编辑后的结构化内容，但服务端会重新验证其来源生成任务、模型调用、商品事实、SKU、目标关键词、语言、完整度与合规结果。客户端传入的旧 `quality.passed` 不能直接授权保存。
