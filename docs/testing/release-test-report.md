# E2E Demo Freeze 发布测试报告

更新日期：2026-07-30

发布基线：`origin/develop@a6fac10210a85f20904f6f32b0b5361c6e005501`

## 数据与迁移

- PostgreSQL：可连接。
- Alembic head/current：`20260728_0007`。
- 数据摘要：1 管理员、103 商品、103 个可供选品的市场快照、1000 评论、263 SKU、
  263 库存、500 订单、451 物流、100 客服会话。
- 知识库：1204 个索引文档、1204 个 chunk、1203 个 embedding；readiness 当前将
  全部来源分类为 Mock，真实文档/真实 chunk 为 0。
- 本阶段无数据库结构变化，无新增迁移。

## 质量门禁

| 命令                                         | 结果                                                           |
| -------------------------------------------- | -------------------------------------------------------------- |
| `uv run ruff format --check .`               | 通过：227 files already formatted                              |
| `uv run ruff check .`                        | 通过：All checks passed                                        |
| `uv run alembic heads/upgrade/current/check` | 通过：单一 `20260728_0007`，无新操作、无待生成迁移             |
| `uv run pytest -q`                           | 通过：375 passed                                               |
| `npm run format:check`                       | 通过：全部匹配 Prettier                                        |
| `npm run lint`                               | 通过：0 warning / 0 error                                      |
| `npm run typecheck`                          | 通过：无 TypeScript 错误                                       |
| `npm run test:run`                           | 通过：32 files、158 tests                                      |
| `npm run build`                              | 通过：4096 modules；大 chunk 与代理探测为非阻塞警告             |
| `docker compose config`                      | BLOCKED_LOCAL_DOCKER：本机无 Docker CLI；YAML 静态格式检查通过 |
| GitHub Actions `quality-gates`               | 通过：develop 的 backend / frontend Job 均为 success           |

## 发布结论

智能选品已通过 PostgreSQL 真实 API 验收，详见
`selection-release-validation.md`。ChromaDB 冷启动查询在 26.08 秒内成功并返回 5 个
已索引 Mock 来源；无答案场景保持拒答。完整本地代码门禁已通过，且
`origin/develop@a6fac102` 的
[GitHub Actions quality-gates](https://github.com/sgreenletto/SellPilot/actions/runs/30555903586)
已成功。

结论：`READY_FOR_RELEASE`。本机无 Docker CLI、当前 CI 未包含 Docker build，作为明确
记录的非阻塞环境限制，不描述为容器已实跑。
