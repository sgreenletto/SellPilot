# Assistant 发布后阻塞清单

更新日期：2026-07-30

## P0_BLOCKER

- 当前未发现可复现的非 RAG 代码 P0。完整门禁、API smoke 和浏览器验收结果以
  `release-test-report.md` 为准。

## P1_NON_BLOCKING

- Vite 生产构建可能提示大 chunk；当前不影响构建产物正确性。
- 选品 → 评论 → 改良按受控任务逐步演示，没有跨域自动 composite workflow。
- GitHub Actions 配置需在本分支 PR 上获得第一次远程运行证据。

## BLOCKED_RAG_DATA

- PostgreSQL 当前只有明确标记为 Mock 的退货政策文档；真实知识条目、chunk 和来源
  尚待用户导入。
- `knowledge_query` 和客服政策 Branch 的代码与 Mock smoke 可执行，但真实命中不能
  标记通过。

## BLOCKED_EXTERNAL_MODEL

- 外部内容模型与 LLM 的鉴权、限流和可用性由供应商决定。缺配置或供应商错误保持真实
  失败语义；演示可使用明确标记的 `offline_template`，不能冒充外部模型。

## BLOCKED_LOCAL_DOCKER

- 本机未安装 Docker CLI，无法执行 build/up/health/down。Compose、Dockerfile 和
  Nginx 配置已完成静态格式检查，仍需在有 Docker 的环境实际运行。

## OUT_OF_SCOPE

- 真实 Shopee、多人多店铺、自动发布真实商品、生产监控和云端费用结算。
- 已发布 `v0.5.0` Tag 的任何移动、覆盖或重新创建。
