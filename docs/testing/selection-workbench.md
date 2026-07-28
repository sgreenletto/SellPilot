# 智能选品前端测试

覆盖以下行为：

- API 查询参数转换、认证头、商品对比参数和分析请求体；
- 候选加载、正式分析结果、规则解释和风险提示；
- 后端未连接的明确错误状态；
- 非法价格范围的表单提示和分析按钮禁用；
- 成本/物流覆盖、风险偏好和重量条件进入后端 Schema；
- 风险偏好选择对应版本化权重，覆盖成本进入利润计算；
- 既有前后端功能全量回归。

质量门禁：

```powershell
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build

cd ../backend
uv run ruff format --check src tests
uv run ruff check src tests
uv run pytest -q
```

测试使用合成数据和 Mock API，不连接真实 Shopee、真实模型或生产数据库。
