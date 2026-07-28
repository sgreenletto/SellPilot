# 公共底座 API

当前版本：**0.1.0**。所有接口位于 `/api/v1`，业务响应统一为：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "UUID"
}
```

`X-Request-ID` 响应头与响应体中的 `request_id` 一致。错误响应沿用相同结构，不返回内部堆栈。

## 健康检查

- `GET /health/live`：进程存活检查，不访问数据库。
- `GET /health/ready`：执行轻量 `SELECT 1`。

## 认证

- `POST /auth/login`：JSON 用户名和密码登录，返回 Bearer JWT。
- `GET /auth/me`：返回当前单用户管理员信息。
- `POST /auth/change-password`：校验旧密码并更新 Argon2 哈希。

JWT 包含 `sub`、`username`、`role`、`iat`、`exp` 和 `jti`。当前不提供刷新 Token、Token 黑名单或多角色授权。退出登录由客户端清除本地 Token 完成。

## 平台状态

- `GET /platform/status`：返回当前适配器、配置状态、可达状态和基础能力。

该接口不表示真实 Shopee 已连接。mock 只保证基础 ping；real 仍是非联网 Stub。

## Task Runtime 与任务中心

- `GET /tasks?page=1&page_size=20&status=pending&workflow_name=diagnostic`
- `POST /tasks`
- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/steps`
- `GET /tasks/{task_id}/operation-logs`
- `POST /tasks/{task_id}/run|resume|retry|rerun|cancel`

需要 Bearer Token，默认只查询当前用户；跨用户资源返回 404。列表支持状态、Workflow、
Task Type、创建时间和分页筛选。详情返回服务端计算的 `available_actions`，前端不复制状态机。
Step、ToolCall、Confirmation 和 OperationLog 通过独立接口按需读取。公开响应不包含
`serialized_state`、执行令牌、runner/heartbeat 字段、原始工具载荷或堆栈。

## 确认任务

- `GET /confirmations?page=1&page_size=20`
- `GET /confirmations/{confirmation_id}`
- `POST /confirmations/{confirmation_id}/confirm`
- `POST /confirmations/{confirmation_id}/cancel`

需要 Bearer Token。确认任务只能由内部 Service 创建，所有接口验证当前用户所有权。
未注册执行器时 confirm 返回明确冲突错误并保持 `pending`；重复 confirm 不重复执行。
成功后所属 Task 保持 `waiting_confirmation` 等待显式 resume；取消或失败会分别同步为
`cancelled` 或 `failed`。快照、结果和错误只返回递归脱敏、截断后的安全摘要。

本轮未新增数据库迁移。Task create/rerun 的请求级幂等持久化仍未实现。
