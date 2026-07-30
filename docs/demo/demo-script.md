# E2E Demo 演示脚本

## 0. 环境准备

```powershell
.\scripts\init-demo.ps1 -AdminUsername admin
.\scripts\check-demo-readiness.ps1
.\start-sellpilot.bat
```

页面显示 `Mock 模式`；任何上架、发送和业务数据均为合成演示，不代表真实 Shopee。

## 1. 基础与运行时

1. 登录并打开 Dashboard，说明数据来自 PostgreSQL Mock 数据。
2. 打开 AI 运营助手，输入“查询已发货订单”。
3. 展开执行详情，展示 Task、Step、ToolCall 和 OperationLog。
4. 打开任务中心并用 URL 中真实 `task_id` 定位任务。

## 2. 产品决策闭环

按顺序执行：

1. “分析新加坡站婴儿产品的选品机会”
   - 应返回 3 个候选、Top N、分项评分、风险、数据完整度和来源。
2. “分析商品 PROD-001 的用户评论”
   - 应解析到稳定商品 ID，展示评论数、情感、主题、痛点与证据。
3. “根据商品 PROD-001 的评论生成产品改良建议”
   - 应基于真实 Mock 评论产生结构化建议、严重度、优先级和证据。
4. 如保存改良草稿，展示 Confirmation；取消和确认均不重复执行。

## 3. 商品运营闭环

1. “为商品 PROD-001 生成英文商品文案”。
2. 展示商品事实、英文标题/卖点/详情/FAQ/关键词和质量 Loop。
3. 默认不保存；保存草稿进入 Confirmation。
4. 模拟上架属于 HIGH_RISK，页面必须明确显示 Mock。

## 4. 客服闭环

1. 对会话 `SES00003` 生成普通回复草稿，展示商品/订单依据。
2. 对会话 `SES00004` 生成退款投诉建议，应转人工。
3. 普通草稿选择“模拟发送”，进入 Confirmation。
4. 重复确认不应新增第二条消息；OperationLog 记录 Mock 写操作。

## 5. RAG（真实数据导入后）

1. 查询“退货政策”，展示来源摘要。
2. 查询不存在主题，展示无可靠依据拒答。
3. 通过 Assistant 和客服政策 Branch 分别验证。

在真实数据未导入前，此段状态为 `BLOCKED_RAG_DATA`，不得用 Mock 政策命中代替验收。

## 自动 HTTP Smoke

```powershell
$password = Read-Host "SellPilot password" -AsSecureString
.\scripts\e2e-smoke.ps1 -Username admin -Password $password
```

写操作需显式加 `-IncludeWrites`。脚本只走真实 HTTP API，不直接查数据库伪装业务通过。
