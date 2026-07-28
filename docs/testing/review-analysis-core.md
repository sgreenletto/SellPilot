# 评论分析内核测试

## 覆盖范围

- English、Filipino、Indonesian、Malay、Thai、Vietnamese 六种模拟数据语言。
- 未知语言、声明语言不一致和翻译不可用。
- 空评论、纯表情、垃圾文本、重复评论和超长文本。
- 正面、中性、负面及多主题评论。
- 正向“与图片一致/符合描述”不会误标为描述不符；包含明确缺点表达的 3 星混合评价会
  进入负向证据。
- 情感、主题、频率、严重度、代表证据和站点/月度趋势重算。
- 来源提示不能覆盖评分驱动结论。
- 空输入及质量检查后无可分析评论时失败。
- Fake Model 合法结构化输出。
- 非法 JSON、缺字段、未知主题、未知或缺失证据 ID、空输出和超时。
- 完整 1,000 条 Mock 评论包以及六站点覆盖。

## 命令

```powershell
cd backend
uv run pytest tests/unit/test_review_analysis.py -q
uv run pytest tests/integration/test_review_analysis_mock_data.py -q
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

集成测试只读取仓库内明确标记为模拟实验数据的 CSV，用于验证内核契约，不代表业务代码直接读取 CSV。后续运行时数据访问仍必须经过成员二 Repository/Service 边界。
