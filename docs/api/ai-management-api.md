# AI 管理 API

所有接口位于 `/api/v1/ai-management`，需要 Bearer 登录。接口不会返回或接受
API Key；百炼密钥和服务地址只能由后端根目录 `.env` 配置。

## 查询

- `GET /prompts`：查询 Prompt 模板、状态和最新版本摘要。
- `GET /prompts/{template_id}/versions`：按版本号倒序查询不可变版本。
- `GET /model-runtime`：查询当前提供方、配置完整性和聚合指标。
- `GET /model-invocations`：查询脱敏调用审计记录。
- `GET /evaluation/member3`：实际运行固定成员三评估集并返回指标。

## 创建 Prompt 新版本

`POST /prompts/{template_id}/versions`

```json
{
  "content": "只根据输入指标生成结构化解释。",
  "input_schema": {"type": "object"},
  "output_schema": {"type": "object"},
  "model_parameters": {"temperature": 0},
  "change_summary": "增加数值引用要求",
  "idempotency_key": "prompt-version-client-key"
}
```

输入和输出 Schema 必须声明 `type=object`。Prompt、Schema 和模型参数不得包含
密码、Token 或 API Key。响应是 `pending` 的 `ConfirmationTask`；确认前不会写入版本。
确认成功后创建递增版本，旧版本保持不变。相同幂等键配合不同载荷返回冲突。

## 修改模板状态

`POST /prompts/{template_id}/status`

```json
{
  "status": "INACTIVE",
  "idempotency_key": "prompt-status-client-key"
}
```

状态只允许 `ACTIVE`、`INACTIVE` 或 `ARCHIVED`。请求同样先创建待确认任务，
通过 `POST /api/v1/confirmations/{confirmation_id}/confirm` 确认后才执行。

## 审计边界

Prompt 写操作关联内部 `AgentTask`、`ConfirmationTask` 和 `OperationLog`。前端可以
管理 Prompt 版本中的非敏感模型参数，但不能修改服务器提供方、Base URL 或密钥。
费用仅按本地配置的价格快照估算；零值不能解释为模型免费。
