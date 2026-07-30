# E2E Demo Freeze 发布测试报告

更新日期：2026-07-30

分支：`feature/e2e-demo-freeze`

## 数据与迁移

- PostgreSQL：可连接。
- Alembic head/current：`20260728_0007`。
- 数据摘要：1 管理员、103 商品、103 个可供选品的市场快照、1000 评论、263 SKU、
  263 库存、500 订单、451 物流、100 客服会话。
- 知识库：1 个 Mock 文档和 1 个 Mock chunk；真实文档/真实 chunk 为 0，
  `BLOCKED_RAG_DATA`。
- 本阶段无数据库结构变化，无新增迁移。

## 质量门禁

| 命令                                         | 结果                                                           |
| -------------------------------------------- | -------------------------------------------------------------- |
| `uv run ruff format --check .`               | 通过：224 files already formatted                              |
| `uv run ruff check .`                        | 通过：All checks passed                                        |
| `uv run alembic heads/upgrade/current/check` | 通过：单一 `20260728_0007`，无新操作、无待生成迁移             |
| `uv run pytest -q`                           | 通过：367 passed                                               |
| `npm run format:check`                       | 通过：全部匹配 Prettier                                        |
| `npm run lint`                               | 通过：0 warning / 0 error                                      |
| `npm run typecheck`                          | 通过：无 TypeScript 错误                                       |
| `npm run test:run`                           | 通过：30 files、144 tests                                      |
| `npm run build`                              | 通过：4095 modules；仅大 chunk 非阻塞警告                      |
| `docker compose config`                      | BLOCKED_LOCAL_DOCKER：本机无 Docker CLI；YAML 静态格式检查通过 |

## 发布结论

完整代码门禁已通过。真实 RAG 数据验收、Docker 实跑和远程 CI 首次通过仍未完成，
因此当前结论为 `NOT_RELEASE_READY`，不创建发布 Tag。
