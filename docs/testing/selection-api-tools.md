# 智能选品 Service、API、Tool 测试

## 覆盖范围

- 使用合成商品和类目趋势验证候选查询、站点映射和最新趋势聚合。
- 验证物流异常率、有效售后申请率、活跃 SKU 与安全库存满足率进入七项评分。
- 导入完整 Mock 数据包后，通过带 Bearer 鉴权的候选、分析、对比和导出 API 验证端到端闭环，
  并断言所有入选商品七项评分非空、数据完整度为 100%。
- 验证内部 `AgentTask`、`ProductSelectionTask` 和排序结果能够一致持久化。
- 验证利润、解释证据、Mock 标记、详情读取和 JSON 导出校验和。
- 验证生成解释中的关键数值不匹配时执行有限重试并回退规则模板。
- 验证批量生成模型解释采用 2–4 路有界并发，并保持确定性评分和排序不变。
- 验证五个选品工具完成注册，利润工具输入输出经过 Schema 校验且风险级别为只读。
- 全量回归现有认证、迁移、确认、适配器、数据导入和评分测试。

## 命令

在 `backend` 目录执行：

```powershell
uv run ruff format --check src tests
uv run ruff check src tests
uv run pytest -q
```

测试使用隔离 PostgreSQL 和合成数据，不访问网络、真实 Shopee 或真实 LLM。应用正式启动仍不会调用 `create_all`；测试夹具使用 `create_all` 只用于每个测试的独立测试数据库。
