# Frontend Foundation Testing

## 范围

前端测试使用 Vitest、Vue Test Utils 和 jsdom，不访问真实后端、外网、Shopee 或模型服务。ECharts 和浏览器布局 API 在测试环境中使用最小桩，仅验证组件契约和页面组合。

覆盖内容：

- `SpButton` 变体、禁用行为和 `SpCard` 插槽。
- 风险条数量与平台模式文案。
- 侧边栏配置渲染、当前路由和分组展开。
- Dashboard 核心卡片、漏斗阶段和风险数据。
- 占位页路由元数据。
- 平台接口失败后的“后端未连接”状态。
- 设计系统页面渲染。
- 移动端 AppShell 侧边栏切换。
- 桌面端 Shell 的侧边栏与主内容滚动区结构。
- 菜单滚动区、底部用户区、导航文字截断容器和折叠状态。
- Task API 的空查询参数过滤、统一 POST 操作和任务范围 OperationLog 路径。
- Task Center 的列表/空态/错误、筛选与分页、查询参数恢复、并行详情加载、
  Step/Confirmation/ToolCall/OperationLog 展示、服务端动作按钮、二次确认和操作后刷新。

## 命令

```bash
cd frontend
npm run test:run
npm run lint
npm run typecheck
npm run build
```

交互开发时可使用：

```bash
npm test
```

## 浏览器验收

短时启动：

```bash
npm run dev -- --host 127.0.0.1
```

检查 `/dashboard`、`/tasks`、`/dev/design-system` 和至少一个占位路由；分别确认 1440×900、1280×800、1100×800、390×844 与 125% 缩放下无不可控水平溢出。主内容滚动时侧边栏应保持不动，菜单超高时只滚动菜单区，并检查浏览器控制台。`/tasks` 需验证筛选、分页、详情响应式布局、操作锁定、确认二次提示和刷新后 `task_id` 恢复。

Dashboard 数据是合成 Mock 数据。浏览器验收只证明前端展示和响应式结构，不证明后端、Shopee 或业务能力已接通。
