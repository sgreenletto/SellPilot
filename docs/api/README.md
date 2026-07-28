# API

- `tool-runtime.md`: authenticated tool metadata, execution and ToolCall query API.

本目录用于后续维护 API 约定、接口清单、请求与响应 Schema、错误模型和版本策略。

公共后端底座 API 已建立，现有端点见 `foundation-api.md`，所有后续模块共同遵守的传输契约见
`common-contracts.md`。当前接口覆盖健康检查、单用户认证、平台状态、内部任务/确认任务、
Mock 商业数据和智能选品分析。
成员二数据库驱动的 Mock 商品、订单、物流和消息只读接口见 `commerce-read-api.md`。

成员三智能选品候选、分析、详情、对比和导出接口见 `selection-api.md`。
