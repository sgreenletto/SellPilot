# 智能选品计算内核测试

核心测试文件为 `backend/tests/unit/test_selection_scoring.py`，模拟数据契约测试为
`backend/tests/integration/test_selection_mock_data.py`。测试不访问数据库、网络、真实
Shopee 或 LLM，样本全部是明确标记的合成数据。

## 已覆盖行为

- 正利润、零利润、负利润和 Decimal 金额舍入；
- 最低利润及最低利润率的包含边界；
- 单候选、全相等、极端离群值和稳定并列；
- 权重和错误、负权重和未知指标；
- 缺少趋势、评论、物流、售后及工厂信息；
- 模拟数据中 `0 分 + 0 条评论` 的无评论标记及非法组合；
- 站点和币种 cohort 隔离；
- 输入顺序变化后的结果可复现；
- 全局排名唯一并与 Step 1 持久化约束兼容；
- 重复商品 ID、空候选列表；
- 固定双候选黄金结果和公式版本。
- 100 条模拟商品均可通过输入 Schema，并形成 6 个站点/币种 cohort。

## 执行命令

在 `backend` 目录运行：

```powershell
uv run pytest tests/unit/test_selection_scoring.py -q
```

提交前运行全量质量门禁：

```powershell
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

测试结果只能记录实际执行结果，不得把计划中的接口、工作流或页面描述为已通过。
