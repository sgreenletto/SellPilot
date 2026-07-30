# 智能选品发布验收

更新日期：2026-07-30

分支：`feature/e2e-demo-freeze`

## 失败证据与根因

修复前任务：

- Task ID：`b8025350-05a6-4c54-aebb-87e9ac1b4942`
- Request ID：`ec6e8a89-f3a8-4143-98b8-b3d0b0210dcf`
- 工作流：`selection@1.0.0`
- 最终状态：`failed`
- 错误码：`TASK_STATE_TOO_LARGE`
- 安全错误摘要：`Workflow state exceeds the configured size limit`

`search_market_products` 和 `score_product_opportunity` 两个 ToolCall 均已成功。失败发生在
`TaskRunner` 将评分后的完整工具输出再次合并进 serialized state 时：

1. 候选查询将 20 条完整商品快照写入 `candidate_search`；
2. 评分工具又返回完整指标、证据和排序结果；
3. `TaskRunner._safe_state()` 序列化更新后的状态；
4. 状态超过 `TASK_STATE_MAX_BYTES=65536`，抛出 `TaskRuntimeError`；
5. 第三个 Step 因状态持久化失败被标记为失败，但评分 ToolCall 已经成功。

该故障与站点解析、候选查询、确定性评分、LLM 或最终 API JSON 序列化无关。

## 修复

- 工作流状态仅保存候选数量、规范化筛选条件和候选商品 ID，不再复制完整商品快照。
- `score_product_opportunity` 作为终端工具节点直接产生最终结果，避免将大型结果重复写入
  serialized state。
- 类目继续为可选参数；只提供站点时执行有界的站点范围分析。
- 集中区分“未提供类目”和“提供了无法识别的类目”。前者执行站点范围分析，后者返回
  结构化 no-data，不扩大查询范围。
- 显式 `product_ids` 继续通过同一候选查询 Tool 和 PostgreSQL 数据源执行。
- 外部解释生成异常时保留确定性评分，标记解释降级，不把任务整体标记为失败。
- Assistant 展示匹配数量、参与评分数量、Top N、站点、类目、数据来源和风险；失败时
  展示安全原因及 Request ID。

## PostgreSQL 真实 API 验收

| 场景 | Task ID | 结果 |
| --- | --- | --- |
| 新加坡站全站分析 | `5ac3b943-172a-400b-b46e-359c82c7cb1a` | 20 条匹配、20 条评分、成功 |
| 新加坡站母婴用品 | `338ce500-f591-4cd4-bdb4-dbbc380ec0fd` | 3 条匹配、3 条评分、成功 |
| 未知类目 | `5229f18e-e358-49a5-bfee-a320a5482343` | 结构化 no-data、成功终态 |
| 显式候选 ID | `6569cb9c-ca87-4556-ad00-4188dbde3470` | 2 条指定候选评分、成功 |

母婴类目 Top 3：

1. `PROD0102`，机会分 `71.2261`
2. `PROD0101`，机会分 `41.8403`
3. `PROD0103`，机会分 `39.2081`

全站 Top 3：

1. `PROD0049`，机会分 `77.5040`
2. `PROD0097`，机会分 `72.4815`
3. `PROD0102`，机会分 `71.3428`

所有成功场景均通过真实 HTTP API 执行，并产生 Task、Step、ToolCall 和 OperationLog。
本阶段无数据库结构变化，无新增 Alembic 迁移。
