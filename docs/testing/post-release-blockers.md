# v1.0.0 发布阻塞清单

更新日期：2026-07-30

结论：`READY_FOR_RELEASE`

## P0_BLOCKER

当前没有已知、可复现的业务、RAG、CI、数据库或安全 P0。

## 已关闭问题

- 智能选品已修复候选检索、大型中间态、站点/类目范围、no-data 和显式候选链路；
- 评论分析可解析稳定商品 ID 并读取关联评论，空数据不会返回 500；
- Content、RAG 和 Customer Service 已进入统一 Tool 与 Workflow 执行链；
- RAG Demo 数据已完成安全重建、来源统计、Chroma 检索命中和无答案拒答；
- README、前端正式展示和发布文档已冻结；
- E2E Demo Freeze 已合入 develop，远程分支不再存在未推送发布内容；
- `origin/develop@a6fac102` 的
  [GitHub Actions quality-gates](https://github.com/sgreenletto/SellPilot/actions/runs/30555903586)
  已通过 backend 与 frontend Job。

## P1_NON_BLOCKING

- Vite 生产构建可能提示大 chunk；最近一次构建成功；
- 选品、评论和改良按受控任务逐步演示，没有跨域自动 composite workflow；
- Chroma embedding 模型首次冷启动实测约 26 秒，后续请求复用进程内模型；
- 外部内容模型和 RAG LLM 的鉴权、限流与可用性由供应商决定；
- 本机未安装 Docker CLI，当前 GitHub Actions 也未执行 Docker build；Compose 和
  Dockerfile 已交付，但容器运行仍需在有 Docker 的环境复核。

## OUT_OF_SCOPE

- 真实 Shopee OAuth、商品发布、客服发送或订单修改；
- 多用户、多店铺生产部署；
- 财务、ERP、生产监控、备份与灾难恢复；
- 对历史 `v0.5.0` Tag 的任何移动、覆盖或重新创建。

最终 release PR 仍需通过分支保护和 PR CI；`v1.0.0` Tag 只在稳定代码合入 `main` 后由
发布负责人创建。
