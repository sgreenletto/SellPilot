# 安全发布审计

审计日期：2026-07-30

## 扫描范围与结果

- 扫描 tracked 文件名：未发现 tracked `.env`、数据库、dump、日志、`dist`、
  `node_modules` 或 `coverage`；仅 `.env.example` 与 `frontend/.env.example`
  属于允许的安全模板。
- 高置信 Token / JWT / 私钥模式：未发现真实凭据。`sk-` 命中来自 CSS
  `risk-indicator` 类名；带凭据数据库 URL 命中来自示例或测试隔离配置。
- 本地绝对用户路径：0 个 tracked 文件命中。
- 本轮 diff 未引入真实密钥。扫描报告只记录文件和类型，不复制疑似凭据。

## 配置与运行边界

- Settings 只读取仓库根 `.env`；`backend/.env` 被初始化脚本拒绝，避免错误覆盖。
- `.env.example` 使用占位配置；浏览器可见的 `VITE_*` 不存放 Token 或密钥。
- PostgreSQL 结构只通过 Alembic；应用启动不调用 `create_all`。
- `DEBUG` 默认关闭；生产响应不返回 traceback。
- CORS 由配置控制；Docker Demo 只允许本机前端来源。
- RealShopeeAdapterStub 缺少真实实现时明确失败，不回退成 Mock。

## 认证、所有权和审计

- 密码使用 Argon2 哈希；JWT 密钥由环境提供。
- Task、Step、ToolCall、Confirmation 和 OperationLog 按当前用户隔离，跨用户资源
  返回 404。
- Tool 输入/输出经过 Schema、递归脱敏和大小限制；公开 Task 结果不返回内部
  serialized state、Prompt 或堆栈。
- WRITE/HIGH_RISK 操作必须 Confirmation；重复确认幂等，不重复执行。
- Mock 结果、Mock 上架和 Mock 客服发送明确标识，不描述为真实 Shopee。

## 剩余风险

- `origin/develop@a6fac102` 的
  [GitHub Actions quality-gates](https://github.com/sgreenletto/SellPilot/actions/runs/30555903586)
  已通过 backend 与 frontend Job。
- 本机无 Docker，且当前 CI 未包含 Docker build；容器运行时安全设置仍需在有 Docker
  的环境复核。
- 导入非 Mock 知识数据时仍需确认来源授权、个人信息脱敏和最小必要范围。
