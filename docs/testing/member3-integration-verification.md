# 成员三全链路联调验收

## 闭环 A：选品与产品改良

现有正式路径测试覆盖：

- `test_selection_service.py`：Mock 市场数据到可解释选品结果、排序、持久化和导出。
- `test_review_analysis_api.py`：评论读取、分析、证据查询、产品改良报告、建议采纳、报告导出、待确认草稿和重复确认保护。

草稿写入只会在明确确认后执行，不会修改真实商品、价格、库存或平台状态。

## 闭环 B：商品内容

`test_member3_content_flow.py` 使用正式 API 和服务路径覆盖：

1. 从 Mock 平台适配器读取商品事实。
2. 使用 `offline_template` 生成严格结构化内容。
3. 完成事实、合规和完整性检查。
4. 创建待确认草稿任务，并验证幂等保护。
5. 明确确认后保存第一版商品草稿。
6. 查询版本用于人工编辑和版本比较。
7. 创建恢复待确认任务，确认后保存第二个不可变版本。

## 可重复命令

```powershell
cd backend
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run sellpilot-evaluate-member3

cd ../frontend
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build

cd ..
git status --short --branch
git diff --check
```

## 验收边界

- 全部测试仅使用 Mock Shopee 与合成数据。
- 业务代码通过平台适配器访问平台数据。
- 离线模式不宣称接入真实 LLM。
- 所有业务写入均经过待确认任务。
- 报告导出为结构化 JSON，服务器不写入用户报告文件。
- 最终前端全量验收在三个页面并行优化任务汇总后执行。

## 2026-07-28 实际验收结果

本节来自实际命令运行，不代表未执行项目也已通过。

- 后端 `ruff format --check`：通过，163 个文件格式正确。
- 后端 `ruff check`：通过。
- 后端全量测试：`240 passed`。
- Step 14 固定评估：9 个合成案例，当前失败案例 0；详细指标见
  `member3-ai-evaluation-report.md`。
- 成员三前端专项测试：选品、评论分析、产品改良、趋势图和内容生成专项均通过。
- 前端生产构建：通过。
- `git diff --check`：通过。

项目级前端门禁仍存在以下非成员三页面问题，未在本次跨责任边界修改：

- 全量测试：经营看板测试 7 项失败，其余 53 项通过。
- TypeScript：经营看板、客服、知识库和登录等文件仍有类型错误。
- ESLint：客服存在 2 个未使用类型、经营看板存在 1 个 `console`、知识库存在
  1 个未使用函数。
- Prettier 全量检查：19 个其他成员文件尚未格式化。

已补齐 ESLint 配置所需的 `vue-eslint-parser` 开发依赖，因此上述 ESLint 结果来自真实规则检查，
不是因为工具无法启动。
