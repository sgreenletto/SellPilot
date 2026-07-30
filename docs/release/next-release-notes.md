# 下一候选版本说明

状态：`NOT_RELEASE_READY`

本分支用于 v0.5.0 后的 E2E Demo Freeze，不创建或移动任何 Tag。候选范围包括：

- 修正知识库空库与真实数据未初始化状态，不再因空数据返回 500；
- 增加 PostgreSQL Demo 初始化、就绪检查和真实 HTTP E2E smoke；
- 增加 PostgreSQL + backend + frontend Docker Compose 配置；
- 增加后端 PostgreSQL 与前端全门禁 GitHub Actions；
- 完成发布后能力、安全、部署、演示和测试文档；
- 移除未被页面使用的 Dashboard 硬编码毛利率 API。

## 未完成验收

- 真实知识数据尚未导入，状态为 `BLOCKED_RAG_DATA`。
- 本机没有 Docker CLI，实际 build/up/health/down 为 `BLOCKED_LOCAL_DOCKER`。
- GitHub Actions 需在 PR 上获得首次远程通过记录。

如果后续仅修复已发布 v0.5.0 的缺陷，建议使用补丁版本；完成真实 RAG、Docker、CI
和 Demo Freeze 后再评估下一候选里程碑。只有全部交付验收后才建议 v1.0.0。
