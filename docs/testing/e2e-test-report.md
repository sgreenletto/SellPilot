# E2E Smoke 报告

更新日期：2026-07-30

`scripts/e2e-smoke.ps1` 只使用真实 HTTP API，覆盖健康、认证、平台状态、商业查询、
Assistant plan/create/run、Task 审计、AI 工作流和 Confirmation。密码通过
`SecureString` 输入，不写报告。

| 范围                                          | 状态             | 证据/说明                                        |
| --------------------------------------------- | ---------------- | ------------------------------------------------ |
| live / ready                                  | AUTOMATED_PASS   | 本机 `127.0.0.1:8000` 健康，PostgreSQL reachable |
| 登录 / 当前用户 / 平台                        | MANUAL_PASS      | v1.0.0 基线已验收；HTTP 脚本仍需交互凭据          |
| Dashboard / 商品 / 库存 / 订单 / 物流         | AUTOMATED_PASS   | 集成测试与 PostgreSQL 数据摘要                   |
| Assistant plan / create_only / create_and_run | AUTOMATED_PASS   | 后端集成测试                                     |
| Step / ToolCall / OperationLog                | AUTOMATED_PASS   | 后端集成测试                                     |
| 缺参数 / unknown / Tool 注入                  | AUTOMATED_PASS   | 后端集成测试                                     |
| 智能选品                                      | AUTOMATED_PASS   | 全站 20 条、SG 母婴 3 条，Top N 有来源           |
| 评论分析                                      | AUTOMATED_PASS   | PROD-001 可解析并读取关联评论                    |
| 产品改良                                      | AUTOMATED_PASS   | 从商品评论 Branch 生成结构化建议                 |
| Content                                       | AUTOMATED_PASS   | 统一工作流和最大三轮质量 Loop                    |
| 低库存 / 补货建议                             | AUTOMATED_PASS   | READ Tool；不自动改库存                          |
| Confirmation 取消/确认/幂等                   | AUTOMATED_PASS   | 既有集成测试；HTTP 写 smoke 需显式开关           |
| RAG Mock smoke                                | AUTOMATED_PASS   | Mock 文档来源明确                                |
| RAG Chroma 检索                               | AUTOMATED_PASS   | 冷启动 26.08 秒，返回 5 个已索引 Mock 来源        |
| 客服订单/物流/人工 Branch                     | AUTOMATED_PASS   | Branch、风险和草稿测试                           |
| 客服政策 RAG Branch                           | AUTOMATED_PASS   | 统一 RAG Tool 与 Branch 集成测试通过              |
| Mock 发送确认                                 | AUTOMATED_PASS   | 仅 Mock，重复确认只写一次                        |

本轮最终全量命令与数量见 `release-test-report.md`。

智能选品补充真实 API 场景包括站点范围、明确类目、未知类目 no-data 和显式候选 ID，
对应 Task/Step/ToolCall/OperationLog 证据见 `selection-release-validation.md`。

本轮应用内浏览器访问 `127.0.0.1` 被浏览器 URL 安全策略拒绝，未采用 CDP 或其他绕过。
匿名 live/ready 和启动器复用由真实进程验证；需要登录的 HTTP 脚本保留为交付命令，
待操作者通过 `SecureString` 输入管理员密码后复跑。
