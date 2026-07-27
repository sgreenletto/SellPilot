# Frontend Foundation Architecture

## 状态与范围

本文描述 SellPilot `0.1.0.dev0` 的前端公共底座。它包含布局、设计变量、组件库、路由、公共状态、API 客户端与经营看板展示，不代表任何跨境电商业务模块已经完成，也不表示 `v0.1.0` 已发布。

## 分层

```text
View
  → Sp 公共组件 / 图表组件
  → composable / Pinia
  → api/http.ts
  → FastAPI /api/v1
```

- View 负责组合页面，不直接使用 `fetch`，不创建 ECharts 实例。
- `components/base` 保持无业务数据，提供交互和视觉原语。
- `components/data-display` 与 `components/ai` 只负责展示契约。
- `components/charts` 管理 ECharts 初始化、响应式 resize 与销毁。
- `config/navigation.ts` 是侧边导航唯一配置来源。
- `stores/app.ts` 只保存侧边栏、页面标题和平台状态等公共状态。
- `mocks/dashboard.ts` 保存 Dashboard 合成演示数据，避免与 View 混合。

## API 与错误

`api/http.ts` 读取 `VITE_API_BASE_URL`，提供超时、统一响应解包和 `FrontendApiError`。开发环境 `/api` 由 Vite 代理到 `VITE_PROXY_TARGET`。

平台状态只通过 `GET /api/v1/platform/status` 获取。接口失败时清空状态并展示“后端未连接”，不允许静默构造 Mock 成功结果。

## 路由与加载

公共路由使用 `DefaultLayout`。业务模块在当前阶段复用 `ModulePlaceholderView`，页面名称、模块和说明来自路由元数据。`/dev/design-system` 仅在开发构建中注册。

## 响应式

- `>= 1280px`：Dashboard 为漏斗与 AI 卡双列。
- `1024px–1279px`：AI 卡移动到漏斗下方。
- `< 1024px`：侧边栏成为抽屉。
- `< 768px`：内容单列，工具栏重排，风险表可横向滚动。

AppShell 使用流式尺寸，不依赖固定画布；全局尊重 `prefers-reduced-motion`。

## 真实边界

- Dashboard 数据为合成 Mock 数据，不是实际店铺数据。
- `MockShopeeAdapter` 的真实状态由后端返回；前端不复制业务适配器。
- `RealShopeeAdapterStub` 只表示未配置占位，不代表连接 Shopee。
- AI Orb 是本地 SVG/CSS 视觉组件；“生成运营报告”不调用模型。
