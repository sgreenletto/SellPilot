# 下一候选版本说明

状态：`NOT_READY`

本分支用于 v0.5.0 后的 E2E Demo Freeze，不创建或移动任何 Tag。候选范围包括：

- 修正知识库空库与真实数据未初始化状态，不再因空数据返回 500；
- 增加 PostgreSQL Demo 初始化、就绪检查和真实 HTTP E2E smoke；
- 增加 PostgreSQL + backend + frontend Docker Compose 配置；
- 增加后端 PostgreSQL 与前端全门禁 GitHub Actions；
- 完成发布后能力、安全、部署、演示和测试文档；
- 移除未被页面使用的 Dashboard 硬编码毛利率 API。
- 修复 Selection 大型中间态超过 Task 状态上限的问题，支持站点范围、类目范围、
  no-data 与显式候选的统一执行链。
- Assistant 展示真实 Top N、查询范围、数据来源和安全错误编号。

## 未完成验收

- 知识库已建立 1204 个文档索引，但 readiness 仍将来源分类为 Mock；本轮真实查询受
  外部模型 `MODEL_CALL_FAILED` 阻塞。
- 本机没有 Docker CLI，实际 build/up/health/down 为 `BLOCKED_LOCAL_DOCKER`。
- 当前分支没有 GitHub Actions 运行记录，需在 PR 上获得首次远程通过证据。

如果后续仅修复已发布 v0.5.0 的缺陷，建议使用补丁版本；完成真实 RAG、Docker、CI
和 Demo Freeze 后再评估下一候选里程碑。只有全部交付验收后才建议 v1.0.0。
