# Assistant 发布后阻塞清单

更新日期：2026-07-30

## P0_BLOCKER

- 智能选品代码故障已修复，当前未发现其他可复现的非 RAG 业务代码 P0。
- 本机没有 Docker CLI，且 `feature/e2e-demo-freeze` 当前没有 GitHub Actions 运行记录；
  尚不满足“Docker build 或 CI 至少一项具有真实远程证据”的最终发布门槛。

## P1_NON_BLOCKING

- Vite 生产构建可能提示大 chunk；当前不影响构建产物正确性。
- 选品 → 评论 → 改良按受控任务逐步演示，没有跨域自动 composite workflow。
- GitHub Actions 配置需在本分支 PR 上获得第一次远程运行证据。
- Vite build 成功，但构建时开发代理对 `127.0.0.1:3000` 的连接探测产生非阻塞
  `ECONNREFUSED` 输出；未影响产物生成。

## BLOCKED_RAG_DATA

- PostgreSQL 当前有 1204 个索引文档和 1204 个 chunk，其中 1203 个 chunk 有
  embedding；readiness 仍将全部来源分类为 Mock，真实来源计数为 0。
- 本轮真实 `knowledge_query` 因外部模型返回 `MODEL_CALL_FAILED`，尚未取得新的命中
  证据。该问题不属于 Selection 修复范围。

## BLOCKED_EXTERNAL_MODEL

- 外部内容模型与 LLM 的鉴权、限流和可用性由供应商决定。缺配置或供应商错误保持真实
  失败语义；演示可使用明确标记的 `offline_template`，不能冒充外部模型。
- 本轮知识库查询 Task `0aeb489f-f78e-48ec-8176-dfdbac2d0d90` 真实失败于
  `MODEL_CALL_FAILED`，安全摘要为模型请求或响应无效。

## BLOCKED_LOCAL_DOCKER

- 本机未安装 Docker CLI，无法执行 build/up/health/down。Compose、Dockerfile 和
  Nginx 配置已完成静态格式检查，仍需在有 Docker 的环境实际运行。

## OUT_OF_SCOPE

- 真实 Shopee、多人多店铺、自动发布真实商品、生产监控和云端费用结算。
- 已发布 `v0.5.0` Tag 的任何移动、覆盖或重新创建。
