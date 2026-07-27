# API 公共契约

## 1. 适用范围

本文是 SellPilot 后续业务 API 的公共传输契约，复用 `v0.1.0` 已有统一响应、异常和 API 客户端，不建立第二套结构。当前只实现底座 API 和公共 Schema；商品、订单、文件中心等示例不是已开放接口。

## 2. 基础协议

| 项目 | 契约 |
| --- | --- |
| API 版本前缀 | `/api/v1` |
| JSON Content-Type | 请求与响应使用 `application/json` |
| 认证头 | 受保护接口使用 `Authorization: Bearer <token>` |
| Request ID | 请求可传 `X-Request-ID: <UUID>`；响应头和响应体都返回最终 UUID |
| 幂等头 | 单项业务写请求预留 `Idempotency-Key`，8–255 个安全字符 |
| 时间 | 带时区 ISO 8601；后端内部使用 UTC |
| 字段命名 | JSON 使用 `snake_case` |

健康检查与平台状态等明确公开的底座接口不要求认证；Task 和 Confirmation 查询及操作要求 Bearer Token。

## 3. Request ID

客户端可发送标准 UUID 格式的 `X-Request-ID`。服务端只接受 36 字符且可解析为 UUID 的值；缺失、超长、非 ASCII 或非法值会被替换为新 UUID。最终值同时写入：

- `X-Request-ID` 响应头；
- 统一响应体 `request_id`；
- 后端日志的 `request_id` 字段。

客户端不得把用户输入、Token 或业务备注作为 Request ID。

## 4. 成功响应

现有成功包络保持不变：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok"
  },
  "request_id": "8df6ea0f-947e-4df5-a3f2-70408d83450b"
}
```

`data` 的结构由具体接口 Schema 决定。

## 5. 错误响应与错误码

错误沿用同一包络。字段校验错误仅返回字段路径、用户可理解消息和校验类型，不回显原始输入：

```json
{
  "code": "PARAMETER_ERROR",
  "message": "Invalid request parameters",
  "data": [
    {
      "field": "body.username",
      "message": "Field required",
      "type": "missing"
    }
  ],
  "request_id": "50cc29d0-0b66-40e7-b645-d4a268ef1a0c"
}
```

| 错误码 | HTTP 建议 | 含义 |
| --- | ---: | --- |
| `PARAMETER_ERROR` | 422 | 参数或结构化 Schema 校验失败 |
| `UNAUTHENTICATED` | 401 | 未认证或凭据无效 |
| `PERMISSION_DENIED` | 403 | 已认证但无权限 |
| `RESOURCE_NOT_FOUND` | 404 | 数据不存在 |
| `STATE_CONFLICT` | 409 | 当前状态不允许操作 |
| `DUPLICATE_OPERATION` | 409 | 重复注册或重复操作 |
| `IDEMPOTENCY_CONFLICT` | 409 | 同一幂等键对应不同请求 |
| `DATA_IMPORT_FAILED` | 422 | 导入内容无法处理 |
| `MODEL_CALL_FAILED` | 502 | 模型调用失败 |
| `TOOL_FAILED` | 500 | 工具执行失败 |
| `WORKFLOW_FAILED` | 500 | 工作流失败 |
| `MOCK_PLATFORM_FAILED` | 502 | Mock 平台操作失败 |
| `EXTERNAL_SERVICE_UNAVAILABLE` | 503 | 外部服务不可用 |
| `INTERNAL_ERROR` | 500 | 未分类内部错误 |

`PLATFORM_NOT_CONFIGURED`、`PLATFORM_FEATURE_NOT_IMPLEMENTED`、`DATABASE_UNAVAILABLE`、`TOOL_CONFIRMATION_REQUIRED` 和 `CONFIRMATION_EXECUTOR_NOT_FOUND` 保留现有底座语义。错误响应不得包含 Python 堆栈、SQL、连接串、Token、密钥、内部文件路径或未经脱敏的原始输入。

## 6. 分页

列表接口只使用页码分页：

- `page`：默认 1，最小 1；
- `page_size`：默认 20，范围 1–100；
- 不另建 offset 响应。

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "pages": 0
}
```

`pages = ceil(total / page_size)`；`total=0` 时 `pages=0`，空列表仍返回完整结构。

## 7. 排序

公共排序参数：

```json
{
  "field": "created_at",
  "direction": "desc"
}
```

`direction` 只允许 `asc` 或 `desc`。`field` 只允许小写 snake_case 标识符，但这不是数据库授权：每个 Service 必须把外部字段映射到显式白名单，不得把客户端字段直接插入 SQL。

## 8. 基础筛选

共享筛选只定义：

- `search`；
- `created_from` / `created_to`；
- `updated_from` / `updated_to`；
- `status`；
- `source`。

时间范围起点不得晚于终点。模块特有字段由模块 Schema 扩展，不得形成包含全部业务字段的万能筛选对象。

## 9. 批量操作

公共请求：

```json
{
  "ids": [
    "041356a1-8b6d-4318-96cc-42aaf66c205b"
  ],
  "idempotency_key": "inventory-import:20260727:001",
  "note": "synthetic acceptance data"
}
```

`ids` 使用内部 UUID，不能为空，保持首次出现顺序并去重，上限 100。`idempotency_key` 是独立字段，不得用 `note` 冒充。

公共结果：

```json
{
  "total": 2,
  "succeeded": 1,
  "failed": 1,
  "failures": [
    {
      "id": "c75e734b-7e2a-4892-97dc-5719106b0820",
      "error_code": "STATE_CONFLICT",
      "message": "SKU is archived"
    }
  ]
}
```

`total = succeeded + failed`，`failed` 必须等于失败详情数。批量写请求只创建待确认任务；确认执行器获得明确确认后才调用 Service。

## 10. 幂等

- 通用单项业务写 API 使用 `Idempotency-Key` 请求头。
- 批量请求使用受校验的请求体 `idempotency_key`；如果网关同时提供同名头，两者必须一致，否则返回 `IDEMPOTENCY_CONFLICT`。
- 确认任务在内部创建时持久化幂等键；公开 confirm 重试依靠 Confirmation 状态锁和终态保护，不重复执行。
- 模拟上下架、库存批量调整、导入和受控重试的具体执行器在后续模块实现时必须保留该能力。
- 同一键与相同规范化请求关联时返回已有结果；同一键关联不同请求时返回冲突。

## 11. 时间、金额、语言与站点

- 时间使用带时区 ISO 8601，例如 `2026-07-27T08:30:00+00:00`。
- `Money.amount` 是十进制字符串，避免 JSON 二进制浮点误差；`currency` 使用冻结的 `CurrencyCode`。
- 公共金额 Schema 最多 38 位有效数字、18 位小数，不把所有币种强制为两位小数；VND、IDR 等币种规则由业务校验补充。
- 语言代码：`zh-CN`、`en`、`ms`、`id`、`th`、`vi`、`tl`、`pt-BR`、`zh-TW`。
- 站点代码：`sg`、`my`、`ph`、`th`、`vn`、`id`、`tw`、`br`。
- 多语言字段使用 `{ "language": "...", "text": "..." }`；多版本使用 `translations` 受约束列表，语言不可重复。

## 12. 数据来源与 Mock 标识

来源类型为 `mock`、`imported`、`collected`、`generated`、`manual`。来源元数据包含 `source_type`、可选来源名称和引用、`is_mock`、采集或生成时间。

`source_type=mock` 时 `is_mock` 必须为 `true`。Mock Adapter 的响应和合成数据不得使用文案暗示真实 Shopee 生产调用；real 模式配置失败不得回退为 mock。

## 13. 文件上传与下载

当前没有文件中心或上传 API，本节只冻结后续实现边界：

- 允许类别：CSV、XLS/XLSX、JPEG、PNG、WebP、PDF 报告。
- 服务端上限由 `FILE_MAX_SIZE_BYTES` 配置，默认 10 MiB，允许配置范围 1 byte–100 MiB。
- 文件名只作为展示元数据；存储名必须安全生成，拒绝路径穿越和控制字符。
- 不信任客户端 MIME；实现方必须结合扩展名、文件签名和解析结果验证。
- 上传结果使用 `FileUploadResult`：`file_id`、原文件名、安全文件名、确认后的内容类型、字节数、SHA-256、Mock 标识。
- CSV/Excel 只承载结构化导入；图片只承载受支持的商品素材；PDF 只承载报告交付。不得借此上传可执行文件。
- 下载不存在返回 `RESOURCE_NOT_FOUND`；校验或存储失败使用稳定业务错误码，不返回内部路径。

## 14. 长任务状态

长任务复用 AgentTask/TaskService，不建立第二套任务系统：

```json
{
  "task_id": "d7ddb43e-1d9f-45fe-a24c-76abafcf92c4",
  "status": "running",
  "progress": 40,
  "current_step": "validate",
  "message": "Validating synthetic rows",
  "error_code": null,
  "created_at": "2026-07-27T08:00:00+00:00",
  "started_at": "2026-07-27T08:00:01+00:00",
  "completed_at": null
}
```

`progress` 范围 0–100。所有工作流循环必须有明确 `max_retries`；失败重试只能走受控 Task 流转。

## 15. 敏感字段与兼容性

- Authorization、密码、Token、JWT、API Key、密钥、连接串、个人数据和真实店铺数据不得进入示例、客户端错误或普通日志。
- 运单号、外部用户标识等按场景脱敏；客户端不能依赖未声明的内部字段。
- 同一 `/api/v1` 内允许增加可选字段和错误码，不删除或改义既有字段。
- 删除字段、修改字段类型、改变枚举值或状态语义属于不兼容变更，需要新 API 版本和迁移说明。
- `v0.1.0` 数据库中的大写 Task/Confirmation/Tool 状态可被后端兼容读取；新写入和 API 输出统一为冻结的小写值。
