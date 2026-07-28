# 成员二 Commerce 集成验收

> 验收分支：`test/member2-commerce-integration`  
> 验收基线：`develop` commit `807812d`

## 覆盖范围

- Mock Commerce 数据模型、导入、查询及待确认写操作。
- 市场数据、商品管理、上架库存、订单履约前端页面。
- 选品评分模块读取成员二 Mock 商品及市场数据的兼容性。
- 前后端格式、静态检查、自动化测试和前端生产构建。

## 验收结果

| 检查                           | 结果                       |
| ------------------------------ | -------------------------- |
| `uv lock --check`              | 通过                       |
| `uv run ruff format --check .` | 通过，112 个 Python 文件   |
| `uv run ruff check .`          | 通过                       |
| `uv run pytest -q`             | 通过，158 项               |
| `npm.cmd run format:check`     | 通过                       |
| `npm.cmd run lint`             | 通过                       |
| `npm.cmd run typecheck`        | 通过                       |
| `npm.cmd run test:run`         | 通过，11 个测试文件、27 项 |
| `npm.cmd run build`            | 通过                       |
| `git diff --check`             | 通过                       |

后端集成测试包含 Mock 商品查询、库存查询、确认任务创建以及选品评分读取 Mock
数据的场景。前端专项测试覆盖市场数据导入、商品草稿、库存调整预演、订单脱敏及物流售后展示。

## 环境问题

本机存在全局环境变量 `DEBUG=release`。后端配置要求该值为布尔值，因此直接运行测试时
Pydantic 会拒绝启动。本次验收仅在测试进程中使用：

```powershell
$env:DEBUG = "false"
uv run pytest -q
```

这不是代码测试失败。开发人员应检查自己的终端或系统环境变量，确保 `DEBUG` 使用
`true`/`false`，不要填写 `release`。

## 已知风险

- 前端 `xlsx` 依赖存在已知安全审计告警，只处理本地用户主动选择或仓库内的 Mock
  文件；不得用于不受信任文件。后续应评估服务端受控解析或更换维护中的解析器。
- Dashboard 产物仍有大于 500 kB 的分包警告，不影响本轮运行，但后续应拆分
  ECharts 相关依赖。
- 客服会话尚无订单关联字段，前端保持禁用状态，不伪造关联结果。
