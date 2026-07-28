# 商品机器翻译预留契约

## 状态与边界

本文仅定义成员二商品页面与成员三翻译服务之间的建议契约，不表示后端路由、翻译供应商或真实机器翻译已经接入。

商品页面在目标语言内容缺失时必须显示“待翻译”，不得使用模板拼接内容伪装成译文。没有配置翻译服务、调用失败或结构校验失败时，必须保留原文并显示真实状态。

## 语言

首批语言沿用公共契约：

```text
en、zh-CN、zh-TW、ms、id、th、vi、tl、pt-BR
```

前端类型定义位于 `frontend/src/types/product-translation.ts`，预留 API 客户端位于
`frontend/src/api/product-translation.ts`。当前商品页不会主动调用尚未实现的后端路由。

## 建议流程

```text
选择商品与目标语言
→ POST /api/v1/product-translations/requests
→ 内部 Service 创建 AgentTask 与 ConfirmationTask
→ 用户通过公共确认接口确认
→ 翻译 Provider 执行
→ Schema 校验
→ 保存 ProductContentVersion
→ 前端读取任务结果与内容版本
```

翻译属于会产生内容版本的业务写操作，公开请求只能创建待确认任务，不能在请求内直接执行翻译或保存结果。

## 建议请求

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

## 建议响应

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
