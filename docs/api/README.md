# API

- `tool-runtime.md`: authenticated tool metadata, execution and ToolCall query API.

本目录用于后续维护 API 约定、接口清单、请求与响应 Schema、错误模型和版本策略。

公共后端底座 API 已建立，现有端点见 `foundation-api.md`，所有后续模块共同遵守的传输契约见 `common-contracts.md`。当前接口只覆盖健康检查、单用户认证、平台状态以及内部任务/确认任务查询与确认操作，不包含具体跨境电商业务 API。
