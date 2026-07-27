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

检查 `/dashboard`、`/dev/design-system` 和至少一个占位路由；分别确认 1440×900、1280×800 与移动宽度无不可控水平溢出，并检查浏览器控制台。

Dashboard 数据是合成 Mock 数据。浏览器验收只证明前端展示和响应式结构，不证明后端、Shopee 或业务能力已接通。
