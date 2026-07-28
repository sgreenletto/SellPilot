# AI 管理与翻译工作流增量说明

## 能力边界

成员三能力运行在单用户、单模拟店铺和 Mock Shopee 边界内。选品分数始终来自确定性公式；模型只能翻译、解释或生成经过结构化 Schema 和事实检查的内容。系统不会访问真实 Shopee，也不会自动发布、改价或修改库存。

## 模型和降级

- `CONTENT_MODEL_PROVIDER=offline_template`：完全离线、确定性、适合自动化测试。
- `CONTENT_MODEL_PROVIDER=aliyun_bailian`：通过 OpenAI 兼容接口调用阿里云百炼。
- 百炼模式必须同时配置 `DASHSCOPE_API_KEY` 与 HTTPS `BAILIAN_BASE_URL`，配置不完整时应用拒绝启动，不会伪装成真实调用。
- 评论缺少已有译文时，百炼模式会分批执行忠实翻译；离线模式明确保留“无翻译”状态。
- 内容质量循环由 LangGraph 执行生成、Schema 校验、事实检查、合规检查和有界重试。

## Prompt 和模型审计

`/api/v1/ai-management` 提供只读审计接口：

- `GET /prompts`
- `GET /prompts/{template_id}/versions`
- `GET /model-runtime`
- `GET /model-invocations`
- `GET /evaluation/member3`

接口绝不返回 API Key。Prompt 变更属于业务写操作，后续如开放编辑必须接入 ConfirmationTask；当前页面只读展示版本，避免绕过确认边界。

## 内容补充接口

- `POST /content-generation/regenerate-field`
- `GET /content-generation/contents/{content_id}/versions/{version_id}`
- `GET /content-generation/contents/{content_id}/compare`
- `GET /content-generation/contents/{content_id}/versions/{version_id}/export`

恢复和保存仍通过待确认任务执行。读取、比较和导出不修改业务数据。

## 评论报告

`GET /review-analysis/analyses/{analysis_id}/export` 返回基于已持久化分析结果生成的 Markdown 报告。报告保留 Mock 来源、分析模式和结构化主题/痛点，不重新调用模型。

## 商品管理翻译契约

成员二商品管理页面预留的翻译契约已由以下后端接口实现：

- `GET /api/v1/product-translations/status`
- `POST /api/v1/product-translations/requests`
- `GET /api/v1/product-translations/tasks/{task_id}`

翻译支持 `en`、`zh-CN`、`zh-TW`、`ms`、`id`、`th`、`vi`、`tl` 和
`pt-BR`。请求创建待确认任务，只有用户明确确认后才会把当前 Mock 商品标题、
详情、类目和规格发送给已配置的阿里云百炼。结果只返回商品管理页面的浏览器
会话，不直接修改商品表、价格、库存或平台状态。

未配置百炼时，状态接口返回 `configured=false`，页面禁用机器翻译按钮；系统
不会用离线模板伪装真实翻译。

## 评估边界

AI 管理页面每次请求都会实际运行固定成员三评估集，而不是读取手写通过率。默认离线评估用于回归，不代表百炼线上质量；配置真实模型后仍应另外记录延迟、Token、成本、限流和失败案例。
