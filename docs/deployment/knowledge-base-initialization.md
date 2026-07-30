# 知识库初始化

SellPilot 使用现有 PostgreSQL `knowledge_documents` / `knowledge_chunks` 和唯一
`RAGService`。默认导入命令只保证一个明确标记为 Mock 的演示政策可幂等写入；它不能
替代真实知识数据验收。

## 前置检查

在仓库根目录配置 `.env`，不要创建 `backend/.env`，不要在终端输出密钥。确认
PostgreSQL 已启动并完成迁移：

```powershell
cd .\backend
uv run alembic upgrade head
uv run alembic current
```

## 幂等导入

源码模块的正式调用方式为：

```powershell
cd .\backend
$env:PYTHONPATH = (Resolve-Path .\src).Path
uv run python -m sellpilot.cli.import_knowledge_data
```

也可使用已安装的项目入口：

```powershell
uv run sellpilot-import-knowledge
```

重复导入通过校验和与来源信息跳过已有文档，不清空或覆盖其他知识数据。不要使用
`--full-rebuild` 处理用户现有库；该参数是旧 CSV 重建路径，具有破坏性且依赖额外模型
环境，不属于 Demo Freeze 的标准步骤。

## 安全状态检查

```powershell
uv run sellpilot-check-demo-readiness
```

输出只包含计数、数据库类型、迁移版本和配置布尔值。重点核对：

- `knowledge.real_documents` 大于 0；
- `knowledge.real_chunks` 大于 0；
- `knowledge.status` 为 `READY`；
- Mock 与真实计数分开，不把 Mock 文档当作真实验收。

## Smoke 验证

1. 登录后通过 `POST /api/v1/knowledge/qa` 查询真实政策主题。
2. 返回必须包含来源、文档 ID、相关度、语言和更新时间。
3. 查询不存在主题，必须返回“当前知识库中没有找到可靠依据。”
4. 空库必须返回“当前知识库尚未完成初始化，请先导入知识数据。”，不得返回 500。
5. 通过 Assistant 执行 `knowledge_query`，检查 Task、Step、ToolCall 和 OperationLog。
6. 再验证 Customer Service 的政策 Branch；无可靠依据时转人工。

导入失败会回滚当前事务，不清空已有数据。报告错误类型即可，不要粘贴连接串、密钥、
完整 Prompt 或供应商响应。
