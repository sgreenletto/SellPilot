# 商品机器翻译 API 契约

## 状态与边界

本文记录成员二商品页面与成员三翻译服务之间已经实现的契约。后端仅在明确配置
阿里云百炼时执行真实机器翻译；未配置时返回不可用状态，不使用模板伪装译文。

商品页面在目标语言内容缺失时必须显示“待翻译”，不得使用模板拼接内容伪装成译文。没有配置翻译服务、调用失败或结构校验失败时，必须保留原文并显示真实状态。

商品标题、描述、类目和具有语言含义的规格进入翻译结果。商品状态、币种、价格、库存、品牌、型号及 Seller SKU 不进入机器翻译：状态由前端枚举按照当前内容语言本地化显示，同时保留稳定业务代码。

## 语言

首批语言沿用公共契约：

```text
en、zh-CN、zh-TW、ms、id、th、vi、tl、pt-BR
```

前端类型定义位于 `frontend/src/types/product-translation.ts`，API 客户端位于
`frontend/src/api/product-translation.ts`，商品管理页面已接入这些接口。

## 已实现流程

```text
选择商品与目标语言
→ POST /api/v1/product-translations/requests
→ 内部 Service 创建 AgentTask 与 ConfirmationTask
→ 用户通过公共确认接口确认
→ 翻译 Provider 执行
→ Schema 校验
→ 将结构化结果保存在确认任务执行结果中
→ 前端按任务 ID 读取当前浏览器会话的翻译结果
```

翻译属于会产生内容版本的业务写操作，公开请求只能创建待确认任务，不能在请求内直接执行翻译或保存结果。

当前翻译结果不会直接修改商品、价格、库存或平台状态，也不会自动保存为
`ProductContentVersion`。如需进入商品内容版本，必须由内容工坊另行创建保存确认任务。

## 请求

```json
{
  "source": {
    "product_id": "PROD0001",
    "source_language": "en",
    "title": "USB-C Hub Essential 001",
    "description": "Multi-port hub for laptop and tablet workflows",
    "category_name": "Consumer Electronics",
    "specifications": [
      {
        "name": "Ports",
        "value": "6-in-1"
      }
    ]
  },
  "target_languages": ["zh-CN", "ms", "th"],
  "fields": ["title", "description", "category_name", "specifications"],
  "idempotency_key": "caller-generated-uuid"
}
```

## 响应

创建请求返回待确认任务引用：

```json
{
  "task_id": "task-uuid",
  "confirmation_task_id": "confirmation-uuid",
  "status": "pending_confirmation",
  "results": [],
  "failed_languages": []
}
```

确认执行成功后，每个目标语言必须返回完整的结构化字段。品牌、型号、Seller SKU 和受保护术语不得擅自翻译。部分语言失败时使用 `partially_failed`，同时返回逐语言稳定错误码，不得把部分成功伪装为全部成功。

## 安全要求

- API Key 只存在于后端环境配置，不进入前端、请求体、日志或仓库。
- 后端通过统一 Translation Provider 访问具体机器翻译服务。
- 请求及响应进入业务流程前必须经过受约束 Schema 校验。
- 原文、机器译文和人工审核稿分别保存，人工编辑不得覆盖来源原文。
- 不记录买家信息、真实店铺凭据或第三方平台 Cookie。
