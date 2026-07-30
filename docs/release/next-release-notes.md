# v1.0.0 候选版本状态

状态：`READY_FOR_RELEASE`

目标版本：`1.0.0`

基线：`origin/develop@a6fac10210a85f20904f6f32b0b5361c6e005501`

## 已完成

- Assistant、TaskRunner、WorkflowRegistry、ToolRegistry、ToolExecutor、Confirmation 和
  Task Center 已完成统一接入；
- 智能选品、评论分析、产品改良、内容生成、知识库检索、库存、订单、物流和客服编排已
  完成最终业务验收；
- RAG Demo 数据完成导入、重建、来源统计、向量检索和无答案拒答，不再保留数据初始化
  阻塞；
- PostgreSQL Demo 初始化、就绪检查和真实 HTTP E2E Smoke 已交付；
- Docker Compose、前后端 Dockerfile 和 GitHub Actions 已交付；
- 前端正式页面、中文展示、标题、错误状态和 Mock 边界已冻结；
- 根目录 README、发布说明、安全审计和测试报告已完成最终更新。

## 发布证据

- 本地完整门禁：后端 375 项测试通过；前端 32 个测试文件、158 项测试通过；
- Alembic：单一 head `20260728_0007`，无待生成迁移；
- `origin/develop@a6fac102` 的
  [quality-gates](https://github.com/sgreenletto/SellPilot/actions/runs/30555903586)
  已通过 backend 与 frontend 两个 Job；
- 智能选品真实 PostgreSQL API、RAG Chroma 检索与三条业务闭环已有测试和运行记录。

## 非阻塞限制

- 外部模型的鉴权、限流和服务可用性不由项目保证；
- 本机没有 Docker CLI，且当前 CI 不包含 Docker build Job，容器运行仍需在有 Docker 的
  环境复核；
- Vite 大 chunk 和本地开发代理连接探测为已记录的非阻塞警告；
- Shopee 平台读取与写入继续使用 Mock Adapter。

详细范围见 [`v1.0.0-release-notes.md`](v1.0.0-release-notes.md)。最终 PR、合并和 Tag 由
发布负责人执行。
